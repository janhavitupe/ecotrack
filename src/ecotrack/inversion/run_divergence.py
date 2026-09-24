"""
Phase 1 — flux-divergence NOx emission map and cluster totals (D1).

Uses the TROPOMI cube, ERA5 wind (same level as the EMG fit) and the EMG lifetime. Produces:
- a NOx emission map (outputs/phase1/figures/divergence_map.png, data in divergence_map.npz)
- totals for the three corridor clusters and for the Pune core, with bootstrap 95% CIs
- a consistency check: total within R km of the source vs the EMG city estimate
- sensitivity to lifetime, background and wind level

Corridor pixels are assigned to the cluster of their nearest waypoint, so clusters don't overlap.

Usage (after run_city):
    python -m ecotrack.inversion.run_divergence
"""

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from scipy.ndimage import uniform_filter
from shapely import contains_xy

from ecotrack.acquire.tropomi_cube import load_cube
from ecotrack.config import OUTPUTS, load_config
from ecotrack.geometry import corridor_polygon, waypoints
from ecotrack.inversion.divergence import emission_map, integrate_kg_s
from ecotrack.inversion.emg import SECONDS_PER_YEAR, M_NO2, offsets_km
from ecotrack.inversion.run_city import BLUE, FIG, GRID, INK, INK2, ORANGE, OUT, SURFACE, match_wind

DIVERGING = LinearSegmentedColormap.from_list("div", ["#2a78d6", "#f0efec", "#e34948"])  # blue - gray - red
CLUSTER_COLORS = {"C1_shivajinagar_kasarwadi": "#2a78d6", "C2_pcmc": "#eb6834", "C3_dehu_talegaon": "#1baf7a"}
CLUSTER_LABELS = {"C1_shivajinagar_kasarwadi": "C1 Shivajinagar–Kasarwadi", "C2_pcmc": "C2 PCMC",
                  "C3_dehu_talegaon": "C3 Dehu Road–Talegaon", "pune_core": "Pune core (outside corridor)"}
RADII_KM = [5, 10, 15, 20, 25, 30, 35]


def zones(lat, lon, src, cfg):
    """Boolean pixel masks: the three clusters (partition of the corridor) and the Pune core."""
    lon2d, lat2d = np.meshgrid(lon, lat)
    in_corr = contains_xy(corridor_polygon(), lon2d, lat2d)
    wps = waypoints()
    cluster_of = {m: c for c, members in cfg["clusters"].items() for m in members}
    dists = np.stack([np.hypot(*offsets_km(lat, lon, w["lat"], w["lon"])) for w in wps])
    nearest = np.array([cluster_of[w["name"]] for w in wps])[np.argmin(dists, axis=0)]
    masks = {c: in_corr & (nearest == c) for c in cfg["clusters"]}
    r_src = np.hypot(*offsets_km(lat, lon, *src))
    masks["pune_core"] = (~in_corr) & (r_src <= 10)
    return masks, in_corr, r_src


def run():
    cfg = load_config()
    inv = cfg["inversion"]
    city = json.loads((OUT / "city_fit.json").read_text())
    src = (city["source_lat"], city["source_lon"])
    tau_h = city["results"][0]["emission"]["tau_h"]

    no2, times, lat, lon, _ = load_cube()
    met, lvl = match_wind(times, cfg)
    ws = met[f"ws{lvl}"].to_numpy()
    use = met[f"u{lvl}"].notna().to_numpy() & (ws <= inv["windy_max_ms"])
    no2, met = no2[use], met[use].reset_index(drop=True)
    u, v = met[f"u{lvl}"].to_numpy(), met[f"v{lvl}"].to_numpy()
    print(f"{use.sum()} overpasses (wind <= {inv['windy_max_ms']} m/s), tau = {tau_h:.2f} h from EMG")

    vbar_all = np.nanmean(no2, axis=0)
    v_bg = float(np.nanpercentile(vbar_all, 10))
    ratio = inv["nox_no2_ratio"]
    e, div, sink, vbar = emission_map(no2, u, v, lat, lon, tau_h * 3600, v_bg, ratio)
    masks, in_corr, r_src = zones(lat, lon, src, cfg)

    def totals(e_map):
        out = {name: integrate_kg_s(e_map, m, lat, lon) for name, m in masks.items()}
        out["corridor"] = integrate_kg_s(e_map, in_corr, lat, lon)
        out.update({f"r{R}km": integrate_kg_s(e_map, r_src <= R, lat, lon) for R in RADII_KM})
        return out

    main = totals(e)

    # Bootstrap over overpasses
    rng = np.random.default_rng(inv["de"]["seed"])
    draws = []
    for _ in range(inv["bootstrap"]):
        wts = np.bincount(rng.integers(0, len(no2), len(no2)), minlength=len(no2)).astype(float)
        e_b, *_ = emission_map(no2, u, v, lat, lon, tau_h * 3600, v_bg, ratio, weights=wts)
        draws.append(totals(e_b))
    ci = {k: [float(np.percentile([d[k] for d in draws], p)) for p in (2.5, 97.5)] for k in main}

    # Sensitivity
    sens = {}
    for label, t_h, bg in [("tau x0.7", tau_h * 0.7, v_bg), ("tau x1.3", tau_h * 1.3, v_bg),
                           ("tau / 0.84 (synthetic-bias corrected)", tau_h / 0.84, v_bg),
                           ("background p5", tau_h, float(np.nanpercentile(vbar_all, 5))),
                           ("background p25", tau_h, float(np.nanpercentile(vbar_all, 25)))]:
        e_s, *_ = emission_map(no2, u, v, lat, lon, t_h * 3600, bg, ratio)
        sens[label] = totals(e_s)
    other = "100" if lvl != "100" else "850"
    ok = met[f"u{other}"].notna().to_numpy()
    e_s, *_ = emission_map(no2[ok], met[f"u{other}"].to_numpy()[ok], met[f"v{other}"].to_numpy()[ok],
                           lat, lon, tau_h * 3600, v_bg, ratio)
    sens[f"wind level {other}"] = totals(e_s)

    emg_e = city["results"][0]["emission"]["e_nox_kg_s"]
    print(f"\nEMG city estimate: {emg_e:.3f} kg/s")
    print("Flux divergence, total within R km of the source:")
    for R in RADII_KM:
        k = f"r{R}km"
        print(f"  {R:2d} km: {main[k]:.3f} kg/s  [{ci[k][0]:.3f}, {ci[k][1]:.3f}]")
    print("Zones:")
    for k in list(masks) + ["corridor"]:
        print(f"  {CLUSTER_LABELS.get(k, k):32s} {main[k]:.3f} kg/s  [{ci[k][0]:.3f}, {ci[k][1]:.3f}]  "
              f"({main[k] * SECONDS_PER_YEAR / 1e6:.1f} kt/yr midday rate)")
    print("Sensitivity (corridor total, kg/s):", {k: round(v["corridor"], 3) for k, v in sens.items()})

    result = {"source": src, "tau_h": tau_h, "v_bg_mol_m2": v_bg, "wind_level": lvl, "n_overpasses": int(use.sum()),
              "emg_city_kg_s": emg_e, "totals_kg_s": main, "ci95_kg_s": ci, "sensitivity_kg_s": sens,
              "zone_pixels": {k: int(m.sum()) for k, m in masks.items()}, "corridor_pixels": int(in_corr.sum())}
    (OUT / "divergence_totals.json").write_text(json.dumps(result, indent=2))
    np.savez_compressed(OUT / "divergence_map.npz", e_nox_mol_m2_s=e, div=div, sink=sink, vbar=vbar, lat=lat, lon=lon)
    figures(e, lat, lon, src, main, ci, emg_e, masks)
    print(f"Saved {OUT / 'divergence_totals.json'}, divergence_map.npz and figures")


def figures(e, lat, lon, src, main, ci, emg_e, masks):
    # Map: t NOx / km2 / yr (midday rate), smoothed to ~3 km for display only
    to_t_km2_yr = M_NO2 * 1e6 * SECONDS_PER_YEAR / 1000
    shown = uniform_filter(np.nan_to_num(e), size=3) * to_t_km2_yr
    lim = np.nanpercentile(np.abs(shown), 99)
    fig, ax = plt.subplots(figsize=(6.6, 5.8))
    ext = [lon[0] - 0.005, lon[-1] + 0.005, lat[-1] - 0.005, lat[0] + 0.005]
    im = ax.imshow(shown, extent=ext, origin="upper", cmap=DIVERGING, norm=TwoSlopeNorm(0, -lim, lim), aspect="auto")
    cx, cy = corridor_polygon().exterior.xy
    ax.plot(cx, cy, color=INK, lw=1.2, label="Corridor")
    ax.plot(src[1], src[0], marker="o", ms=9, mfc=ORANGE, mec=SURFACE, mew=2, ls="none", label="EMG source (calm max)")
    ax.set_xlim(73.55, 74.10); ax.set_ylim(18.30, 18.90)
    ax.set_xlabel("Longitude (°E)"); ax.set_ylabel("Latitude (°N)"); ax.grid(False)
    ax.set_title("NOx emission from flux divergence (~3 km smoothing)", fontsize=11, loc="left")
    cb = fig.colorbar(im, ax=ax, shrink=0.85); cb.set_label("t NOx / km² / yr (midday rate)", color=INK2)
    cb.outline.set_edgecolor(GRID)
    ax.legend(loc="lower left", frameon=False)
    fig.tight_layout(); fig.savefig(FIG / "divergence_map.png"); plt.close(fig)

    # Consistency: cumulative total vs radius, with the EMG estimate as reference
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    tot = [main[f"r{R}km"] for R in RADII_KM]
    lo = [ci[f"r{R}km"][0] for R in RADII_KM]
    hi = [ci[f"r{R}km"][1] for R in RADII_KM]
    ax.fill_between(RADII_KM, lo, hi, color=BLUE, alpha=0.18, lw=0, label="95% bootstrap interval")
    ax.plot(RADII_KM, tot, "-o", color=BLUE, ms=6, mec=SURFACE, mew=1.5, label="Flux divergence, within R")
    ax.axhline(emg_e, color=ORANGE, ls="--", label=f"EMG city estimate ({emg_e:.2f} kg/s)")
    ax.set_xlabel("Radius around source (km)"); ax.set_ylabel("NOx emission (kg/s)")
    ax.set_ylim(bottom=0)
    ax.set_title("Two independent estimators: flux divergence vs EMG", fontsize=11, loc="left")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    fig.tight_layout(); fig.savefig(FIG / "divergence_vs_emg.png"); plt.close(fig)

    # Zone totals
    keys = ["pune_core", "C1_shivajinagar_kasarwadi", "C2_pcmc", "C3_dehu_talegaon"]
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    for i, k in enumerate(keys):
        col = CLUSTER_COLORS.get(k, INK2)
        ax.barh(i, main[k], color=col, height=0.55)
        ax.plot(ci[k], [i, i], color=INK, lw=1.5)
        ax.text(max(main[k], ci[k][1]) + 0.005, i, f"{main[k]:.3f}", va="center", fontsize=9, color=INK)
    ax.set_yticks(range(len(keys)), [f"{CLUSTER_LABELS[k]} ({masks[k].sum()} px)" for k in keys])
    ax.invert_yaxis(); ax.axvline(0, color=INK2, lw=1); ax.grid(axis="y", visible=False)
    ax.set_xlabel("NOx emission (kg/s), 95% CI")
    ax.set_title("NOx emission by zone (flux divergence)", fontsize=11, loc="left")
    fig.tight_layout(); fig.savefig(FIG / "divergence_zones.png"); plt.close(fig)


if __name__ == "__main__":
    run()
