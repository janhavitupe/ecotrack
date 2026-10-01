"""
Proposal Phase 1 step 4: Differential Evolution settings "sensitivity-tested, not treated as fixed
constants". Refits the main EMG line density over a grid of DE settings and seeds and reports how
much the emission, lifetime and fit quality move.

The cost function is vectorised (scipy's `vectorized=True`: the whole population is evaluated in
one call) purely for speed; the DE algorithm is unchanged.

Usage (after run_city; uses the same cube, IQR filter, wind and source):
    python -m ecotrack.inversion.de_sensitivity
"""

import itertools
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import differential_evolution

from ecotrack.acquire.tropomi_cube import load_cube
from ecotrack.config import load_config
from ecotrack.inversion.emg import (PARAMS, RotatedGrid, bin_days, default_bounds, emg_model, emissions, param_names,
                                    line_density, offsets_km)
from ecotrack.inversion.run_city import BLUE, FIG, INK, INK2, ORANGE, OUT, SURFACE, fit_window, match_wind

POPSIZE = [30, 60]                       # x 5 parameters -> NP 150, 300 (proposal: 300); x 6 with the D19 slope
MUTATION = [(0.5, 1.0), 0.5, 0.9]        # proposal: F in [0.5, 1.0] (dithered)
RECOMBINATION = [0.3, 0.7, 0.9]          # proposal: CR 0.7
SEEDS = [1, 2]


def main_line_density(cfg):
    inv = cfg["inversion"]
    city = json.loads((OUT / "city_fit.json").read_text())
    no2, times, lat, lon, _ = load_cube()
    met, lvl = match_wind(times, cfg)
    ws = met[f"ws{lvl}"].to_numpy()
    sel = met[f"u{lvl}"].notna().to_numpy() & (ws >= inv["windy_min_ms"]) & (ws <= inv["windy_max_ms"])
    grid = RotatedGrid.from_config(inv)
    dx, dy = offsets_km(lat, lon, city["source_lat"], city["source_lon"])
    s, c = bin_days(no2[sel], met[f"u{lvl}"].to_numpy()[sel], met[f"v{lvl}"].to_numpy()[sel], dx, dy, grid)
    L, _ = line_density(s, c, grid)
    m = fit_window(grid, inv)
    return grid.along[m], L[m], float(ws[sel].mean()), inv, city


def run():
    cfg = load_config()
    x, L, w, inv, city = main_line_density(cfg)
    ok = np.isfinite(L)
    x, L = x[ok], L[ok]
    sloped = bool(inv.get("background_slope", False))
    names = param_names(sloped)
    bounds = default_bounds(x, L, sloped)
    scale = np.nanmax(np.abs(L))

    def cost(P):  # P: (n_params, S) population
        cols = [P[i][:, None] for i in range(len(names))]
        return np.sum(((emg_model(x[None, :], *cols) - L[None, :]) / scale) ** 2, axis=1)

    rows = []
    for pop, mut, cr, seed in itertools.product(POPSIZE, MUTATION, RECOMBINATION, SEEDS):
        res = differential_evolution(cost, bounds, popsize=pop, mutation=mut, recombination=cr, seed=seed,
                                     maxiter=inv["de"]["maxiter"], tol=1e-10, polish=True, vectorized=True,
                                     updating="deferred")
        p = dict(zip(names, res.x))
        e = emissions(p["a"], p["x0"], w, inv["nox_no2_ratio"])
        resid = L - emg_model(x, *res.x)
        rows.append({"NP": pop * len(names), "F": str(mut), "CR": cr, "seed": seed, "e_nox_kg_s": e.e_nox_kg_s,
                     "tau_h": e.tau_h, "x0_km": p["x0"], "r2": float(1 - np.sum(resid**2) / np.sum((L - L.mean()) ** 2)),
                     "cost": float(res.fun), "nfev": int(res.nfev), "converged": bool(res.success)})
        r = rows[-1]
        print(f"NP {r['NP']:3d}  F {r['F']:10s}  CR {cr:.1f}  seed {seed}  E {r['e_nox_kg_s']:.4f} kg/s  "
              f"tau {r['tau_h']:.3f} h  R2 {r['r2']:.4f}  nfev {r['nfev']:6d}  {'ok' if r['converged'] else 'NOT CONVERGED'}")

    e = np.array([r["e_nox_kg_s"] for r in rows])
    t = np.array([r["tau_h"] for r in rows])
    conv = np.array([r["converged"] for r in rows])
    # With the 6-parameter (D19 sloped) model, low-crossover runs (CR 0.3) can hit maxiter before converging;
    # report the converged fits separately (they all reach the same optimum).
    conv_stats = {"n_converged": int(conv.sum()),
                  "e_spread_rel_converged": float((e[conv].max() - e[conv].min()) / e[conv].mean()) if conv.any() else None,
                  "unconverged_settings": sorted({f"NP {r['NP']} F {r['F']} CR {r['CR']}" for r in rows if not r["converged"]})}
    ref = city["results"][0]["emission"]
    summary = {"n_fits": len(rows), "grid": {"NP": [p * 5 for p in POPSIZE], "F": [str(m) for m in MUTATION],
                                              "CR": RECOMBINATION, "seeds": SEEDS},
               "e_nox_kg_s": {"min": float(e.min()), "max": float(e.max()), "spread_rel": float((e.max() - e.min()) / ref["e_nox_kg_s"])},
               "tau_h": {"min": float(t.min()), "max": float(t.max()), "spread_rel": float((t.max() - t.min()) / ref["tau_h"])},
               "all_converged": all(r["converged"] for r in rows), "converged_only": conv_stats,
               "reference_main_fit": ref, "fits": rows}
    (OUT / "de_sensitivity.json").write_text(json.dumps(summary, indent=2))
    print(f"\n{len(rows)} fits: E(NOx) {e.min():.4f}-{e.max():.4f} kg/s (spread {100 * summary['e_nox_kg_s']['spread_rel']:.2f}% of main), "
          f"tau {t.min():.3f}-{t.max():.3f} h (spread {100 * summary['tau_h']['spread_rel']:.2f}%); all converged: {summary['all_converged']}")
    print(f"Converged fits: {conv_stats['n_converged']} of {len(rows)}, E spread {100 * (conv_stats['e_spread_rel_converged'] or 0):.4f}%; "
          f"unconverged settings: {conv_stats['unconverged_settings']}")

    fig, ax = plt.subplots(figsize=(7, 3.2))
    labels = [f"NP {r['NP']} · F {r['F']} · CR {r['CR']}" for r in rows]
    uniq = list(dict.fromkeys(labels))
    for i, lab in enumerate(uniq):
        vals = [r["e_nox_kg_s"] for r, l2 in zip(rows, labels) if l2 == lab]
        ax.plot([i] * len(vals), vals, "o", color=BLUE, ms=5, mec=SURFACE, mew=1)
    ax.axhline(ref["e_nox_kg_s"], color=ORANGE, ls="--", lw=1.5, label=f"Main fit ({ref['e_nox_kg_s']:.3f} kg/s)")
    ax.set_xticks(range(len(uniq)), uniq, rotation=90, fontsize=6)
    ax.set_ylabel("E(NOx) (kg/s)"); ax.legend(frameon=False, fontsize=9)
    pad = max(0.002, 2 * (e.max() - e.min()))
    ax.set_ylim(ref["e_nox_kg_s"] - pad, ref["e_nox_kg_s"] + pad)
    fig.suptitle(f"DE settings sensitivity: {len(rows)} fits, spread {100 * summary['e_nox_kg_s']['spread_rel']:.2f}%",
                 fontsize=11, x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(FIG / "de_sensitivity.png"); plt.close(fig)


if __name__ == "__main__":
    run()
