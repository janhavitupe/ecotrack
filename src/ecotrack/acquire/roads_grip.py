"""
Phase 2 — road density from GRIP4 (Global Roads Inventory Project; Meijer et al. 2018,
Environ. Res. Lett. 13, 064006) on the 1 km grid, computed entirely in Earth Engine.

Why: the OpenStreetMap Overpass servers (and mirrors, and Geofabrik) were overloaded for hours on
2026-10-01, so the OSM layer (roads_osm.py) downloads very slowly. GRIP4 is a published global road
dataset, partly built from OSM, hosted in the Earth Engine community catalogue. It's used as
(a) a fallback if OSM can't complete and (b) an independent cross-check once it does.

GRIP road type GP_RTP: 1 highways, 2 primary, 3 secondary, 4 tertiary, 5 local → mapped to the
same classes as the OSM layer: major = 1+2, mid = 3+4, minor = 5. Note the older sources
(e.g. GP_RSY = 2014 for Pune segments) vs today's OSM.

Output: data/interim/grid/layers_roads_grip.csv (same columns as layers_roads.csv)

Usage:
    python -m ecotrack.acquire.roads_grip
"""

import ee
import pandas as pd

from ecotrack.acquire.ee_utils import init_ee
from ecotrack.acquire.grid_layers_gee import cells_fc
from ecotrack.grid import GRID_DIR

GRIP = "projects/sat-io/open-datasets/GRIP4/South-East-Asia"
CLASSES = {"road_major_km": [1, 2], "road_mid_km": [3, 4], "road_minor_km": [5]}
BATCH = 40


def run():
    cells = cells_fc()
    roads = ee.FeatureCollection(GRIP).filterBounds(cells.geometry().bounds())

    def per_cell(cell):
        geom = cell.geometry()
        here = roads.filterBounds(geom)
        props = {}
        for name, types in CLASSES.items():
            sub = here.filter(ee.Filter.inList("GP_RTP", types))
            length_m = sub.map(lambda f: f.set("len", f.geometry().intersection(geom, 1).length(1))).aggregate_sum("len")
            props[name] = ee.Number(length_m).divide(1000)
        return cell.set(props)

    n = cells.size().getInfo()
    lst = cells.toList(n)
    rows = []
    for i in range(0, n, BATCH):
        part = ee.FeatureCollection(ee.List(lst.slice(i, min(i + BATCH, n)))).map(per_cell)
        for f in part.getInfo()["features"]:
            p = f["properties"]
            rows.append({"cell_id": p["cell_id"], **{k: p.get(k, 0.0) for k in CLASSES}})
        print(f"  cells {min(i + BATCH, n)}/{n}")
    df = pd.DataFrame(rows)
    df["road_total_km"] = df[list(CLASSES)].sum(axis=1)
    df.to_csv(GRID_DIR / "layers_roads_grip.csv", index=False)
    print(f"GRIP4 roads per cell: total median {df.road_total_km.median():.1f} km, max {df.road_total_km.max():.1f}; "
          f"cells with a major road {(df.road_major_km > 0).sum()} of {len(df)}")


if __name__ == "__main__":
    init_ee()
    run()
