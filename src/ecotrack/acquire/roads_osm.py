"""
Phase 2 — OpenStreetMap road density on the 1 km grid (a static layer).

Downloads drivable roads over the grid area from the Overpass API (in tiles, to stay under its
limits), clips them to each 1 km cell in UTM metres, and sums length per road class:
  road_major_km   motorway, trunk, primary (+ their links)   → heavy and through traffic
  road_mid_km     secondary, tertiary (+ links)
  road_minor_km   residential, unclassified, living_street
  road_total_km   all of the above (cells are 1 km², so this is also km per km²)
Footpaths, tracks and service roads are excluded (not traffic-emission relevant).

Note: OSM is a snapshot of *today's* map (downloaded 2026), used for all study years. Pune's road
network changed little over 2019–2024 compared with the 1 km scale, but this is a stated assumption.

Output: data/interim/grid/layers_roads.csv

Usage:
    python -m ecotrack.acquire.roads_osm
"""

import json
import time
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd
import pyproj
from shapely import STRtree
from shapely.geometry import LineString, box
from shapely.ops import transform

from ecotrack.config import DATA_INTERIM, load_config
from ecotrack.grid import GRID_DIR, load_cells

# The main server is often overloaded (504); mirrors serve the same OSM data.
MIRRORS = ["https://overpass-api.de/api/interpreter",
           "https://overpass.kumi.systems/api/interpreter",
           "https://overpass.private.coffee/api/interpreter"]
TILE_CACHE = DATA_INTERIM / "osm_road_tiles"  # one JSON per tile, so reruns resume
CLASSES = {
    "road_major_km": ["motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link"],
    "road_mid_km": ["secondary", "secondary_link", "tertiary", "tertiary_link"],
    "road_minor_km": ["residential", "unclassified", "living_street"],
}
TILE_DEG = 0.05  # small tiles keep each Overpass response modest (0.1 deg tiles were refused under load)


def _query(q, cache):
    for attempt in range(6):
        url = MIRRORS[attempt % len(MIRRORS)]
        try:
            req = urllib.request.Request(url, data=urllib.parse.urlencode({"data": q}).encode(),
                                         headers={"User-Agent": "EcoTrack-final-year-project/0.1 (academic research)"})
            with urllib.request.urlopen(req, timeout=180) as r:
                els = json.load(r)["elements"]
            TILE_CACHE.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(els))
            return els
        except Exception as exc:  # busy server (429/504/timeout): try the next mirror
            print(f"    attempt {attempt + 1} via {url.split('/')[2]}: {exc}")
            time.sleep(10)
    raise RuntimeError("Overpass failed on all mirrors for one tile; rerun later (finished tiles are cached)")


def fetch_tile(s, w, n, e):
    """All road ways of a tile, each tagged with our class. Uses a cached full-tile download if
    present (first runs); otherwise one light query per class with `out skel geom` (geometry only,
    no tags: the class is known from the query), which keeps responses small for a busy server."""
    full = TILE_CACHE / f"{s:.3f}_{w:.3f}.json"
    if full.exists():
        cls_of = {h: c for c, hs in CLASSES.items() for h in hs}
        return [dict(el, cls=cls_of[el["tags"]["highway"]]) for el in json.loads(full.read_text())], True
    out, cached_all = [], True
    for cls, highways in CLASSES.items():
        cache = TILE_CACHE / f"{s:.3f}_{w:.3f}_{cls}.json"
        if cache.exists():
            els = json.loads(cache.read_text())
        else:
            cached_all = False
            q = f'[out:json][timeout:120];way["highway"~"^({"|".join(highways)})$"]({s},{w},{n},{e});out skel geom;'
            els = _query(q, cache)
            time.sleep(3)
        out += [dict(el, cls=cls) for el in els]
    return out, cached_all


def run():
    cfg = load_config()
    cells = load_cells()
    to_utm = pyproj.Transformer.from_crs("EPSG:4326", f"EPSG:{cfg['region']['utm_epsg']}", always_xy=True).transform
    pad = 0.01
    s, n = cells.lat.min() - pad, cells.lat.max() + pad
    w, e = cells.lon.min() - pad, cells.lon.max() + pad

    ways = {}
    for lat0 in np.arange(s, n, TILE_DEG):
        for lon0 in np.arange(w, e, TILE_DEG):
            els, cached = fetch_tile(lat0, lon0, min(lat0 + TILE_DEG, n), min(lon0 + TILE_DEG, e))
            for el in els:  # ways crossing tile edges come back twice; keep one copy
                ways[el["id"]] = el
            print(f"  tile {lat0:.2f},{lon0:.2f}: {len(els)} ways (total unique {len(ways)}){' [cached]' if cached else ''}")
            if not cached:
                time.sleep(5)

    lines, labels = [], []
    for el in ways.values():
        pts = el.get("geometry", [])
        if len(pts) < 2:
            continue
        lines.append(transform(to_utm, LineString([(p["lon"], p["lat"]) for p in pts])))
        labels.append(el["cls"])
    tree = STRtree(lines)

    half = cfg["phase2"]["cell_km"] * 500
    rows = []
    for c in cells.itertuples():
        cell = box(c.x_utm - half, c.y_utm - half, c.x_utm + half, c.y_utm + half)
        out = {"cell_id": c.cell_id, **{k: 0.0 for k in CLASSES}}
        for idx in tree.query(cell):
            out[labels[idx]] += lines[idx].intersection(cell).length / 1000
        rows.append(out)
    df = pd.DataFrame(rows)
    df["road_total_km"] = df[list(CLASSES)].sum(axis=1)
    df.to_csv(GRID_DIR / "layers_roads.csv", index=False)
    print(f"{len(ways)} road ways; per cell: total median {df.road_total_km.median():.1f} km, "
          f"max {df.road_total_km.max():.1f}; cells with a major road: {(df.road_major_km > 0).sum()} of {len(df)}")


if __name__ == "__main__":
    run()
