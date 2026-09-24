"""
Phase 1 — city-scale NO2 inversion for Pune + PCMC (reproduces the base paper's method).

Steps
1. Match every cube overpass to its ERA5 wind (nearest time, <= 30 min).
2. Source location: maximum of the smoothed calm-wind composite (ws < calm_max_ms) within
   source_search_radius_km of the Pune/PCMC centre (mean of the C1 and C2 waypoints).
3. Rotate windy overpasses (windy_min_ms..windy_max_ms) about that point, build the line density,
   fit the EMG by Differential Evolution (settings from configs/study.yaml).
4. Uncertainty: bootstrap over overpasses (refit from the DE optimum with bounded least squares).
5. Sensitivity: wind regime (E-SE vs W-NW), wind-speed class, wind level.

Outputs: outputs/phase1/city_fit.json and figures in outputs/phase1/figures/.

Usage:
    python -m ecotrack.inversion.run_city
"""

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from scipy.ndimage import uniform_filter
from scipy.optimize import least_squares

from ecotrack.acquire.tropomi_cube import load_cube
from ecotrack.config import DATA_INTERIM, OUTPUTS, load_config
from ecotrack.geometry import corridor_polygon, waypoints
from ecotrack.inversion.emg import (
    PARAMS, RotatedGrid, as_dict, bin_days, default_bounds, emg_model, emissions, fit_emg,
    line_density, offsets_km,
)

OUT = OUTPUTS / "phase1"
FIG = OUT / "figures"

# Figure styling (dataviz reference palette): one-hue blue ramp for magnitude, ink for text,
# recessive grid, 2 px lines.
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
BLUE, ORANGE = "#2a78d6", "#eb6834"
SEQ = LinearSegmentedColormap.from_list("seq_blue", ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "axes.edgecolor": GRID,
    "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.spines.top": False,
    "axes.spines.right": False, "font.size": 10, "lines.linewidth": 2, "savefig.dpi": 200,
})


# ----------------------------------------------------------------------------- data
def match_wind(times, cfg):
    met = pd.read_csv(DATA_INTERIM / "era5" / "overpass_met.csv", parse_dates=["time_utc"])
    met = met[met.cluster == "C2_pcmc"].sort_values("time_utc")
    lvl = cfg["inversion"]["wind_level"]
    met["time_utc"] = met.time_utc.astype("datetime64[ns]")
    cube = pd.DataFrame({"t": pd.DatetimeIndex(times).astype("datetime64[ns]"), "k": np.arange(len(times))}).sort_values("t")
    m = pd.merge_asof(cube, met, left_on="t", right_on="time_utc", direction="nearest",
                      tolerance=pd.Timedelta("30min")).sort_values("k")
    return m.reset_index(drop=True), lvl


def city_centre():
    wp = {w["name"]: w for w in waypoints()}
    cfg = load_config()
    names = cfg["clusters"]["C1_shivajinagar_kasarwadi"] + cfg["clusters"]["C2_pcmc"]
    return np.mean([wp[n]["lat"] for n in names]), np.mean([wp[n]["lon"] for n in names])


def locate_source(no2, calm, lat, lon, inv):
    comp = np.nanmean(no2[calm], axis=0)
    smooth = uniform_filter(np.nan_to_num(comp, nan=np.nanmean(comp)), size=3)
    lat_c, lon_c = city_centre()
    dx, dy = offsets_km(lat, lon, lat_c, lon_c)
    smooth_masked = np.where(np.hypot(dx, dy) <= inv["source_search_radius_km"], smooth, -np.inf)
    i, j = np.unravel_index(np.argmax(smooth_masked), smooth.shape)
    return float(lat[i]), float(lon[j]), comp


# ----------------------------------------------------------------------------- fitting
def fit_subset(sel, sums, cnts, grid, ws, inv, label, n_boot=0, rng=None):
    L, field = line_density(sums[sel], cnts[sel], grid)
    fit = fit_emg(grid.along, L, inv["de"])
    w = float(np.mean(ws[sel]))
    e = emissions(fit["a"], fit["x0"], w, inv["nox_no2_ratio"])
    out = {"label": label, "n_overpasses": int(sel.sum()), "fit": {k: float(fit[k]) for k in PARAMS + ("r2",)},
           "at_bound": fit["at_bound"], "emission": as_dict(e)}
    if n_boot:
        out["bootstrap"] = bootstrap(sel, sums, cnts, grid, ws, inv, fit, n_boot, rng)
    return out, L, field, fit


def bootstrap(sel, sums, cnts, grid, ws, inv, fit, n_boot, rng):
    idx = np.flatnonzero(sel)
    x = grid.along
    p0 = np.array([fit[k] for k in PARAMS])
    bounds = default_bounds(x, line_density(sums[sel], cnts[sel], grid)[0])
    lo, hi = np.array(bounds).T
    draws = []
    for _ in range(n_boot):
        pick = rng.choice(idx, size=len(idx), replace=True)
        wts = np.bincount(pick, minlength=len(sums)).astype(float)
        L, _ = line_density(sums, cnts, grid, weights=wts)
        ok = np.isfinite(L)
        scale = np.nanmax(np.abs(L))
        res = least_squares(lambda p: (emg_model(x[ok], *p) - L[ok]) / scale, np.clip(p0, lo, hi), bounds=(lo, hi))
        e = emissions(res.x[0], res.x[1], float(np.mean(ws[pick])), inv["nox_no2_ratio"])
        draws.append([e.e_nox_kg_s, e.e_nox_kt_yr, e.tau_h, res.x[1]])
    d = np.array(draws)
    q = lambda col: [float(v) for v in np.percentile(d[:, col], [2.5, 50, 97.5])]
    rel = float(np.std(d[:, 0]) / np.mean(d[:, 0]))
    return {"n": n_boot, "e_nox_kg_s_ci95": q(0), "e_nox_kt_yr_ci95": q(1), "tau_h_ci95": q(2),
            "x0_km_ci95": q(3), "e_nox_rel_std": rel}


# ----------------------------------------------------------------------------- figures
def fig_calm(comp, lat, lon, src, n_calm):
    fig, ax = plt.subplots(figsize=(6.4, 5.6))
    extent = [lon[0] - 0.005, lon[-1] + 0.005, lat[-1] - 0.005, lat[0] + 0.005]
    im = ax.imshow(comp * 1e6, extent=extent, cmap=SEQ, origin="upper", aspect="auto")
    cx, cy = corridor_polygon().exterior.xy
    ax.plot(cx, cy, color=INK, lw=1.2, label="Corridor")
    ax.plot(src[1], src[0], marker="o", ms=9, mfc=ORANGE, mec=SURFACE, mew=2, ls="none", label="Source (calm max)")
    ax.set_xlabel("Longitude (°E)"); ax.set_ylabel("Latitude (°N)"); ax.grid(False)
    ax.set_title(f"Calm-wind NO₂ composite (n = {n_calm} overpasses, wind < 2 m/s)", fontsize=11, loc="left")
    cb = fig.colorbar(im, ax=ax, shrink=0.85); cb.set_label("Tropospheric NO₂ (µmol/m²)", color=INK2)
    cb.outline.set_edgecolor(GRID)
    ax.legend(loc="lower left", frameon=False)
    fig.tight_layout(); fig.savefig(FIG / "calm_composite.png"); plt.close(fig)


def fig_rotated(field, grid, label, name):
    fig, ax = plt.subplots(figsize=(7, 3.4))
    ext = [grid.along_edges[0], grid.along_edges[-1], grid.across_edges[0], grid.across_edges[-1]]
    im = ax.imshow(field.T * 1e6, extent=ext, origin="lower", cmap=SEQ, aspect="auto")
    ax.axvline(0, color=INK, lw=1, ls=":")
    ax.set_xlabel("Distance along wind (km, + = downwind)"); ax.set_ylabel("Across wind (km)"); ax.grid(False)
    ax.set_title(f"Wind-rotated mean NO₂: {label}", fontsize=11, loc="left")
    cb = fig.colorbar(im, ax=ax); cb.set_label("µmol/m²", color=INK2); cb.outline.set_edgecolor(GRID)
    fig.tight_layout(); fig.savefig(FIG / f"rotated_{name}.png"); plt.close(fig)


def fig_line_density(grid, L, fit, res, name):
    fig, ax = plt.subplots(figsize=(7, 3.8))
    x = grid.along
    xf = np.linspace(x[0], x[-1], 400)
    ax.plot(x, L * 1e3, "o", ms=5, color=BLUE, mec=SURFACE, mew=1, label="Observed line density")
    ax.plot(xf, emg_model(xf, *[fit[k] for k in PARAMS]) * 1e3, color=ORANGE, label="EMG fit")
    ax.axhline(fit["b"] * 1e3, color=INK2, lw=1, ls="--", label="Fitted background")
    e = res["emission"]
    ci = res.get("bootstrap", {}).get("e_nox_kg_s_ci95")
    txt = (f"E(NOx) = {e['e_nox_kg_s']:.2f} kg/s" + (f"  [{ci[0]:.2f}–{ci[2]:.2f}]" if ci else "")
           + f"\nτ = {e['tau_h']:.1f} h   x₀ = {e['x0_km']:.0f} km   w = {e['wind_ms']:.1f} m/s   R² = {fit['r2']:.2f}"
           + f"\nn = {res['n_overpasses']} overpasses")
    ax.text(0.99, 0.97, txt, transform=ax.transAxes, ha="right", va="top", fontsize=9, color=INK)
    ax.set_xlabel("Distance along wind (km, + = downwind)"); ax.set_ylabel("NO₂ line density (mmol/m)")
    ax.set_title(f"Line density and EMG fit: {res['label']}", fontsize=11, loc="left")
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    fig.tight_layout(); fig.savefig(FIG / f"line_density_{name}.png"); plt.close(fig)


def fig_sensitivity(results):
    rows = [r for r in results if r.get("bootstrap")] + [r for r in results if not r.get("bootstrap")]
    fig, ax = plt.subplots(figsize=(7, 0.45 * len(rows) + 1.2))
    for i, r in enumerate(rows):
        e = r["emission"]["e_nox_kg_s"]
        ax.plot(e, i, "o", ms=8, color=BLUE, mec=SURFACE, mew=2)
        if r.get("bootstrap"):
            lo, _, hi = r["bootstrap"]["e_nox_kg_s_ci95"]
            ax.plot([lo, hi], [i, i], color=BLUE, lw=2)
        ax.text(e, i + 0.28, f"{e:.2f}", ha="center", fontsize=8, color=INK2)
    ax.set_yticks(range(len(rows)), [f"{r['label']} (n={r['n_overpasses']})" for r in rows])
    ax.invert_yaxis(); ax.set_xlabel("NOx emission (kg/s, as NO₂)"); ax.grid(axis="y", visible=False)
    ax.set_title("Pune + PCMC NOx emission: main fit (95% CI) and sensitivity runs", fontsize=11, loc="left")
    fig.tight_layout(); fig.savefig(FIG / "sensitivity.png"); plt.close(fig)


# ----------------------------------------------------------------------------- main
def run():
    cfg = load_config()
    inv = cfg["inversion"]
    OUT.mkdir(parents=True, exist_ok=True); FIG.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(inv["de"]["seed"])

    no2, times, lat, lon, _ = load_cube()
    met, lvl = match_wind(times, cfg)
    has_wind = met[f"u{lvl}"].notna().to_numpy()
    print(f"{len(times)} overpasses in cube, {has_wind.sum()} matched to ERA5 (level {lvl})")

    ws = met[f"ws{lvl}"].to_numpy()
    calm = has_wind & (ws < inv["calm_max_ms"])
    windy = has_wind & (ws >= inv["windy_min_ms"]) & (ws <= inv["windy_max_ms"])
    lat0, lon0, calm_comp = locate_source(no2, calm, lat, lon, inv)
    print(f"Source (calm composite max, n={calm.sum()}): {lat0:.3f} N, {lon0:.3f} E")
    fig_calm(calm_comp, lat, lon, (lat0, lon0), int(calm.sum()))

    grid = RotatedGrid.from_config(inv)
    dx, dy = offsets_km(lat, lon, lat0, lon0)

    def binned(level):
        u, v = met[f"u{level}"].fillna(0).to_numpy(), met[f"v{level}"].fillna(0).to_numpy()
        return bin_days(no2, u, v, dx, dy, grid)

    sums, cnts = binned(lvl)
    wd = met[f"wd{lvl}"].to_numpy()
    results = []

    main, L, field, fit = fit_subset(windy, sums, cnts, grid, ws, inv, f"All windy days ({lvl} hPa wind)" if lvl == "850" else f"All windy days ({lvl} m wind)",
                                     n_boot=inv["bootstrap"], rng=rng)
    results.append(main)
    fig_rotated(field, grid, main["label"], "main")
    fig_line_density(grid, L, fit, main, "main")
    print(f"MAIN: E(NOx) = {main['emission']['e_nox_kg_s']:.3f} kg/s, tau = {main['emission']['tau_h']:.2f} h, R2 = {fit['r2']:.3f}")

    subsets = {
        "regime_ese": ("Easterly regime (from 45–180°)", windy & (wd >= 45) & (wd < 180)),
        "regime_wnw": ("Westerly regime (from 225–360°)", windy & (wd >= 225)),
        "ws_2_4": ("Wind 2–4 m/s", windy & (ws < 4)),
        "ws_4_8": ("Wind 4–8 m/s", windy & (ws >= 4)),
    }
    for name, (label, sel) in subsets.items():
        r, L, field, fit = fit_subset(sel, sums, cnts, grid, ws, inv, label, n_boot=100, rng=rng)
        results.append(r); fig_line_density(grid, L, fit, r, name)
        print(f"  {label:34s} n={r['n_overpasses']:4d}  E = {r['emission']['e_nox_kg_s']:.3f} kg/s  tau = {r['emission']['tau_h']:.2f} h  R2 = {fit['r2']:.2f}")

    for other in [lvl_ for lvl_ in ("100", "10") if lvl_ != lvl]:
        ws_o = met[f"ws{other}"].to_numpy()
        sel = has_wind & (ws_o >= inv["windy_min_ms"]) & (ws_o <= inv["windy_max_ms"])
        s_o, c_o = binned(other)
        r, L, field, fit = fit_subset(sel, s_o, c_o, grid, ws_o, inv, f"Wind level {other} m")
        results.append(r); fig_line_density(grid, L, fit, r, f"level_{other}")
        print(f"  {r['label']:34s} n={r['n_overpasses']:4d}  E = {r['emission']['e_nox_kg_s']:.3f} kg/s  tau = {r['emission']['tau_h']:.2f} h  R2 = {fit['r2']:.2f}")

    fig_sensitivity(results)
    summary = {"source_lat": lat0, "source_lon": lon0, "n_calm": int(calm.sum()), "wind_level": lvl,
               "settings": {k: inv[k] for k in ("rot_res_km", "along_km", "across_halfwidth_km", "nox_no2_ratio", "de")},
               "results": results}
    (OUT / "city_fit.json").write_text(json.dumps(summary, indent=2))
    print(f"Saved {OUT / 'city_fit.json'} and figures in {FIG}")


if __name__ == "__main__":
    run()
