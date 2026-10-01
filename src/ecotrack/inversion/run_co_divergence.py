"""
D16 feasibility test — a CO flux-divergence map as an NO₂-independent label source (L-co).

CO is inert on plume timescales, so its emission map is just the flux divergence (no sink term):
    E_CO = div(V' · w),   V' = terrain-normalised CO with the daily box median and each pixel's
                               long-term mean removed
Removing the static pattern is essential: Pune's winds are directional (mean wind ~1 m/s of a
3.4 m/s mean speed), so the fixed terrain imprint × the mean wind fakes a large divergence. With Pune's
real wind record on synthetic data: raw −70 mol/s fake signal at 25 km; static-removed ≈ 0 and
a source recovered at −12% (research log, 2026-10-01).

Checks against the NO₂ results: total vs the CO step (6.73 kg/s), hotspot locations, corridor share
(+ bootstrap noise), and cell-level agreement with the NO₂ flux-divergence shares.

Output: outputs/phase1/co_divergence.json, figures/co_divergence_map.png

Usage (after run_divergence, run_co_ratio):
    python -m ecotrack.inversion.run_co_divergence
"""

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from scipy.ndimage import maximum_filter, uniform_filter

from ecotrack.config import load_config
from ecotrack.geometry import corridor_polygon
from ecotrack.inversion.divergence import emission_map, integrate_kg_s
from ecotrack.inversion.emg import M_NO2, offsets_km
from ecotrack.inversion.run_city import FIG, GRID, INK, INK2, ORANGE, OUT, SURFACE, match_wind
from ecotrack.inversion.run_co_ratio import M_CO, SCALE_HEIGHT_KM, prepare_co
from ecotrack.inversion.run_divergence import zones

DIVERGING = LinearSegmentedColormap.from_list("div", ["#2a78d6", "#f0efec", "#e34948"])
N_BOOT = 100


def run():
    cfg = load_config()
    inv = cfg["inversion"]
    city = json.loads((OUT / "city_fit.json").read_text())
    co_ratio = json.loads((OUT / "co_ratio.json").read_text())
    src = (city["source_lat"], city["source_lon"])

    co, times, lat, lon, z = prepare_co(cfg)
    met, lvl = match_wind(times, cfg)
    ws = met[f"ws{lvl}"].to_numpy()
    use = met[f"u{lvl}"].notna().to_numpy() & (ws <= inv["windy_max_ms"])
    u, v = met[f"u{lvl}"].to_numpy()[use], met[f"v{lvl}"].to_numpy()[use]
    x = co[use] / np.exp(-z / (SCALE_HEIGHT_KM * 1000))[None]
    x = x - np.nanmedian(x.reshape(len(x), -1), axis=1)[:, None, None]
    x = x - np.nanmean(x, axis=0)[None]
    print(f"{use.sum()} CO overpasses (wind <= {inv['windy_max_ms']} m/s); mean wind u {u.mean():.2f}, v {v.mean():.2f} m/s")

    def emap_for(weights=None):
        e, *_ = emission_map(x, u, v, lat, lon, tau_s=1e15, v_bg=0.0, nox_no2_ratio=1.0, weights=weights)
        return e  # mol CO m-2 s-1

    e = emap_for()
    masks, in_corr, r_src = zones(lat, lon, src, cfg)
    mol_s = lambda m, emap=e: integrate_kg_s(emap, m, lat, lon) / M_NO2  # integrate_kg_s multiplies by M_NO2
    tot = {R: mol_s(r_src <= R) for R in (10, 15, 20, 25, 30, 35)}
    corr_share = mol_s(in_corr) / tot[25]

    rng = np.random.default_rng(inv["de"]["seed"])
    shares, totals = [], []
    for _ in range(N_BOOT):
        w = np.bincount(rng.integers(0, len(x), len(x)), minlength=len(x)).astype(float)
        eb = emap_for(w)
        t25 = integrate_kg_s(eb, r_src <= 25, lat, lon) / M_NO2
        totals.append(t25)
        shares.append(integrate_kg_s(eb, in_corr, lat, lon) / M_NO2 / t25)

    # Cell-level agreement with the NO2 flux-divergence map (both smoothed to ~5 km, TROPOMI CO footprint)
    no2_map = np.load(OUT / "divergence_map.npz")["e_nox_mol_m2_s"]
    a = uniform_filter(np.nan_to_num(e), 5)[r_src <= 25]
    b = uniform_filter(np.nan_to_num(no2_map), 5)[r_src <= 25]
    r_cells = float(np.corrcoef(a, b)[0, 1])

    s = uniform_filter(np.nan_to_num(e), 5)
    peaks = (s == maximum_filter(s, size=11)) & (s > np.percentile(s, 97))
    peak_list = sorted([(float(s[i, j]), float(lat[i]), float(lon[j])) for i, j in zip(*np.nonzero(peaks))], reverse=True)[:4]

    step = co_ratio["main"]["e_co_mol_s"]
    result = {"n": int(use.sum()), "totals_mol_s": tot, "co_step_mol_s": step,
              "ratio_25km_to_step": tot[25] / step, "corridor_share": corr_share,
              "corridor_share_boot_ci95": [float(np.percentile(shares, p)) for p in (2.5, 97.5)],
              "total25_boot_ci95": [float(np.percentile(totals, p)) for p in (2.5, 97.5)],
              "corr_with_no2_fd_cells_25km": r_cells, "peaks": peak_list,
              "no2_fd_corridor_share": json.loads((OUT / "divergence_totals.json").read_text())["totals_kg_s"]["corridor"]
              / json.loads((OUT / "divergence_totals.json").read_text())["totals_kg_s"]["r25km"]}
    (OUT / "co_divergence.json").write_text(json.dumps(result, indent=2, default=float))
    print("Total within R km (mol/s): " + ", ".join(f"{R}: {t:.0f}" for R, t in tot.items()))
    print(f"25 km: {tot[25]:.0f} mol/s ({tot[25] * M_CO:.2f} kg/s) vs CO step {step:.0f} mol/s -> ratio {tot[25] / step:.2f}; "
          f"bootstrap 95% {result['total25_boot_ci95'][0]:.0f}-{result['total25_boot_ci95'][1]:.0f}")
    print(f"Corridor share: CO {100 * corr_share:.1f}% [boot {100 * result['corridor_share_boot_ci95'][0]:.1f}-"
          f"{100 * result['corridor_share_boot_ci95'][1]:.1f}%] vs NO2 {100 * result['no2_fd_corridor_share']:.1f}%")
    print(f"Cell-level correlation with the NO2 FD map (5 km smoothing, within 25 km): r = {r_cells:.2f}")
    print("Top peaks (value, lat, lon):", [(f"{p[0]:.2e}", round(p[1], 3), round(p[2], 3)) for p in peak_list])

    lim = np.nanpercentile(np.abs(s), 99)
    fig, ax = plt.subplots(figsize=(6.6, 5.8))
    ext = [lon[0] - 0.005, lon[-1] + 0.005, lat[-1] - 0.005, lat[0] + 0.005]
    im = ax.imshow(s * M_CO * 1e6 * 31_557_600 / 1000, extent=ext, origin="upper", cmap=DIVERGING,
                   norm=TwoSlopeNorm(0, -lim * M_CO * 1e6 * 31_557_600 / 1000, lim * M_CO * 1e6 * 31_557_600 / 1000), aspect="auto")
    cx, cy = corridor_polygon().exterior.xy
    ax.plot(cx, cy, color=INK, lw=1.2, label="Corridor")
    ax.plot(src[1], src[0], "o", ms=9, mfc=ORANGE, mec=SURFACE, mew=2, ls="none", label="NO₂ source (Phase 1)")
    ax.set_xlim(73.55, 74.10); ax.set_ylim(18.30, 18.90); ax.grid(False)
    ax.set_xlabel("Longitude (°E)"); ax.set_ylabel("Latitude (°N)")
    cb = fig.colorbar(im, ax=ax, shrink=0.85); cb.set_label("t CO / km² / yr (midday rate)", color=INK2); cb.outline.set_edgecolor(GRID)
    ax.legend(loc="lower left", frameon=False)
    fig.suptitle("CO emission from flux divergence (terrain-normalised, static removed, ~5 km smoothing)",
                 fontsize=10, x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(FIG / "co_divergence_map.png"); plt.close(fig)


if __name__ == "__main__":
    run()
