"""
Phase 4 — the model table: season-mean features joined to labels, plus the cross-validation splits.

Steps (docs/phase5_analysis_plan.md §1, §4):
1. Average the monthly features over each season's months. Wind direction is circular, so it
   becomes sin/cos of the direction, averaged as vectors.
2. Join the Phase 3 labels on (cell_id, season).
3. Block size from the correlation range of the label *errors* (analysis plan §4.1, amendment 1):
   rebuild the NO2 emission map from bootstrap resamples of the overpasses, sample each at the cells
   (5 km smoothing, as the labels), and compute the variogram of (resample - main) averaged over
   resamples. Its practical range (95% of the sill), rounded up, at least 5 km, is the block size.
   Why errors, not the label itself: the label is smooth at every scale (its variogram, even after
   removing the distance trend, keeps rising to 30 km on the regional grid, so a "range" is undefined
   and the first rule returned 100 km blocks). Copying the smooth *signal* from neighbouring cells is
   what the geography-only null N0 measures, and every experiment is scored as skill above N0; blocks
   must stop neighbouring cells sharing *label errors*. The label variogram is still drawn, descriptively.
4. Splits:
   fold_block     spatial blocks of that size, assigned to K folds balanced by cell count (all seasons
                  of a cell stay together)
   split_corridor "train" = cells outside the corridor, "test" = corridor cells
   split_pcmc     "test" = cluster C2 (PCMC), "train" = cells more than `pcmc_buffer_km` from any C2 cell,
                  "gap" = the buffer (unused)
   (leave-one-season-out needs no column: it uses `season`)

Output: data/processed/model_table_v1{SUFFIX}.csv (+ .meta.json), outputs/phase4{SUFFIX}/variogram.png

Usage (after features and labels on the same grid):
    $env:ECOTRACK_GRID="region"; python -m ecotrack.tensor
"""

import hashlib
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy.spatial.distance import pdist
from sklearn.isotonic import IsotonicRegression

from ecotrack.config import OUTPUTS, ROOT, load_config
from ecotrack.features import FEATURES
from ecotrack.grid import SUFFIX, load_cells
from ecotrack.inversion.divergence import integrate_kg_s
from ecotrack.inversion.emg import M_NO2
from ecotrack.inversion.run_city import BLUE, GRID, INK2, ORANGE, SURFACE
from ecotrack.inversion.run_divergence import zones
from ecotrack.labels import density_from_map, no2_inputs, no2_map

VERSION = "v1"
OUT_CSV = ROOT / "data" / "processed" / f"model_table_{VERSION}{SUFFIX}.csv"
OUT = OUTPUTS / f"phase4{SUFFIX}"
STATIC = ["road_major_km", "road_mid_km", "road_minor_km", "road_total_km", "industrial_frac"]


def season_features(ft):
    """Season means of the monthly features; wind direction as averaged sin/cos."""
    ft = ft.copy()
    rad = np.radians(ft["wd850"])
    ft["wd850_sin"], ft["wd850_cos"] = np.sin(rad), np.cos(rad)
    cols = [f for f in FEATURES if f != "wd850"] + ["wd850_sin", "wd850_cos"]
    g = ft.groupby(["cell_id", "season"])
    out = g[cols].mean()
    out["n_months"] = g.size()
    out = out.reset_index()
    norm = np.hypot(out.wd850_sin, out.wd850_cos)  # back to unit vectors (direction only)
    out["wd850_sin"], out["wd850_cos"] = out.wd850_sin / norm, out.wd850_cos / norm
    return out


def detrend(y, dist):
    """Remove the smooth decline of the label with distance to the source (isotonic, decreasing)."""
    iso = IsotonicRegression(increasing=False, out_of_bounds="clip").fit(dist, y)
    return y - iso.predict(dist)


def variogram(x_km, y_km, z, max_km=30.0, bin_km=1.0):
    """Empirical semivariance in distance bins (all pairs)."""
    d = pdist(np.column_stack([x_km, y_km]))
    g = 0.5 * pdist(z[:, None], metric="sqeuclidean")
    edges = np.arange(0, max_km + bin_km, bin_km)
    idx = np.digitize(d, edges) - 1
    keep = (idx >= 0) & (idx < len(edges) - 1)
    sums = np.bincount(idx[keep], weights=g[keep], minlength=len(edges) - 1)
    cnts = np.bincount(idx[keep], minlength=len(edges) - 1)
    centres = edges[:-1] + bin_km / 2
    ok = cnts > 0
    return centres[ok], sums[ok] / cnts[ok], cnts[ok]


def exp_model(h, nugget, sill, rng):
    return nugget + sill * (1 - np.exp(-3 * h / rng))  # rng = practical range (95% of the sill)


def block_size_km(h, gamma, var, min_km):
    """Block size = the larger of (a) the fitted exponential practical range and (b) the first lag where
    the empirical semivariance reaches 95% of the data variance (the theoretical sill); rounded up to a
    whole km, at least min_km. Rule (b) guards against a poor model fit, e.g. the 'hole effect' of a
    narrow, elongated domain like the corridor (fixed 2026-10-10, before the regional result was seen)."""
    g = gamma / var  # fit in units of the sill: raw error semivariances are ~1e-18, too small for the optimiser
    p, _ = curve_fit(exp_model, h, g, p0=[0.0, 1.0, 5.0], bounds=([0, 0, 0.5], [np.inf, np.inf, 100]))
    p = np.array([p[0] * var, p[1] * var, p[2]])
    reach = h[gamma >= 0.95 * var]
    first = float(reach[0]) if len(reach) else float(h.max())
    return max(min_km, int(np.ceil(max(p[2], first)))), p, first


def label_noise_variogram(cfg, cells, n_draws, max_km):
    """Variogram of the L-fd share error field: bootstrap NO2 maps minus the main map, at the cells."""
    k = cfg["phase3"]["smoothing_px"]
    dn = no2_inputs(cfg)
    lat, lon = dn["lat"], dn["lon"]
    _, _, r_src = zones(lat, lon, dn["src"], cfg)
    e = no2_map(dn)
    main = density_from_map(e, integrate_kg_s(e, r_src <= 25, lat, lon), k, lat, lon, cells, M_NO2)
    rng = np.random.default_rng(cfg["phase4"]["seed"])
    gams = []
    for _ in range(n_draws):
        w = np.bincount(rng.integers(0, len(dn["x"]), len(dn["x"])), minlength=len(dn["x"])).astype(float)
        eb = no2_map(dn, weights=w)
        d = density_from_map(eb, integrate_kg_s(eb, r_src <= 25, lat, lon), k, lat, lon, cells, M_NO2) - main
        h, g, _ = variogram(cells.x_utm.to_numpy() / 1000, cells.y_utm.to_numpy() / 1000, d, max_km=max_km)
        gams.append(g)
    return h, np.mean(gams, axis=0)


def block_folds(tab, blk_km, k, seed):
    """Square spatial blocks of blk_km and their fold (0..k-1). Blocks (partial at the domain edge) go,
    largest first, to the fold with the fewest cells so far; a seeded shuffle breaks ties. (Random
    assignment gave folds of 207-1,057 cells on the regional grid.) Also used by Phase 5 for the
    10/20 km robustness folds (analysis plan §4.2)."""
    bx = np.floor(tab.x_utm / (blk_km * 1000)).astype(int)
    by = np.floor(tab.y_utm / (blk_km * 1000)).astype(int)
    block_id = bx.astype(str) + "_" + by.astype(str)
    cells = pd.DataFrame({"cell_id": tab.cell_id, "block_id": block_id}).drop_duplicates("cell_id")
    size_of = cells.groupby("block_id").size()
    rng = np.random.default_rng(seed)
    order = sorted(rng.permutation(np.array(sorted(size_of.index))), key=lambda b_: -size_of[b_])
    load, fold_of = np.zeros(k), {}
    for b_ in order:
        f = int(np.argmin(load))
        fold_of[b_] = f
        load[f] += size_of[b_]
    return block_id, block_id.map(fold_of)


def build():
    cfg = load_config()
    p4 = cfg["phase4"]
    cells = load_cells()
    OUT.mkdir(parents=True, exist_ok=True)

    ft = pd.read_csv(ROOT / "data" / "processed" / f"feature_table_v2{SUFFIX}.csv")
    lab = pd.read_csv(ROOT / "data" / "processed" / f"labels_v1{SUFFIX}.csv")
    sf = season_features(ft)
    ctx = [c for c in ["x_utm", "y_utm", "lat", "lon", "cluster", "in_corridor", "corridor_cell_id", "dist_to_source_km"] if c in cells]
    tab = (lab.drop(columns="cluster").merge(sf, on=["cell_id", "season"], how="left")
           .merge(cells[["cell_id"] + ctx], on="cell_id", how="left"))
    if "in_corridor" not in tab:
        tab["in_corridor"] = True
    assert tab[[f for f in FEATURES if f != "wd850"]].notna().all().all(), "missing features after the join"

    # ---- variogram -> block size
    cm = tab.groupby("cell_id").agg(label=("label_fd", "mean"), x=("x_utm", "first"), y=("y_utm", "first"),
                                    dist=("dist_to_source_km", "first")).reset_index()
    resid = detrend(cm.label.to_numpy(), cm.dist.to_numpy())
    h_res, gam_res, _ = variogram(cm.x / 1000, cm.y / 1000, resid, max_km=p4["variogram_max_km"])  # descriptive
    h_raw, gam_raw, _ = variogram(cm.x / 1000, cm.y / 1000, cm.label.to_numpy() - cm.label.mean(), max_km=p4["variogram_max_km"])
    print(f"Label-error variogram ({p4['noise_draws']} bootstrap maps) ...")
    h, gam = label_noise_variogram(cfg, cells, p4["noise_draws"], p4["variogram_max_km"])
    tail = gam[h >= p4["variogram_max_km"] / 2]  # the error field has no trend, so it levels off: its sill
    blk, params, first_cross = block_size_km(h, gam, float(np.mean(tail)), p4["min_block_km"])

    # ---- splits
    tab["block_id"], tab["fold_block"] = block_folds(tab, blk, p4["k_folds"], p4["seed"])
    blocks = tab.block_id.unique()
    tab["split_corridor"] = np.where(tab.in_corridor, "test", "train")
    c2 = tab.loc[tab.cluster == "C2_pcmc", ["x_utm", "y_utm"]].drop_duplicates().to_numpy()
    d_c2 = np.min(np.hypot(tab.x_utm.to_numpy()[:, None] - c2[None, :, 0], tab.y_utm.to_numpy()[:, None] - c2[None, :, 1]), axis=1) / 1000
    tab["split_pcmc"] = np.where(tab.cluster == "C2_pcmc", "test", np.where(d_c2 > p4["pcmc_buffer_km"], "train", "gap"))

    tab.to_csv(OUT_CSV, index=False)
    per_fold = tab.drop_duplicates("cell_id").groupby("fold_block").size().to_dict()
    meta = {"version": VERSION, "grid": SUFFIX or "corridor", "rows": len(tab), "cells": int(tab.cell_id.nunique()),
            "seasons": sorted(tab.season.unique()),
            "variogram": {"target": "L-fd share error field (bootstrap maps - main map), averaged over draws",
                          "noise_draws": p4["noise_draws"],
                          "nugget": params[0], "sill": params[1], "practical_range_km": params[2],
                          "first_lag_reaching_95pct_variance_km": first_cross, "label_detrended_variance_descriptive": float(np.var(resid)),
                          "block_km": blk, "n_blocks": int(len(blocks)),
                          "effective_independent_areas": float(tab.drop_duplicates("cell_id").shape[0] / blk ** 2)},
            "cells_per_fold": {int(k): int(v) for k, v in per_fold.items()},
            "split_pcmc_counts": tab.drop_duplicates("cell_id").split_pcmc.value_counts().to_dict(),
            "split_corridor_counts": tab.drop_duplicates("cell_id").split_corridor.value_counts().to_dict(),
            "sha256": hashlib.sha256(OUT_CSV.read_bytes()).hexdigest()}
    OUT_CSV.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2, default=float))
    print(f"Model table: {len(tab)} rows = {tab.cell_id.nunique()} cells x {tab.season.nunique()} seasons -> {OUT_CSV}")
    print(f"Variogram (label errors): nugget share {params[0] / (params[0] + params[1]):.2f}, practical range {params[2]:.1f} km, "
          f"first lag at 95% of variance {first_cross:.1f} km "
          f"-> block {blk} km, {len(blocks)} blocks, ~{meta['variogram']['effective_independent_areas']:.0f} independent areas")
    print("cells per fold:", meta["cells_per_fold"], "| PCMC split:", meta["split_pcmc_counts"])

    plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "font.size": 9})
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    ax.plot(h_raw, gam_raw / gam_raw.max(), "o-", ms=3, color=INK2, lw=1, label="label (scaled): smooth at all scales")
    ax.plot(h_res, gam_res / gam_res.max(), "o-", ms=3, color="#b8b7b2", lw=1, label="label minus distance trend (scaled)")
    ax.plot(h, gam / (params[0] + params[1]), "o", ms=4, color=BLUE, label="label ERRORS (bootstrap)")
    hh = np.linspace(0, h.max(), 200)
    ax.plot(hh, exp_model(hh, *params) / (params[0] + params[1]), color=BLUE, lw=1.5, label=f"fit: range {params[2]:.1f} km")
    ax.axvline(blk, color=ORANGE, ls="--", lw=1.2); ax.text(blk + 0.3, 0.05, f"block {blk} km", color=ORANGE, fontsize=8)
    ax.set_xlabel("Distance between cells (km)"); ax.set_ylabel("Semivariance (÷ sill)")
    ax.grid(color=GRID); ax.spines[["top", "right"]].set_visible(False); ax.legend(frameon=False, fontsize=8)
    ax.set_title("How far apart must cells be to count as independent?", fontsize=10, loc="left")
    fig.tight_layout(); fig.savefig(OUT / "variogram.png", dpi=200); plt.close(fig)
    return tab, meta


if __name__ == "__main__":
    build()
