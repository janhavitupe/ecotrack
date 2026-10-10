"""
Phase 3 — CO2 labels for every 1 km cell and season (decision D16, PROPOSED: awaiting the guide).

No direct 1 km CO2 measurement exists, so labels are *constructed* from Phase 1 physics:

  L-fd (primary)  y(cell, s) = share_NO2(cell) x E_NOx(s) x R
      share_NO2   the cell's fraction of the 25 km flux-divergence NOx total (multi-year map)
      E_NOx(s)    season s city NOx from the EMG fit (run_seasonal; D10: EMG for totals, FD for shares)
      R           CO2:NOx mass ratio constrained by TROPOMI CO (162.7; D12)

  L-co (independent of NO2)  y(cell, s) = share_CO(cell) x C x CO25(s) / CO25(all)
      share_CO    the cell's fraction of the 25 km CO flux-divergence total (terrain-normalised,
                  static pattern removed; run_co_divergence)
      CO25(s)     season s CO flux-divergence total, so the time variation also comes from CO. D21: CO can't
                  resolve season-to-season totals (between/within-season ratio 0.5, vs 2.8 for NO2), so by
                  default (phase3.co_seasonal_scale: false) CO25(s) = CO25(all): L-co is a spatial-only label
      C           the multi-year city CO2 (E_NOx(all) x R): one constant, so NO2 sets only the overall scale

Both maps are smoothed to ~5 km (TROPOMI's real resolution) before sampling at the cell centres; a
1 km label is therefore a downscaled 5 km field, not an independent 1 km measurement.

Units: t CO2 / km2 / yr as the midday October–May rate (what the satellite sees); the `_annual`
columns divide by the D17 factor F. Per-cell uncertainty (random part) combines the map bootstrap
(share) and the season-total uncertainty; the common scale uncertainty (ratio, NOx/NO2, method bias:
the same factor for every cell) is recorded in the meta file and doesn't affect which cells are high or low.

Checks written to outputs/phase3/qa_labels.json:
- the rebuilt NO2 map equals the saved Phase 1 map; cell sums reproduce the corridor shares;
- noise ceiling (best R2 any model could reach given label noise); label spatial-variance share;
- L-fd vs L-co agreement; per-season maps vs the multi-year pattern; smoothing sensitivity;
- Spearman correlation of each label with every feature (construction links flagged) and with the
  inventories (reference only).

Output: data/processed/labels_v1.csv (+ .meta.json), outputs/phase3/qa_labels.json, figures/*.png

Usage (after Phase 1 and Phase 2):
    python -m ecotrack.labels
"""

import hashlib
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Polygon as MplPolygon
from scipy.interpolate import RegularGridInterpolator
from scipy.ndimage import uniform_filter

from ecotrack.acquire.tropomi_cube import load_cube
from ecotrack.config import DATA_INTERIM, OUTPUTS, ROOT, load_config
from ecotrack.features import FEATURES
from ecotrack.grid import GRID_DIR, SUFFIX, load_cells
from ecotrack.inversion.divergence import emission_map, integrate_kg_s
from ecotrack.inversion.emg import M_NO2
from ecotrack.inversion.run_city import BLUE, GRID, INK, INK2, ORANGE, SEQ, SURFACE, match_wind
from ecotrack.inversion.run_co_ratio import SCALE_HEIGHT_KM, prepare_co
from ecotrack.inversion.run_divergence import zones
from ecotrack.inversion.run_seasonal import season_of

VERSION = "v1"
P1 = OUTPUTS / "phase1"
OUT = OUTPUTS / f"phase3{SUFFIX}"
FIG = OUT / "figures"
LABELS_CSV = ROOT / "data" / "processed" / f"labels_{VERSION}{SUFFIX}.csv"  # SUFFIX "_region" for the D22 grid
SECONDS_PER_YEAR = 31_557_600
TO_T_KM2_YR = 1e6 * SECONDS_PER_YEAR / 1000  # kg m-2 s-1 -> t km-2 yr-1
FEATURES_TABLE = ROOT / "data" / "processed" / f"feature_table_v2{SUFFIX}.csv"

# Inputs used to *build* each label: features that share them are construction-linked (D2/D16)
CONSTRUCTION = {
    "label_fd": {"no2": "label is built from the NO2 emission map (Experiment A = construction baseline)",
                 "ws850": "ERA5 850 hPa wind moves the NO2 field in the flux divergence",
                 "wd850": "same wind", "frac_ese": "same wind"},
    "label_co": {"co_norm": "label is built from the CO emission map: drop CO from the features",
                 "ws850": "ERA5 850 hPa wind moves the CO field", "wd850": "same wind", "frac_ese": "same wind"},
}


# ============================================================================ helpers
def sample_cells(field, lat, lon, cells):
    """Bilinear value of a (lat-descending) map at each cell centre."""
    f = RegularGridInterpolator((lat[::-1], lon), field[::-1], bounds_error=False, fill_value=np.nan)
    return f(np.column_stack([cells.lat.values, cells.lon.values]))


def density_from_map(e_map, total_25, smoothing_px, lat, lon, cells, molar_mass):
    """Each cell's emission density as a fraction of the 25 km total, per m2: the smoothed map
    (mol m-2 s-1) x molar mass, divided by the 25 km total (kg/s). Multiply by a city total (kg/s)
    to get kg m-2 s-1. `total_25` must be in kg/s with the same molar-mass convention."""
    smooth = uniform_filter(np.nan_to_num(e_map), size=smoothing_px)
    return sample_cells(smooth, lat, lon, cells) * molar_mass / total_25


def no2_inputs(cfg):
    """The NO2 flux-divergence inputs exactly as in run_divergence (multi-year map)."""
    inv = cfg["inversion"]
    city = json.loads((P1 / "city_fit.json").read_text())
    no2, times, lat, lon, _ = load_cube()
    met, lvl = match_wind(times, cfg)
    ws = met[f"ws{lvl}"].to_numpy()
    use = met[f"u{lvl}"].notna().to_numpy() & (ws <= inv["windy_max_ms"])
    tau_s = city["results"][0]["emission"]["tau_h"] * 3600
    v_bg = float(np.nanpercentile(np.nanmean(no2[use], axis=0), 10))
    return dict(x=no2[use], u=met[f"u{lvl}"].to_numpy()[use], v=met[f"v{lvl}"].to_numpy()[use],
                seasons=season_of(pd.DatetimeIndex(times[use])), lat=lat, lon=lon, tau_s=tau_s, v_bg=v_bg,
                ratio=inv["nox_no2_ratio"], src=(city["source_lat"], city["source_lon"]))


def co_inputs(cfg):
    """The CO flux-divergence inputs exactly as in run_co_divergence."""
    inv = cfg["inversion"]
    co, times, lat, lon, z = prepare_co(cfg)
    met, lvl = match_wind(times, cfg)
    ws = met[f"ws{lvl}"].to_numpy()
    use = met[f"u{lvl}"].notna().to_numpy() & (ws <= inv["windy_max_ms"])
    x = co[use] / np.exp(-z / (SCALE_HEIGHT_KM * 1000))[None]
    x = x - np.nanmedian(x.reshape(len(x), -1), axis=1)[:, None, None]
    x = x - np.nanmean(x, axis=0)[None]
    return dict(x=x, u=met[f"u{lvl}"].to_numpy()[use], v=met[f"v{lvl}"].to_numpy()[use],
                seasons=season_of(pd.DatetimeIndex(times[use])), lat=lat, lon=lon)


def no2_map(d, weights=None, sel=None):
    s = slice(None) if sel is None else sel
    w = None if weights is None else weights
    e, *_ = emission_map(d["x"][s], d["u"][s], d["v"][s], d["lat"], d["lon"], d["tau_s"], d["v_bg"], d["ratio"], weights=w)
    return e


def co_map(d, weights=None, sel=None):
    s = slice(None) if sel is None else sel
    e, *_ = emission_map(d["x"][s], d["u"][s], d["v"][s], d["lat"], d["lon"], tau_s=1e15, v_bg=0.0,
                         nox_no2_ratio=1.0, weights=weights)
    return e  # mol CO m-2 s-1


# ============================================================================ build
def build():
    cfg = load_config()
    p3 = cfg["phase3"]
    k = p3["smoothing_px"]
    rng = np.random.default_rng(cfg["inversion"]["de"]["seed"])
    cells = load_cells()
    OUT.mkdir(parents=True, exist_ok=True); FIG.mkdir(parents=True, exist_ok=True)

    seasonal = {r["season"]: r for r in json.loads((P1 / "seasonal.json").read_text())["seasons"]}
    city = json.loads((P1 / "city_fit.json").read_text())["results"][0]
    co_ratio = json.loads((P1 / "co_ratio.json").read_text())
    R = co_ratio["co2_nox_co_constrained"]["central"]
    R_lo, R_hi = co_ratio["co2_nox_co_constrained"]["range_95"]
    ta = json.loads((P1 / "temporal_adjust.json").read_text())
    F = float(np.mean([ta["EDGAR profiles"]["F"], ta["flat residential month profile"]["F"]]))
    E_all = city["emission"]["e_nox_kg_s"]
    seasons = sorted(seasonal)
    qa = {"constants": {"co2_nox_ratio": R, "co2_nox_ratio_95": [R_lo, R_hi], "annual_factor_F": F,
                        "e_nox_all_kg_s": E_all, "smoothing_px": k}}

    # ---------------------------------------------------------------- L-fd
    print("NO2 flux-divergence map (multi-year) ...")
    dn = no2_inputs(cfg)
    lat, lon = dn["lat"], dn["lon"]
    masks, in_corr, r_src = zones(lat, lon, dn["src"], cfg)
    e_no2 = no2_map(dn)
    saved = np.load(P1 / "divergence_map.npz")["e_nox_mol_m2_s"]
    qa["check_map_equals_phase1"] = bool(np.allclose(e_no2, saved, equal_nan=True, rtol=1e-9, atol=0))
    fd25 = integrate_kg_s(e_no2, r_src <= 25, lat, lon)
    dens_fd = density_from_map(e_no2, fd25, k, lat, lon, cells, M_NO2)  # per m2, fraction of the 25 km total

    print(f"  bootstrap x{p3['bootstrap_fd']} ...")
    boot_fd = []
    for _ in range(p3["bootstrap_fd"]):
        w = np.bincount(rng.integers(0, len(dn["x"]), len(dn["x"])), minlength=len(dn["x"])).astype(float)
        eb = no2_map(dn, weights=w)
        boot_fd.append(density_from_map(eb, integrate_kg_s(eb, r_src <= 25, lat, lon), k, lat, lon, cells, M_NO2))
    sd_dens_fd = np.std(boot_fd, axis=0)

    # ---------------------------------------------------------------- L-co
    print("CO flux-divergence map (multi-year) ...")
    dc = co_inputs(cfg)
    e_co = co_map(dc)
    mol25 = lambda e: integrate_kg_s(e, r_src <= 25, lat, lon) / M_NO2  # integrate_kg_s multiplies by M_NO2
    co25_all = mol25(e_co)
    dens_co = density_from_map(e_co, co25_all, k, lat, lon, cells, 1.0)  # fraction of the 25 km mol/s total, per m2
    print(f"  bootstrap x{p3['bootstrap_co']} ...")
    boot_co = []
    for _ in range(p3["bootstrap_co"]):
        w = np.bincount(rng.integers(0, len(dc["x"]), len(dc["x"])), minlength=len(dc["x"])).astype(float)
        eb = co_map(dc, weights=w)
        boot_co.append(density_from_map(eb, mol25(eb), k, lat, lon, cells, 1.0))
    sd_dens_co = np.std(boot_co, axis=0)

    # per-season CO totals (time variation of L-co) with their own bootstrap
    co_season = {}
    for s in seasons:
        sel = np.asarray(dc["seasons"] == s)
        n = int(sel.sum())
        tot = mol25(co_map(dc, sel=sel))
        draws = []
        for _ in range(p3["bootstrap_co"]):
            w = np.bincount(rng.integers(0, n, n), minlength=n).astype(float)
            draws.append(mol25(co_map(dc, weights=w, sel=sel)))
        co_season[s] = {"n": n, "co25_mol_s": tot, "sd_mol_s": float(np.std(draws))}

    # ---------------------------------------------------------------- assemble
    C_all = E_all * R  # kg CO2/s, multi-year city (midday rate)
    rows = []
    for s in seasons:
        Es = seasonal[s]["e_nox_kg_s"]
        lo, _, hi = seasonal[s]["ci95"]
        sd_Es = (hi - lo) / (2 * 1.96)
        if p3["co_seasonal_scale"]:
            scale_co, sd_scale_co = co_season[s]["co25_mol_s"] / co25_all, co_season[s]["sd_mol_s"] / co25_all
        else:  # D21: spatial-only L-co
            scale_co, sd_scale_co = 1.0, 0.0
        lab_fd = dens_fd * Es * R * TO_T_KM2_YR
        sd_fd = np.hypot(sd_dens_fd * Es, dens_fd * sd_Es) * R * TO_T_KM2_YR
        lab_co = dens_co * C_all * scale_co * TO_T_KM2_YR
        sd_co = np.hypot(sd_dens_co * scale_co, dens_co * sd_scale_co) * C_all * TO_T_KM2_YR
        rows.append(pd.DataFrame({"cell_id": cells.cell_id, "season": s, "cluster": cells.cluster,
                                  "label_fd": lab_fd, "label_fd_sd": sd_fd, "label_fd_annual": lab_fd / F,
                                  "label_co": lab_co, "label_co_sd": sd_co, "label_co_annual": lab_co / F,
                                  "share_fd_per_km2": dens_fd * 1e6, "share_co_per_km2": dens_co * 1e6}))
    lab = pd.concat(rows, ignore_index=True)
    LABELS_CSV.parent.mkdir(parents=True, exist_ok=True)
    lab.to_csv(LABELS_CSV, index=False)

    # ---------------------------------------------------------------- QA
    # 1. cells reproduce the pixel-based corridor shares (268 cells of 1 km2 vs the corridor polygon)
    in_c = cells.in_corridor.to_numpy(bool) if "in_corridor" in cells else np.ones(len(cells), bool)
    corr_fd_pix = integrate_kg_s(e_no2, in_corr, lat, lon) / fd25
    corr_co_pix = integrate_kg_s(e_co, in_corr, lat, lon) / M_NO2 / co25_all
    qa["corridor_share"] = {
        "label_fd_cells": float(dens_fd[in_c].sum() * 1e6), "fd_pixels_unsmoothed": corr_fd_pix,
        "label_co_cells": float(dens_co[in_c].sum() * 1e6), "co_pixels_unsmoothed": corr_co_pix,
        "note": "cells use the ~5 km smoothed map, which spreads some emission across the corridor edge"}
    # 2. totals per cluster and season (kt CO2/yr, midday rate)
    lab["kt_fd"] = lab.label_fd / 1000  # 1 km2 cells: t/km2/yr -> t/yr; /1000 -> kt
    lab["kt_co"] = lab.label_co / 1000
    qa["totals_kt_yr_midday"] = {
        lbl: {s: {**{c: round(float(g[col].sum()), 1) for c, g in lab[lab.season == s].groupby("cluster")},
                  "corridor": round(float(lab.loc[(lab.season == s) & lab.cluster.ne("outside"), col].sum()), 1)} for s in seasons}
        for lbl, col in (("label_fd", "kt_fd"), ("label_co", "kt_co"))}
    # 3. distribution, negatives, noise ceiling, spatial share
    for col in ("label_fd", "label_co"):
        y, sd = lab[col].to_numpy(), lab[col + "_sd"].to_numpy()
        cell_mean = lab.groupby("cell_id")[col].transform("mean")
        qa[col] = {"min": float(y.min()), "p1": float(np.percentile(y, 1)), "median": float(np.median(y)),
                   "p99": float(np.percentile(y, 99)), "max": float(y.max()),
                   "negative_fraction": float((y < 0).mean()),
                   "noise_ceiling_r2": float(1 - np.mean(sd ** 2) / np.var(y)),
                   "median_relative_sd": float(np.median(sd / np.abs(y))),
                   "spatial_variance_share": float(np.var(cell_mean) / np.var(y))}
    # 4. agreement between the two labels (cell pattern)
    pat = lab[lab.season == seasons[0]]
    qa["fd_vs_co_cells"] = {"pearson": float(np.corrcoef(pat.share_fd_per_km2, pat.share_co_per_km2)[0, 1]),
                            "spearman": float(pat.share_fd_per_km2.corr(pat.share_co_per_km2, method="spearman"))}
    # 5. per-season maps vs the multi-year pattern (is a fixed pattern justified?)
    qa["season_pattern_vs_multiyear"] = {}
    for s in seasons:
        sel_n = np.asarray(dn["seasons"] == s)
        e_s = no2_map(dn, sel=sel_n)
        d_s = density_from_map(e_s, integrate_kg_s(e_s, r_src <= 25, lat, lon), k, lat, lon, cells, M_NO2)
        sel_c = np.asarray(dc["seasons"] == s)
        ec_s = co_map(dc, sel=sel_c)
        dco_s = density_from_map(ec_s, mol25(ec_s), k, lat, lon, cells, 1.0)
        qa["season_pattern_vs_multiyear"][s] = {"fd_r": float(np.corrcoef(d_s, dens_fd)[0, 1]),
                                                "co_r": float(np.corrcoef(dco_s, dens_co)[0, 1])}
    # 6. smoothing sensitivity
    qa["smoothing_sensitivity"] = {}
    for kk in p3["smoothing_sensitivity"]:
        d_fd = density_from_map(e_no2, fd25, kk, lat, lon, cells, M_NO2)
        d_co = density_from_map(e_co, co25_all, kk, lat, lon, cells, 1.0)
        qa["smoothing_sensitivity"][f"{kk}px"] = {
            "fd_r_vs_main": float(np.corrcoef(d_fd, dens_fd)[0, 1]), "fd_corridor_share": float(d_fd[in_c].sum() * 1e6),
            "co_r_vs_main": float(np.corrcoef(d_co, dens_co)[0, 1]), "co_corridor_share": float(d_co[in_c].sum() * 1e6)}
    # 7. label vs features (season means) and inventories: construction links flagged
    ft = pd.read_csv(FEATURES_TABLE)
    fs = ft.groupby(["cell_id", "season"])[FEATURES + [c for c in ft.columns if c.startswith("ref_")]].mean().reset_index()
    m = lab.merge(fs, on=["cell_id", "season"], how="left")
    qa["label_feature_spearman"] = {
        col: {f: {"r": round(float(m[col].corr(m[f], method="spearman")), 3),
                  "construction_link": CONSTRUCTION[col].get(f)} for f in FEATURES}
        for col in ("label_fd", "label_co")}
    qa["label_inventory_spearman"] = {col: {f: round(float(m[col].corr(m[f], method="spearman")), 3)
                                            for f in ("ref_edgar_co2_t_km2_yr", "ref_odiac_co2_t_km2_month")}
                                      for col in ("label_fd", "label_co")}
    qa["co_season_totals"] = co_season
    # can CO resolve season-to-season changes? (between-season spread vs within-season noise; NO2 EMG: 2.8)
    tots = np.array([v["co25_mol_s"] for v in co_season.values()])
    qa["co_between_within_ratio"] = float(np.std(tots, ddof=1) / np.mean([v["sd_mol_s"] for v in co_season.values()]))
    qa["construction_inputs"] = CONSTRUCTION
    (OUT / "qa_labels.json").write_text(json.dumps(qa, indent=2, default=float))

    meta = {"version": VERSION, "design": "D16 (PROPOSED, awaiting the guide); D21 L-co spatial-only",
            "primary_label": p3["primary_label"], "co_seasonal_scale": p3["co_seasonal_scale"],
            "rows": len(lab), "cells": int(lab.cell_id.nunique()), "seasons": seasons,
            "units": "t CO2 / km2 / yr, midday Oct-May rate; *_annual = / F",
            "constants": qa["constants"],
            "common_scale_uncertainty_rel_1sigma": {
                "note": "same factor for every cell; not in label_*_sd",
                "co2_nox_ratio": (R_hi - R_lo) / (2 * 1.96) / R, "nox_no2_ratio": 0.1 / 1.32,
                "emg_method_bias": 0.12},
            "sha256": hashlib.sha256(LABELS_CSV.read_bytes()).hexdigest()}
    LABELS_CSV.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2, default=float))

    report(qa, lab, seasons)
    figures(lab, cells, seasons, qa)
    return lab, qa


# ============================================================================ outputs
def report(qa, lab, seasons):
    print(f"\nLabels {VERSION}: {len(lab)} rows = {lab.cell_id.nunique()} cells x {len(seasons)} seasons -> {LABELS_CSV}")
    print("Rebuilt NO2 map equals Phase 1 map:", qa["check_map_equals_phase1"])
    print(f"CO season totals between/within ratio: {qa['co_between_within_ratio']:.2f} (NO2 EMG: 2.8)")
    cs = qa["corridor_share"]
    print(f"Corridor share from cells: L-fd {100 * cs['label_fd_cells']:.1f}% (pixels {100 * cs['fd_pixels_unsmoothed']:.1f}%), "
          f"L-co {100 * cs['label_co_cells']:.1f}% (pixels {100 * cs['co_pixels_unsmoothed']:.1f}%)")
    for col in ("label_fd", "label_co"):
        q = qa[col]
        print(f"{col}: median {q['median']:.0f} t/km2/yr [p1 {q['p1']:.0f}, p99 {q['p99']:.0f}], negative {100 * q['negative_fraction']:.1f}%, "
              f"median rel. sd {100 * q['median_relative_sd']:.0f}%, noise ceiling R2 {q['noise_ceiling_r2']:.2f}, "
              f"spatial share {q['spatial_variance_share']:.2f}")
    print("L-fd vs L-co cell pattern:", {k: round(v, 2) for k, v in qa["fd_vs_co_cells"].items()})
    print("Per-season pattern vs multi-year (r):", {s: (round(v["fd_r"], 2), round(v["co_r"], 2))
                                                     for s, v in qa["season_pattern_vs_multiyear"].items()})
    print("Smoothing sensitivity:", {k: {kk: round(vv, 3) for kk, vv in v.items()} for k, v in qa["smoothing_sensitivity"].items()})
    print("Corridor totals, kt CO2/yr (midday):",
          {s: (qa["totals_kt_yr_midday"]["label_fd"][s]["corridor"], qa["totals_kt_yr_midday"]["label_co"][s]["corridor"]) for s in seasons})
    for col in ("label_fd", "label_co"):
        top = sorted(qa["label_feature_spearman"][col].items(), key=lambda kv: -abs(kv[1]["r"]))[:6]
        print(f"{col} vs features (Spearman):", [(f, v["r"], "LINK" if v["construction_link"] else "") for f, v in top])
    print("vs inventories (reference):", qa["label_inventory_spearman"])


def figures(lab, cells, seasons, qa):
    plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "font.size": 9, "text.color": INK,
                         "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2})
    geo = json.loads((GRID_DIR / "cells.geojson").read_text())
    rings = {f["properties"]["cell_id"]: np.array(f["geometry"]["coordinates"][0]) for f in geo["features"]}

    def cell_map(ax, values, title, norm, cmap=SEQ):
        for cid, v in values.items():
            ax.add_patch(MplPolygon(rings[cid], closed=True, fc=cmap(norm(v)), ec="none"))
        ax.autoscale_view(); ax.set_aspect(1 / np.cos(np.radians(18.6)))
        ax.set_xticks([]); ax.set_yticks([]); [s.set_visible(False) for s in ax.spines.values()]
        ax.set_title(title, fontsize=9, loc="left")

    # 1. multi-year mean labels side by side + uncertainty
    mean = lab.groupby("cell_id")[["label_fd", "label_co", "label_fd_sd", "label_co_sd"]].mean() / 1000
    vmax = float(np.nanpercentile(mean[["label_fd", "label_co"]].to_numpy(), 99))
    norm = plt.Normalize(0, vmax)
    fig, axes = plt.subplots(1, 4, figsize=(13, 4.6))
    cell_map(axes[0], mean.label_fd, "L-fd (from NO₂), mean of 5 seasons", norm)
    cell_map(axes[1], mean.label_co, "L-co (from CO), mean of 5 seasons", norm)
    rel_n = plt.Normalize(0, 1)
    cell_map(axes[2], (mean.label_fd_sd / mean.label_fd.abs()).clip(0, 1), "L-fd relative uncertainty", rel_n, plt.cm.Greys)
    cell_map(axes[3], (mean.label_co_sd / mean.label_co.abs()).clip(0, 1), "L-co relative uncertainty", rel_n, plt.cm.Greys)
    for ax_, (n_, cm_, lbl_) in zip([axes[:2], axes[2:]], [(norm, SEQ, "kt CO₂ / km² / yr (midday rate)"),
                                                          (rel_n, plt.cm.Greys, "1σ / label")]):
        cb = fig.colorbar(plt.cm.ScalarMappable(norm=n_, cmap=cm_), ax=list(ax_), orientation="horizontal", shrink=0.6, pad=0.04)
        cb.set_label(lbl_, color=INK2, fontsize=8); cb.outline.set_edgecolor(GRID)
    fig.suptitle("Phase 3 labels: fossil CO₂ per 1 km cell", fontsize=11, x=0.01, ha="left")
    fig.savefig(FIG / "label_maps.png", dpi=200, bbox_inches="tight"); plt.close(fig)

    # 2. corridor total per season, both labels
    t = qa["totals_kt_yr_midday"]
    x = np.arange(len(seasons))
    fig, ax = plt.subplots(figsize=(7, 3.2))
    ax.bar(x - 0.18, [t["label_fd"][s]["corridor"] for s in seasons], 0.34, color=BLUE, label="L-fd (NO₂)")
    ax.bar(x + 0.18, [t["label_co"][s]["corridor"] for s in seasons], 0.34, color=ORANGE, label="L-co (CO)")
    ax.set_xticks(x, seasons); ax.set_ylabel("Corridor CO₂ (kt/yr, midday rate)"); ax.grid(axis="y", color=GRID)
    ax.spines[["top", "right"]].set_visible(False); ax.legend(frameon=False)
    ax.set_title("Corridor total per season: the two labels' time patterns", fontsize=10, loc="left")
    fig.tight_layout(); fig.savefig(FIG / "label_seasons.png", dpi=200); plt.close(fig)

    # 3. L-fd vs L-co per cell, coloured by cluster
    pat = lab.groupby(["cell_id", "cluster"])[["label_fd", "label_co"]].mean().reset_index()
    cols = {"C1_shivajinagar_kasarwadi": BLUE, "C2_pcmc": ORANGE, "C3_dehu_talegaon": "#1baf7a"}
    fig, ax = plt.subplots(figsize=(4.8, 4.4))
    for c, g in pat.groupby("cluster"):
        ax.scatter(g.label_fd / 1000, g.label_co / 1000, s=10, color=cols.get(c, "#b8b7b2"), label=c.split("_")[0], alpha=0.8 if c in cols else 0.25)
    lim = float(max(pat.label_fd.max(), pat.label_co.max()) / 1000) * 1.05
    ax.plot([0, lim], [0, lim], color=INK2, lw=0.8, ls="--")
    ax.set_xlabel("L-fd (kt/km²/yr)"); ax.set_ylabel("L-co (kt/km²/yr)"); ax.legend(frameon=False, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title(f"Per-cell agreement (r = {qa['fd_vs_co_cells']['pearson']:.2f})", fontsize=10, loc="left")
    fig.tight_layout(); fig.savefig(FIG / "label_fd_vs_co.png", dpi=200); plt.close(fig)


if __name__ == "__main__":
    build()
