"""
D4 — TROPOMI CO/NOx emission ratio -> sector mix -> a better-constrained CO2:NOx ratio.

CO is inert on plume timescales, so downwind of a city the CO line density steps up by E_CO/w.
Estimator (robust to terrain and any other static pattern):
1. Terrain normalisation: CO column / exp(-z/H), z = SRTM elevation smoothed to the ~5 km
   TROPOMI CO footprint. Removes the Western Ghats air-mass imprint (~6%, larger than Pune's signal).
2. Per-day median over the box removed (regional day-to-day CO swings).
3. Each pixel's long-term mean removed. Anything fixed in space disappears, including the
   city's direction-averaged CO dome; only the wind-relative part survives.
4. Rotate by the day's wind; line density of the anomaly. Because the removed dome is symmetric
   about the source, L_anom(downwind) - L_anom(upwind) equals the full step E_CO * <1/w>.
5. E_CO = step / <1/w>. Bootstrap over days. Emission ratio CO:NOx (mol/mol) uses the EMG NOx.
6. Sector mix: two-group mixing. Sectors are grouped by EDGAR's OWN CO:NOx ratio (above the
   city average = "high-CO", else "low-CO"; not by assumption). The observed CO:NOx fixes the
   high-CO share of NOx, which with each group's CO2:NOx gives an implied city CO2:NOx ratio.
7. Scenario check (which sectors absorb the change): hold all other sectors at EDGAR shares and
   re-split one pair (industry/transport, residential/industry, residential/transport) to match the
   observed CO:NOx. Scenarios needing a share outside 0-1 are infeasible. The feasible scenarios
   give the CO-constrained CO2:NOx range, which replaces the base paper's 25% representativeness
   term in the uncertainty budget (plus an assumed 10% for EDGAR's per-sector ratios).

Usage (after acquire.tropomi_cube --product co, acquire.dem, acquire.edgar, run_city, run_co2):
    python -m ecotrack.inversion.run_co_ratio
"""

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.ndimage import uniform_filter

from ecotrack.acquire.tropomi_cube import load_cube
from ecotrack.config import DATA_INTERIM, load_config
from ecotrack.inversion.emg import M_NO2, RotatedGrid, bin_days, line_density, offsets_km
from ecotrack.inversion.run_city import BLUE, FIG, INK, INK2, ORANGE, OUT, SURFACE, match_wind
from ecotrack.inversion.run_co2 import RADIUS_KM, edgar, fine_mask, _offs

M_CO = 28.0101e-3
SCALE_HEIGHT_KM = 8.4
FOOTPRINT_PX = 5            # ~5 km smoothing of elevation to match TROPOMI CO pixels
UPWIND = (-40, -20)         # km, plateau windows for the step
DOWNWIND = (20, 40)


def prepare_co(cfg):
    co, t_co, lat, lon, _ = load_cube("co")
    dem = np.load(DATA_INTERIM / "dem_cube_grid.npz")["elevation_m"]
    z = uniform_filter(dem, size=FOOTPRINT_PX)
    return co, t_co, lat, lon, z


def anomalies(co, z, H_km):
    x = co / np.exp(-z / (H_km * 1000))[None]
    x = x - np.nanmedian(x.reshape(len(x), -1), axis=1)[:, None, None]
    return x - np.nanmean(x, axis=0)[None]


def step_from(sums, cnts, grid, weights=None):
    L, field = line_density(sums, cnts, grid, weights)
    a = grid.along
    up = np.nanmean(L[(a >= UPWIND[0]) & (a <= UPWIND[1])])
    down = np.nanmean(L[(a >= DOWNWIND[0]) & (a <= DOWNWIND[1])])
    return down - up, L, field


def run():
    cfg = load_config()
    inv = cfg["inversion"]
    city = json.loads((OUT / "city_fit.json").read_text())
    co2 = json.loads((OUT / "co2_summary.json").read_text())
    src = (city["source_lat"], city["source_lon"])
    e_nox_kg_s = city["results"][0]["emission"]["e_nox_kg_s"]
    e_nox_mol_s = e_nox_kg_s / M_NO2

    co, times, lat, lon, z = prepare_co(cfg)
    met, lvl = match_wind(times, cfg)
    ws = met[f"ws{lvl}"].to_numpy()
    use = met[f"u{lvl}"].notna().to_numpy() & (ws >= inv["windy_min_ms"]) & (ws <= inv["windy_max_ms"])
    u, v = met[f"u{lvl}"].to_numpy(), met[f"v{lvl}"].to_numpy()
    months = pd.DatetimeIndex(times).month
    print(f"{len(times)} CO overpasses; {use.sum()} windy ({inv['windy_min_ms']}-{inv['windy_max_ms']} m/s)")

    grid = RotatedGrid.from_config(inv)
    dx, dy = offsets_km(lat, lon, *src)

    def estimate(H_km, sel, n_boot=0, rng=None):
        an = anomalies(co, z, H_km)
        sums, cnts = bin_days(an[sel], u[sel], v[sel], dx, dy, grid)
        inv_w = np.mean(1 / ws[sel])
        step, L, field = step_from(sums, cnts, grid)
        e = step / inv_w  # mol/s
        out = {"n": int(sel.sum()), "step_mol_m": float(step), "e_co_mol_s": float(e),
               "e_co_kg_s": float(e * M_CO), "ratio_co_nox_mol": float(e / e_nox_mol_s)}
        if n_boot:
            draws = []
            n = int(sel.sum())
            for _ in range(n_boot):
                wts = np.bincount(rng.integers(0, n, n), minlength=n).astype(float)
                s_b, _, _ = step_from(sums, cnts, grid, wts)
                iw = np.sum(wts / ws[sel]) / wts.sum()
                draws.append(s_b / iw / e_nox_mol_s)
            out["ratio_ci95"] = [float(np.percentile(draws, p)) for p in (2.5, 97.5)]
            out["ratio_se"] = float(np.std(draws))
        return out, L, field

    rng = np.random.default_rng(inv["de"]["seed"])
    main, L_main, field_main = estimate(SCALE_HEIGHT_KM, use, n_boot=inv["bootstrap"], rng=rng)
    print(f"MAIN: CO step {main['step_mol_m']:.2f} mol/m -> E_CO {main['e_co_kg_s']:.2f} kg/s; "
          f"CO:NOx = {main['ratio_co_nox_mol']:.2f} mol/mol [{main['ratio_ci95'][0]:.2f}, {main['ratio_ci95'][1]:.2f}]")

    sens = {}
    for label, H, sel in [("H = 7.5 km", 7.5, use), ("H = 9.5 km", 9.5, use),
                          ("no terrain correction", 1e9, use),
                          ("Oct-Jan only", SCALE_HEIGHT_KM, use & np.isin(months, [10, 11, 12, 1])),
                          ("Feb-May only (fire season)", SCALE_HEIGHT_KM, use & np.isin(months, [2, 3, 4, 5]))]:
        r, _, _ = estimate(H, sel)
        sens[label] = r
        print(f"  {label:28s} n={r['n']:4d}  CO:NOx = {r['ratio_co_nox_mol']:.2f}")

    # ---------------- EDGAR sector ratios over the same area, and the two-group mixing model
    lat_e, lon_e, _ = edgar("NOx", 2021)
    w_city = fine_mask(lat_e, lon_e, 0.1, lambda la, lo: np.hypot(*_offs(la, lo, src)) <= RADIUS_KM)
    tot = lambda sp, s: (float((edgar(sp, 2021, s)[2] * w_city).sum()) if edgar(sp, 2021, s) else 0.0)
    sectors = [s for s in co2["edgar_sectors_2021"]]
    per = {s: {"nox": tot("NOx", s), "co": tot("CO", s), "co2": tot("CO2", s)} for s in sectors}
    for s, d in per.items():
        d["co_nox_mol"] = (d["co"] / 28.0101) / (d["nox"] / 46.0055) if d["nox"] > 1 else None
    edgar_city_ratio = (sum(d["co"] for d in per.values()) / 28.0101) / (sum(d["nox"] for d in per.values()) / 46.0055)
    # Group by EDGAR's own ratios; sectors with (almost) no NOx don't affect the NOx mix -> "low"
    high = [s for s, d in per.items() if d["nox"] > 100 and d["co_nox_mol"] and d["co_nox_mol"] > edgar_city_ratio]
    grp = {g: {k: sum(per[s][k] for s in sectors if (s in high) == (g == "high")) for k in ("nox", "co", "co2")}
           for g in ("high", "low")}
    grp["high"]["sectors"] = high
    for g in grp.values():
        g.setdefault("sectors", [])
        g["co_nox_mol"] = (g["co"] / 28.0101) / (g["nox"] / 46.0055)
        g["co2_nox"] = g["co2"] / g["nox"]
    edgar_mix = grp["high"]["nox"] / (grp["high"]["nox"] + grp["low"]["nox"])

    def mix(r_obs):
        a = (r_obs - grp["low"]["co_nox_mol"]) / (grp["high"]["co_nox_mol"] - grp["low"]["co_nox_mol"])
        a_c = float(np.clip(a, 0, 1))
        return float(a), a_c, a_c * grp["high"]["co2_nox"] + (1 - a_c) * grp["low"]["co2_nox"]

    alpha, alpha_c, r_co2 = mix(main["ratio_co_nox_mol"])
    lo_ci, hi_ci = main["ratio_ci95"]
    _, _, r_co2_lo = mix(lo_ci)
    _, _, r_co2_hi = mix(hi_ci)
    # Scenario check: re-split one sector pair, others fixed at EDGAR shares
    nox = {k: d["nox"] for k, d in per.items() if d["nox"] > 1}
    share = {k: n / sum(nox.values()) for k, n in nox.items()}
    cr = {k: per[k]["co_nox_mol"] or 0.0 for k in nox}
    c2 = {k: per[k]["co2"] / per[k]["nox"] for k in nox}

    def split(a, b, target):
        fixed = {k: v for k, v in share.items() if k not in (a, b)}
        pool = share[a] + share[b]
        f = ((target - sum(fixed[k] * cr[k] for k in fixed)) / pool - cr[b]) / (cr[a] - cr[b])
        fc = min(max(f, 0.0), 1.0)
        new = dict(fixed, **{a: pool * fc, b: pool * (1 - fc)})
        return f, sum(new[k] * c2[k] for k in new)

    scenarios = {"A: high-CO group vs rest": {"feasible": 0 <= alpha <= 1, "co2_nox": r_co2,
                                              "co2_nox_ci": sorted([r_co2_lo, r_co2_hi])}}
    for label, a, b in (("B: industry vs transport", "IND", "TRO"), ("C: residential vs industry", "RCO", "IND"),
                        ("D: residential vs transport", "RCO", "TRO")):
        f, rc = split(a, b, main["ratio_co_nox_mol"])
        rng_ci = sorted(split(a, b, t)[1] for t in main["ratio_ci95"])
        scenarios[label] = {"fraction_a": f, "feasible": 0 <= f <= 1, "co2_nox": rc, "co2_nox_ci": rng_ci,
                            "edgar_fraction_a": share[a] / (share[a] + share[b])}
    feas = [v for v in scenarios.values() if v["feasible"]]
    r_lo = min(v["co2_nox_ci"][0] for v in feas)
    r_hi = max(v["co2_nox_ci"][1] for v in feas)
    r_central = float(np.mean([v["co2_nox"] for v in feas]))
    co2_new = co2["satellite_nox_kt_yr_midday"] * r_central / 1000

    # Revised uncertainty budget: swap the 25% representativeness term for the CO-constrained spread
    budget = dict(co2["uncertainty_budget_rel_1sigma"])
    old_key = next(k for k in budget if k.startswith("EDGAR ratio representativeness"))
    budget.pop(old_key)
    budget["CO2:NOx from TROPOMI CO scenarios (half-range of feasible 95% CIs)"] = (r_hi - r_lo) / 2 / r_central
    budget["EDGAR per-sector ratios (assumed)"] = 0.10
    total_new = float(np.sqrt(sum(v**2 for v in budget.values())))

    result = {
        "source": src, "scale_height_km": SCALE_HEIGHT_KM, "windows_km": {"upwind": UPWIND, "downwind": DOWNWIND},
        "main": main, "sensitivity": sens,
        "edgar_2021_sectors": per, "edgar_groups": grp, "edgar_high_co_share_of_nox": edgar_mix,
        "edgar_city_co_nox_mol": edgar_city_ratio,
        "implied_high_co_share_of_nox": alpha, "implied_share_clipped": alpha_c,
        "implied_co2_nox_ratio": r_co2, "implied_co2_nox_ratio_from_ci": [r_co2_lo, r_co2_hi],
        "edgar_co2_nox_ratio": co2["ratio_co2_per_nox_mean"],
        "scenarios": scenarios, "co2_nox_co_constrained": {"central": r_central, "range_95": [r_lo, r_hi]},
        "co2_mt_yr_co_constrained": co2_new,
        "co2_mt_yr_co_constrained_range_1sigma": [co2_new * (1 - total_new), co2_new * (1 + total_new)],
        "uncertainty_budget_rel_1sigma_revised": budget, "uncertainty_total_rel_1sigma_revised": total_new,
        "uncertainty_total_rel_1sigma_before": co2["uncertainty_total_rel_1sigma"],
    }
    (OUT / "co_ratio.json").write_text(json.dumps(result, indent=2, default=float))
    print("EDGAR 2021 sector CO:NOx (mol/mol) and CO2:NOx (t/t):",
          {s: (round(d["co_nox_mol"], 2) if d["co_nox_mol"] else None, round(d["co2"] / d["nox"]) if d["nox"] > 1 else None)
           for s, d in per.items() if d["nox"] > 100})
    print(f"High-CO group (by EDGAR's own ratios): {grp['high']['sectors']}")
    print(f"\nEDGAR (within {RADIUS_KM} km) CO:NOx = {edgar_city_ratio:.2f} mol/mol; high-CO group "
          f"{grp['high']['co_nox_mol']:.2f}, low-CO group {grp['low']['co_nox_mol']:.2f}; "
          f"EDGAR high-CO share of NOx {100 * edgar_mix:.0f}%")
    print(f"Implied high-CO share of NOx: {100 * alpha:.0f}% (EDGAR {100 * edgar_mix:.0f}%)")
    for k, v in scenarios.items():
        fa = f"  share {v['fraction_a']:.2f} (EDGAR {v['edgar_fraction_a']:.2f})" if "fraction_a" in v else ""
        print(f"  {k:30s} {'feasible' if v['feasible'] else 'INFEASIBLE':10s} CO2:NOx {v['co2_nox']:.0f} "
              f"[{v['co2_nox_ci'][0]:.0f}-{v['co2_nox_ci'][1]:.0f}]{fa}")
    print(f"CO-constrained CO2:NOx {r_central:.0f} (95% range {r_lo:.0f}-{r_hi:.0f}) vs EDGAR {co2['ratio_co2_per_nox_mean']:.0f}"
          f" -> city CO2 {co2_new:.2f} Mt/yr (EDGAR-ratio estimate {co2['satellite_co2_mt_yr_midday']:.2f})")
    print(f"Uncertainty (1 sigma): {100 * co2['uncertainty_total_rel_1sigma']:.1f}% -> {100 * total_new:.1f}%")
    for k, v in budget.items():
        print(f"  {k:66s} {100 * v:5.1f}%")
    figures(grid, L_main, field_main, result)


def figures(grid, L, field, r):
    fig, ax = plt.subplots(figsize=(7, 3.8))
    a = grid.along
    ax.plot(a, L, "o-", color=BLUE, ms=4, mec=SURFACE, mew=1, lw=1.5, label="CO anomaly line density")
    for (x0, x1), lab in ((UPWIND, "upwind plateau"), (DOWNWIND, "downwind plateau")):
        sel = (a >= x0) & (a <= x1)
        ax.hlines(np.nanmean(L[sel]), x0, x1, color=ORANGE, lw=3)
        ax.text((x0 + x1) / 2, np.nanmean(L[sel]) - 2, lab, ha="center", va="top", fontsize=8, color=INK2)
    ax.axvline(0, color=INK, lw=1, ls=":")
    m = r["main"]
    ax.text(0.01, 0.97, f"step = {m['step_mol_m']:.2f} mol/m  →  E(CO) = {m['e_co_kg_s']:.2f} kg/s\n"
            f"CO:NOx = {m['ratio_co_nox_mol']:.2f} mol/mol [{m['ratio_ci95'][0]:.2f}–{m['ratio_ci95'][1]:.2f}], n = {m['n']}",
            transform=ax.transAxes, va="top", fontsize=9, color=INK)
    ax.set_xlabel("Distance along wind (km, + = downwind)"); ax.set_ylabel("CO anomaly line density (mol/m)")
    fig.suptitle("TROPOMI CO: downwind step over Pune (terrain-normalised, static pattern removed)",
                 fontsize=11, x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(FIG / "co_step.png"); plt.close(fig)


if __name__ == "__main__":
    run()
