"""
Phase 3 groundwork — can emissions be resolved per season, or only as a multi-year mean?

For each October–May season: the EMG city fit (same source, settings and wind as run_city) with a
bootstrap, and the flux-divergence corridor share. If the season-to-season differences are larger
than the per-season uncertainty, Phase 3 labels can vary by season. If not, labels must be a single
multi-year map (and time-varying features would have nothing real to explain).

Output: outputs/phase1/seasonal.json, figures/seasonal.png

Usage (after run_city):
    python -m ecotrack.inversion.run_seasonal
"""

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ecotrack.acquire.tropomi_cube import load_cube
from ecotrack.config import load_config
from ecotrack.inversion.divergence import emission_map, integrate_kg_s
from ecotrack.inversion.emg import RotatedGrid, bin_days, offsets_km
from ecotrack.inversion.run_city import BLUE, FIG, INK, ORANGE, OUT, SURFACE, fit_subset, match_wind
from ecotrack.inversion.run_divergence import zones

N_BOOT = 100


def season_of(ts):
    start = np.where(ts.month >= 10, ts.year, ts.year - 1)
    return pd.Index([f"{s}-{str(s + 1)[2:]}" for s in start])


def run():
    cfg = load_config()
    inv = cfg["inversion"]
    city = json.loads((OUT / "city_fit.json").read_text())
    src = (city["source_lat"], city["source_lon"])
    no2, times, lat, lon, _ = load_cube()
    met, lvl = match_wind(times, cfg)
    ws = met[f"ws{lvl}"].to_numpy()
    u, v = met[f"u{lvl}"].to_numpy(), met[f"v{lvl}"].to_numpy()
    has = met[f"u{lvl}"].notna().to_numpy()
    windy = has & (ws >= inv["windy_min_ms"]) & (ws <= inv["windy_max_ms"])
    seasons = season_of(pd.DatetimeIndex(times))

    grid = RotatedGrid.from_config(inv)
    dx, dy = offsets_km(lat, lon, *src)
    sums, cnts = bin_days(no2, np.nan_to_num(u), np.nan_to_num(v), dx, dy, grid)
    masks, in_corr, r_src = zones(lat, lon, src, cfg)
    tau_all = city["results"][0]["emission"]["tau_h"]
    vbar = np.nanmean(no2, axis=0)
    v_bg = float(np.nanpercentile(vbar, 10))
    rng = np.random.default_rng(inv["de"]["seed"])

    rows = []
    for s in sorted(set(seasons)):
        sel = windy & (seasons == s)
        res, *_ = fit_subset(sel, sums, cnts, grid, ws, inv, f"season {s}", n_boot=N_BOOT, rng=rng)
        e = res["emission"]
        fd_sel = has & (ws <= inv["windy_max_ms"]) & (seasons == s)
        emap, *_ = emission_map(no2[fd_sel], u[fd_sel], v[fd_sel], lat, lon, tau_all * 3600, v_bg, inv["nox_no2_ratio"])
        corr = integrate_kg_s(emap, in_corr, lat, lon)
        r25 = integrate_kg_s(emap, r_src <= 25, lat, lon)
        rows.append({"season": s, "n_windy": int(sel.sum()), "e_nox_kg_s": e["e_nox_kg_s"],
                     "ci95": res["bootstrap"]["e_nox_kg_s_ci95"], "tau_h": e["tau_h"], "r2": res["fit"]["r2"],
                     "at_bound": res["at_bound"], "corridor_share": corr / r25})
        r = rows[-1]
        print(f"{s}: n={r['n_windy']:3d}  E(NOx) {r['e_nox_kg_s']:.3f} [{r['ci95'][0]:.3f}-{r['ci95'][2]:.3f}] kg/s  "
              f"tau {r['tau_h']:.2f} h  R2 {r['r2']:.3f}  corridor share {100 * r['corridor_share']:.1f}%  {r['at_bound'] or ''}")

    e = np.array([r["e_nox_kg_s"] for r in rows])
    half_ci = np.array([(r["ci95"][2] - r["ci95"][0]) / 2 for r in rows])
    spread = float(e.std(ddof=1))
    typical_err = float(np.mean(half_ci) / 1.96)  # 95% half-width -> 1 sigma
    shares = np.array([r["corridor_share"] for r in rows])
    summary = {"seasons": rows, "between_season_sd_kg_s": spread, "mean_within_season_1sigma_kg_s": typical_err,
               "ratio_between_to_within": spread / typical_err,
               "corridor_share_range": [float(shares.min()), float(shares.max())]}
    (OUT / "seasonal.json").write_text(json.dumps(summary, indent=2, default=float))
    print(f"\nBetween-season SD {spread:.3f} kg/s vs typical within-season 1-sigma {typical_err:.3f} kg/s "
          f"(ratio {spread / typical_err:.1f}); corridor share {100 * shares.min():.1f}-{100 * shares.max():.1f}%")

    fig, ax = plt.subplots(figsize=(6.6, 3.4))
    for i, r in enumerate(rows):
        ax.plot([i, i], [r["ci95"][0], r["ci95"][2]], color=BLUE, lw=2)
        ax.plot(i, r["e_nox_kg_s"], "o", color=BLUE, ms=8, mec=SURFACE, mew=2)
    ax.axhline(city["results"][0]["emission"]["e_nox_kg_s"], color=ORANGE, ls="--", label=f"All seasons ({city['results'][0]['emission']['e_nox_kg_s']:.3f} kg/s)")
    ax.set_xticks(range(len(rows)), [r["season"] for r in rows])
    ax.set_ylabel("E(NOx) (kg/s), 95% CI"); ax.legend(frameon=False, fontsize=9)
    fig.suptitle("City NOx emission by season (EMG, bootstrap 95% CI)", fontsize=11, x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(FIG / "seasonal.png"); plt.close(fig)


if __name__ == "__main__":
    run()
