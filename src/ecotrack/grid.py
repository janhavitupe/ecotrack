"""
Phase 2 — the 1 km modelling grid over the corridor.

Cells are 1 km squares in UTM 43N (real kilometres), aligned to whole kilometres. A cell is kept
if at least `min_frac_in_corridor` of its area lies inside the corridor polygon (D15). Each cell
gets: an id, centre lat/lon, its fraction inside the corridor, its cluster (nearest waypoint's
cluster, as in the flux-divergence zones) and its distance to the Phase 1 emission source.

Outputs: data/interim/grid/cells.csv and cells.geojson (WGS84 polygons, used by Earth Engine).

Regional grid (D22): with the environment variable ECOTRACK_GRID=region, every Phase 2-3 script
works on a larger training grid instead: all 1 km cells whose centre lies within `region.radius_km`
of the Phase 1 source and at least `region.box_margin_km` inside the TROPOMI cube box, plus every
corridor cell. Same 1 km alignment, so corridor cells coincide exactly; extra columns `in_corridor`
and `corridor_cell_id` link them to the corridor grid. Files go to data/interim/grid_region/ and every
downstream output gets a "_region" suffix, so the corridor products stay untouched.

Usage:
    python -m ecotrack.grid                      # corridor grid (268 cells)
    $env:ECOTRACK_GRID="region"; python -m ecotrack.grid    # regional training grid (PowerShell)
"""

import json
import os

import numpy as np
import pandas as pd
import pyproj
from shapely.geometry import box, mapping
from shapely.ops import transform

from ecotrack.config import DATA_INTERIM, OUTPUTS, load_config
from ecotrack.geometry import corridor_polygon, waypoints

GRID_NAME = os.environ.get("ECOTRACK_GRID", "corridor")
if GRID_NAME not in ("corridor", "region"):
    raise ValueError(f"ECOTRACK_GRID must be 'corridor' or 'region', not {GRID_NAME!r}")
GRID_DIR = DATA_INTERIM / ("grid" if GRID_NAME == "corridor" else "grid_region")
SUFFIX = "" if GRID_NAME == "corridor" else "_region"  # appended to every downstream output name


def build():
    return build_corridor() if GRID_NAME == "corridor" else build_region()


def build_corridor():
    cfg = load_config()
    utm = f"EPSG:{cfg['region']['utm_epsg']}"
    to_utm = pyproj.Transformer.from_crs("EPSG:4326", utm, always_xy=True).transform
    to_wgs = pyproj.Transformer.from_crs(utm, "EPSG:4326", always_xy=True).transform
    size = cfg["phase2"]["cell_km"] * 1000
    corr = transform(to_utm, corridor_polygon())
    x0, y0, x1, y1 = corr.bounds
    xs = np.arange(np.floor(x0 / size) * size, x1, size)
    ys = np.arange(np.floor(y0 / size) * size, y1, size)

    src = json.loads((OUTPUTS / "phase1" / "city_fit.json").read_text())
    src_xy = to_utm(src["source_lon"], src["source_lat"])
    cluster_of = {m: c for c, members in cfg["clusters"].items() for m in members}
    wps = [(to_utm(w["lon"], w["lat"]), cluster_of[w["name"]]) for w in waypoints()]

    rows, polys = [], []
    for j, y in enumerate(ys):
        for i, x in enumerate(xs):
            cell = box(x, y, x + size, y + size)
            frac = cell.intersection(corr).area / cell.area
            if frac < cfg["phase2"]["min_frac_in_corridor"]:
                continue
            cx, cy = x + size / 2, y + size / 2
            nearest = min(wps, key=lambda w: np.hypot(w[0][0] - cx, w[0][1] - cy))
            lon, lat = to_wgs(cx, cy)
            cid = f"c{j:03d}_{i:03d}"
            rows.append({"cell_id": cid, "row": j, "col": i, "x_utm": cx, "y_utm": cy,
                         "lat": round(lat, 5), "lon": round(lon, 5), "frac_in_corridor": round(frac, 3),
                         "cluster": nearest[1],
                         "dist_to_source_km": round(np.hypot(cx - src_xy[0], cy - src_xy[1]) / 1000, 2)})
            polys.append({"type": "Feature", "properties": {"cell_id": cid},
                          "geometry": mapping(transform(to_wgs, cell))})

    GRID_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(GRID_DIR / "cells.csv", index=False)
    (GRID_DIR / "cells.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": polys}))
    print(f"{len(df)} cells of {size / 1000:.0f} km (>= {cfg['phase2']['min_frac_in_corridor']:.0%} inside the corridor); "
          f"total cell area {len(df) * size ** 2 / 1e6:.0f} km² vs corridor {corr.area / 1e6:.0f} km²")
    print(df.cluster.value_counts().to_dict())
    return df


def build_region():
    """All 1 km cells near the source (training domain, D22) + every corridor cell, same alignment."""
    cfg = load_config()
    reg = cfg["phase2"]["region"]
    utm = f"EPSG:{cfg['region']['utm_epsg']}"
    to_utm = pyproj.Transformer.from_crs("EPSG:4326", utm, always_xy=True).transform
    to_wgs = pyproj.Transformer.from_crs(utm, "EPSG:4326", always_xy=True).transform
    size = cfg["phase2"]["cell_km"] * 1000
    corr_cells = pd.read_csv(DATA_INTERIM / "grid" / "cells.csv")
    corr_by_xy = {(round(r.x_utm), round(r.y_utm)): r for r in corr_cells.itertuples()}

    src = json.loads((OUTPUTS / "phase1" / "city_fit.json").read_text())
    sx, sy = to_utm(src["source_lon"], src["source_lat"])
    cb = cfg["inversion"]["cube_box"]
    margin = reg["box_margin_km"] * 1000
    bx0, by0 = to_utm(cb["lon_min"], cb["lat_min"])
    bx1, by1 = to_utm(cb["lon_max"], cb["lat_max"])
    R = reg["radius_km"] * 1000
    x0 = np.floor(min(sx - R, corr_cells.x_utm.min()) / size) * size
    y0 = np.floor(min(sy - R, corr_cells.y_utm.min()) / size) * size
    x1 = max(sx + R, corr_cells.x_utm.max() + size)
    y1 = max(sy + R, corr_cells.y_utm.max() + size)

    rows, polys = [], []
    for y in np.arange(y0, y1, size):
        for x in np.arange(x0, x1, size):
            cx, cy = x + size / 2, y + size / 2
            corr = corr_by_xy.get((round(cx), round(cy)))
            near = np.hypot(cx - sx, cy - sy) <= R
            inside_box = (bx0 + margin <= cx <= bx1 - margin) and (by0 + margin <= cy <= by1 - margin)
            if corr is None and not (near and inside_box):
                continue
            lon, lat = to_wgs(cx, cy)
            cid = f"g{int(cx // 1000):04d}_{int(cy // 1000):05d}"  # UTM km of the centre: unique and stable
            rows.append({"cell_id": cid, "x_utm": cx, "y_utm": cy, "lat": round(lat, 5), "lon": round(lon, 5),
                         "in_corridor": corr is not None,
                         "corridor_cell_id": corr.cell_id if corr is not None else "",
                         "frac_in_corridor": corr.frac_in_corridor if corr is not None else 0.0,
                         "cluster": corr.cluster if corr is not None else "outside",
                         "dist_to_source_km": round(np.hypot(cx - sx, cy - sy) / 1000, 2)})
            polys.append({"type": "Feature", "properties": {"cell_id": cid},
                          "geometry": mapping(transform(to_wgs, box(x, y, x + size, y + size)))})

    GRID_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(GRID_DIR / "cells.csv", index=False)
    (GRID_DIR / "cells.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": polys}))
    print(f"Regional grid: {len(df)} cells ({df.in_corridor.sum()} corridor + {(~df.in_corridor).sum()} outside); "
          f"radius {reg['radius_km']} km, >= {reg['box_margin_km']} km inside the cube box")
    print(f"distance to source: max {df.dist_to_source_km.max():.1f} km; lat {df.lat.min():.3f}-{df.lat.max():.3f}, "
          f"lon {df.lon.min():.3f}-{df.lon.max():.3f}")
    return df


def load_cells():
    return pd.read_csv(GRID_DIR / "cells.csv")


if __name__ == "__main__":
    build()
