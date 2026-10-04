"""
Phase 2 — assemble the frozen multi-source feature table (one row per 1 km cell per month).

Sources joined here:
  atmosphere (per cell-month)  no2, no2_n (overpasses behind it), co_norm (terrain-normalised CO),
                               hcho (D14)                                  ← TROPOMI cubes / GEE
  meteorology (per month)      ws850, wd850, blh_m, frac_ese, t2m_k, ssrd  ← ERA5 (uniform over the
                               corridor: one 0.25° cell, see research log)
  human activity               viirs_rad (monthly); ndvi, ndbi (seasonal);
                               road_major/mid/minor/total_km, industrial_frac (static)
                                                                            ← VIIRS, Sentinel-2, OSM
                               (roads + industrial land from a Geofabrik OSM extract, osm_pbf.py;
                                GRIP4 kept as grip_* cross-check columns; v1 used GRIP4 only, D20)
  reference only (ref_*)       ref_edgar_nox/co/co2_t_km2_yr, ref_odiac_co2_t_km2_month
                               — inventories: comparison / priors only, NEVER model features
                                 (proposal §5 rule; D2)
OCO-3 XCO₂ is not a column: too sparse for per-cell features (D11).

QA (proposal Phase 2 step 5): missing-data audit, per-feature histograms, spot checks of 8 cells;
from v2 also feature correlations (redundancy before ML), how much of each feature varies between
cells vs between months, and the OSM-vs-GRIP4 road agreement. The CSV's SHA-256 goes in the meta
file, so the frozen table can be verified later.
Output: data/processed/feature_table_v2.csv (+ outputs/phase2/qa_*_v2.{json,png}).
v1 (GRIP4 roads, 16 features) is kept unchanged as the earlier frozen version.

Usage:
    python -m ecotrack.features
"""

import glob
import hashlib
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.interpolate import RegularGridInterpolator
from scipy.ndimage import uniform_filter

from ecotrack.acquire.tropomi_cube import load_cube
from ecotrack.config import DATA_INTERIM, OUTPUTS, ROOT, load_config
from ecotrack.grid import GRID_DIR, load_cells
from ecotrack.inversion.run_co_ratio import FOOTPRINT_PX, SCALE_HEIGHT_KM

VERSION = "v2"
OUT_CSV = ROOT / "data" / "processed" / f"feature_table_{VERSION}.csv"
QA_DIR = OUTPUTS / "phase2"
C_TO_CO2 = 44.0095 / 12.011
FEATURES = ["no2", "co_norm", "hcho", "ws850", "wd850", "blh_m", "frac_ese", "t2m_k", "ssrd_j_m2",
            "viirs_rad", "ndvi", "ndbi", "road_major_km", "road_mid_km", "road_minor_km", "road_total_km", "industrial_frac"]


def season_of(month: str) -> str:
    y, m = int(month[:4]), int(month[5:7])
    start = y if m >= 10 else y - 1
    return f"{start}-{str(start + 1)[2:]}"


def sample_cube(arr, times, lat, lon, cells):
    """Monthly mean of a cube at each cell centre (bilinear), plus the number of valid overpasses."""
    months = pd.DatetimeIndex(times).strftime("%Y-%m")
    pts = np.column_stack([cells.lat.values, cells.lon.values])
    rows = []
    for m in sorted(set(months)):
        sel = months == m
        mean = np.nanmean(arr[sel], axis=0)
        count = np.isfinite(arr[sel]).sum(axis=0).astype(float)
        mean_f = np.where(np.isfinite(mean), mean, np.nanmean(mean))
        interp = RegularGridInterpolator((lat[::-1], lon), mean_f[::-1], bounds_error=False)
        cnt = RegularGridInterpolator((lat[::-1], lon), count[::-1], method="nearest", bounds_error=False)
        rows.append(pd.DataFrame({"cell_id": cells.cell_id, "month": m, "value": interp(pts), "n": cnt(pts)}))
    return pd.concat(rows, ignore_index=True)


def met_monthly(cfg):
    met = pd.read_csv(DATA_INTERIM / "era5" / "overpass_met.csv", parse_dates=["time_utc"])
    met = met[met.cluster == "C2_pcmc"].copy()
    met["month"] = met.time_utc.dt.strftime("%Y-%m")
    g = met.groupby("month")
    out = pd.DataFrame({
        "ws850": g.ws850.mean(),
        "blh_m": g.blh.mean(),
        # vector-mean direction (wind FROM), from mean u and v
        "wd850": (270 - np.degrees(np.arctan2(g.v850.mean(), g.u850.mean()))) % 360,
        "frac_ese": g.wd850.apply(lambda s: float(((s >= 45) & (s < 180)).mean())),
    }).reset_index()
    return out


def inventories(cells, months):
    """EDGAR (0.1°, annual) and ODIAC (1 km, monthly) densities at each cell centre — reference only."""
    rows = []
    cell_area_km2 = lambda lat: 0.1 * 110.574 * 0.1 * 111.320 * np.cos(np.radians(lat))
    ed = {}
    for sp in ("NOx", "CO", "CO2"):
        for y in (2019, 2020, 2021, 2022):
            d = np.load(DATA_INTERIM / "edgar" / f"{sp}_{y}_TOTALS.npz")
            ed[(sp, y)] = (d["lat"], d["lon"], d["emissions_t"])
    od = {Path_stem: np.load(f) for f, Path_stem in ((f, f[-10:-4]) for f in glob.glob(str(DATA_INTERIM / "odiac" / "*.npz")))}
    for m in months:
        y = min(int(m[:4]), 2022)
        ym = m.replace("-", "")
        if ym not in od:  # ODIAC v2024 ends Dec 2023: use the same month of 2023
            ym = "2023" + ym[4:]
        o = od[ym]
        for c in cells.itertuples():
            r = {"cell_id": c.cell_id, "month": m}
            for sp in ("NOx", "CO", "CO2"):
                la, lo, em = ed[(sp, y)]
                i, j = np.abs(la - c.lat).argmin(), np.abs(lo - c.lon).argmin()
                r[f"ref_edgar_{sp.lower()}_t_km2_yr"] = em[i, j] / cell_area_km2(c.lat)
            i, j = np.abs(o["lat"] - c.lat).argmin(), np.abs(o["lon"] - c.lon).argmin()
            px_km2 = (o["lat"][0] - o["lat"][1]) * 110.574 * (o["lon"][1] - o["lon"][0]) * 111.320 * np.cos(np.radians(c.lat))
            r["ref_odiac_co2_t_km2_month"] = o["t_c_per_cell"][i, j] * C_TO_CO2 / px_km2
            rows.append(r)
    return pd.DataFrame(rows)


def build():
    cfg = load_config()
    cells = load_cells()

    no2, t, lat, lon, _ = load_cube("no2")
    df = sample_cube(no2, t, lat, lon, cells).rename(columns={"value": "no2", "n": "no2_n"})

    co, t_co, lat_c, lon_c, _ = load_cube("co")
    z = uniform_filter(np.load(DATA_INTERIM / "dem_cube_grid.npz")["elevation_m"], size=FOOTPRINT_PX)
    co_norm = co / np.exp(-z / (SCALE_HEIGHT_KM * 1000))[None]
    df = df.merge(sample_cube(co_norm, t_co, lat_c, lon_c, cells).rename(columns={"value": "co_norm", "n": "co_n"}),
                  on=["cell_id", "month"], how="left")

    gee = pd.read_csv(GRID_DIR / "layers_monthly.csv")
    df = df.merge(gee, on=["cell_id", "month"], how="left")
    df = df.merge(met_monthly(cfg), on="month", how="left")
    df["season"] = df.month.map(season_of)
    df = df.merge(pd.read_csv(GRID_DIR / "layers_seasonal.csv").drop(columns="n_scenes"), on=["cell_id", "season"], how="left")
    # Roads: OpenStreetMap (proposal) if its download completed; otherwise GRIP4 (Earth Engine) as a
    # documented fallback. When both exist, GRIP4 is kept as `grip_*` cross-check columns.
    osm, grip = GRID_DIR / "layers_roads.csv", GRID_DIR / "layers_roads_grip.csv"
    road_cols = ["road_major_km", "road_mid_km", "road_minor_km", "road_total_km"]
    if osm.exists():
        road_source = "OpenStreetMap"
        df = df.merge(pd.read_csv(osm), on="cell_id", how="left")
        if grip.exists():
            g = pd.read_csv(grip).rename(columns={c: "grip_" + c for c in road_cols})
            df = df.merge(g, on="cell_id", how="left")
    elif grip.exists():
        road_source = "GRIP4 (OSM fallback)"
        print("NOTE: OSM roads not available -> using GRIP4 roads (documented fallback)")
        df = df.merge(pd.read_csv(grip), on="cell_id", how="left")
    else:
        road_source = "none (DRAFT)"
        print("WARNING: no road layer -> road columns empty; writing a DRAFT table")
        for c in road_cols:
            df[c] = np.nan
    roads = osm if osm.exists() else grip
    df = df.merge(pd.read_csv(GRID_DIR / "layers_landuse.csv"), on="cell_id", how="left")
    df = df.merge(cells[["cell_id", "lat", "lon", "cluster", "frac_in_corridor", "dist_to_source_km"]], on="cell_id", how="left")
    df = df.merge(inventories(cells, sorted(df.month.unique())), on=["cell_id", "month"], how="left")

    lead = ["cell_id", "month", "season", "lat", "lon", "cluster", "frac_in_corridor", "dist_to_source_km"]
    df = df[lead + FEATURES + ["no2_n", "co_n"] + [c for c in df.columns if c.startswith("grip_")]
            + [c for c in df.columns if c.startswith("ref_")]]
    df.attrs["road_source"] = road_source
    out = OUT_CSV if roads.exists() else OUT_CSV.with_name(OUT_CSV.stem + "_draft_noroads.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    osm_src = GRID_DIR / "osm_source.json"
    (out.with_suffix(".meta.json")).write_text(json.dumps({
        "version": VERSION, "road_source": road_source,
        "osm_extract": json.loads(osm_src.read_text())["file"] if osm_src.exists() and osm.exists() else None,
        "rows": len(df), "cells": int(df.cell_id.nunique()), "months": int(df.month.nunique()),
        "features": FEATURES, "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}, indent=2))
    print(f"Road source: {road_source}")
    print(f"Feature table {VERSION}: {len(df)} rows = {df.cell_id.nunique()} cells x {df.month.nunique()} months, "
          f"{len(FEATURES)} features -> {out}")
    qa(df)
    return df


def qa(df):
    QA_DIR.mkdir(parents=True, exist_ok=True)
    cols = FEATURES + [c for c in df.columns if c.startswith("ref_")]
    missing = {c: int(df[c].isna().sum()) for c in cols}
    stats = df[cols].describe(percentiles=[0.01, 0.5, 0.99]).T[["min", "1%", "50%", "99%", "max"]]
    spot = df[df.month == "2022-01"].sample(8, random_state=1)[["cell_id", "cluster"] + FEATURES]
    report = {"rows": len(df), "cells": int(df.cell_id.nunique()), "months": int(df.month.nunique()),
              "missing_per_column": missing, "missing_total_pct": 100 * sum(missing.values()) / (len(df) * len(cols)),
              "stats": stats.round(6).to_dict(orient="index"),
              "no2_overpasses_per_cell_month": {"min": float(df.no2_n.min()), "median": float(df.no2_n.median())},
              "spot_check_2022_01": spot.round(6).to_dict(orient="records")}
    # redundancy before ML: Spearman correlation between features (rank-based: robust to skew)
    corr = df[FEATURES].corr(method="spearman")
    pairs = [(a, b, round(float(corr.loc[a, b]), 3)) for i, a in enumerate(FEATURES) for b in FEATURES[i + 1:]
             if abs(corr.loc[a, b]) >= 0.8]
    report["high_correlation_pairs_abs_ge_0.8"] = pairs
    # share of each feature's variance that is between cells (spatial) rather than between months
    report["spatial_variance_share"] = {c: round(float(df.groupby("cell_id")[c].mean().var(ddof=0) / df[c].var(ddof=0)), 3)
                                        if df[c].var() > 0 else None for c in FEATURES}
    if "grip_road_total_km" in df:
        st = df.drop_duplicates("cell_id")
        report["osm_vs_grip4_roads"] = {c: {"median_osm": round(float(st[c].median()), 3),
                                            "median_grip": round(float(st["grip_" + c].median()), 3),
                                            "spearman": round(float(st[c].corr(st["grip_" + c], method="spearman")), 3)}
                                        for c in ["road_major_km", "road_mid_km", "road_minor_km", "road_total_km"]}
    (QA_DIR / f"qa_feature_table_{VERSION}.json").write_text(json.dumps(report, indent=2, default=float))

    fig, ax = plt.subplots(figsize=(8.5, 7.5))
    im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.grid(False)
    ax.set_xticks(range(len(FEATURES)), FEATURES, rotation=90, fontsize=8)
    ax.set_yticks(range(len(FEATURES)), FEATURES, fontsize=8)
    for i in range(len(FEATURES)):
        for j in range(len(FEATURES)):
            ax.text(j, i, f"{corr.values[i, j]:.1f}", ha="center", va="center", fontsize=5.5,
                    color="white" if abs(corr.values[i, j]) > 0.6 else "#0b0b0b")
    fig.colorbar(im, ax=ax, shrink=0.8, label="Spearman correlation")
    ax.set_title(f"Feature table {VERSION}: correlation between features", fontsize=10, loc="left")
    fig.tight_layout(); fig.savefig(QA_DIR / f"qa_correlation_{VERSION}.png", dpi=150); plt.close(fig)

    n = len(cols)
    fig, axes = plt.subplots((n + 3) // 4, 4, figsize=(13, 2.3 * ((n + 3) // 4)))
    for ax, c in zip(axes.flat, cols):
        v = df[c].dropna()
        ax.hist(v, bins=40, color="#2a78d6")
        ax.set_title(f"{c}  (missing {missing[c]})", fontsize=8, loc="left")
        ax.tick_params(labelsize=7)
    for ax in list(axes.flat)[n:]:
        ax.axis("off")
    fig.suptitle(f"Feature table {VERSION}: per-column histograms (QA)", fontsize=11, x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(QA_DIR / f"qa_histograms_{VERSION}.png", dpi=150); plt.close(fig)

    print("Missing values per column:", {k: v for k, v in missing.items() if v})
    print(stats.to_string(float_format=lambda x: f"{x:.4g}"))
    print("Feature pairs with |Spearman| >= 0.8:", pairs)
    print("Spatial variance share:", report["spatial_variance_share"])
    print("OSM vs GRIP4:", report.get("osm_vs_grip4_roads"))
    print("Spot check (2022-01, 8 random cells):")
    print(spot.to_string(index=False, float_format=lambda x: f"{x:.4g}"))


if __name__ == "__main__":
    build()
