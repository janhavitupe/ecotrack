"""
Phase 2 — the 1 km modelling grid over the corridor.

Cells are 1 km squares in UTM 43N (real kilometres), aligned to whole kilometres. A cell is kept
if at least `min_frac_in_corridor` of its area lies inside the corridor polygon (D15). Each cell
gets: an id, centre lat/lon, its fraction inside the corridor, its cluster (nearest waypoint's
cluster, as in the flux-divergence zones) and its distance to the Phase 1 emission source.

Outputs: data/interim/grid/cells.csv and cells.geojson (WGS84 polygons, used by Earth Engine).

Usage:
    python -m ecotrack.grid
"""

import json

import numpy as np
import pandas as pd
import pyproj
from shapely.geometry import box, mapping
from shapely.ops import transform

from ecotrack.config import DATA_INTERIM, OUTPUTS, load_config
from ecotrack.geometry import corridor_polygon, waypoints

GRID_DIR = DATA_INTERIM / "grid"


def build():
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


def load_cells():
    return pd.read_csv(GRID_DIR / "cells.csv")


if __name__ == "__main__":
    build()
