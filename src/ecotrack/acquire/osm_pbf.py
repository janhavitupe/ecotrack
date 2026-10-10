"""
Phase 2 — OpenStreetMap roads and industrial land on the 1 km grid, from a Geofabrik extract.

Why this file exists: the Overpass API (roads_osm.py) was overloaded for days (504/429, 16 of 35
tiles). Geofabrik publishes the same OpenStreetMap data as daily regional files; the "India —
western zone" extract (~220 MB, .osm.pbf) contains the whole corridor. Reading it locally needs no
server at all, and the file is dated, so the snapshot is reproducible (D20 update).

Layers (static; OSM is today's map, used for all study years, as stated in roads_osm.py):
  road_major/mid/minor/total_km   same road classes as roads_osm.py (km of road per 1 km cell)
  industrial_frac                 share of the cell covered by landuse=industrial (MIDC estates,
                                  factories): the proposal's "industrial-land fraction" (§Phase 3)

Download (once):
    curl -L -o data/raw/osm/western-zone-<date>.osm.pbf https://download.geofabrik.de/asia/india/western-zone-latest.osm.pbf
    (check against the .md5 file published next to it)

Output: data/interim/grid/layers_roads.csv, layers_landuse.csv, osm_source.json

Usage:
    python -m ecotrack.acquire.osm_pbf
"""

import gc
import glob
import json

import osmium
import pandas as pd
import pyproj
import shapely.wkb
from shapely import STRtree
from shapely.geometry import LineString, box
from shapely.ops import transform, unary_union

from ecotrack.acquire.roads_osm import CLASSES
from ecotrack.config import DATA_INTERIM, DATA_RAW, load_config
from ecotrack.grid import GRID_DIR, load_cells

PBF_GLOB = str(DATA_RAW / "osm" / "*.osm.pbf")
# Node coordinates are cached in a file on disk, not in RAM: the in-memory cache needs ~1-2 GB and
# failed with MemoryError on an 8 GB laptop with a nearly full C: drive (no room to grow the page file).
NODE_CACHE = DATA_INTERIM / "osm_node_locations.idx"


def read_osm(pbf, bbox):
    """Road ways (with class) and industrial-landuse polygons inside bbox (w, s, e, n), in lon/lat."""
    w, s, e, n = bbox
    inside = lambda lon, lat: w <= lon <= e and s <= lat <= n
    cls_of = {h: c for c, hs in CLASSES.items() for h in hs}
    wkb = osmium.geom.WKBFactory()
    roads, industrial, skipped = [], [], 0
    NODE_CACHE.unlink(missing_ok=True)
    fp = (osmium.FileProcessor(pbf).with_locations(f"sparse_file_array,{NODE_CACHE}")
          .with_areas(osmium.filter.TagFilter(("landuse", "industrial")))
          .with_filter(osmium.filter.KeyFilter("highway", "landuse")))
    for obj in fp:
        try:
            if obj.is_way() and obj.tags.get("highway") in cls_of:
                pts = [(nd.lon, nd.lat) for nd in obj.nodes]
                if len(pts) >= 2 and any(inside(*p) for p in pts):
                    roads.append((cls_of[obj.tags["highway"]], LineString(pts)))
            elif obj.is_area() and obj.tags.get("landuse") == "industrial":
                geom = shapely.wkb.loads(wkb.create_multipolygon(obj), hex=True)
                if geom.intersects(box(w, s, e, n)):
                    industrial.append(geom)
        except (osmium.InvalidLocationError, RuntimeError):
            skipped += 1  # objects cut by the extract boundary (far from Pune)
    del fp
    gc.collect()  # release osmium's handle on the cache file
    try:
        NODE_CACHE.unlink(missing_ok=True)
    except PermissionError:  # still held on Windows: it is removed at the start of the next run
        pass
    return roads, industrial, skipped


def run():
    cfg = load_config()
    cells = load_cells()
    pbfs = sorted(glob.glob(PBF_GLOB))
    if not pbfs:
        raise SystemExit(f"No OSM extract found ({PBF_GLOB}); see the download line in this file's docstring")
    pbf = pbfs[-1]
    to_utm = pyproj.Transformer.from_crs("EPSG:4326", f"EPSG:{cfg['region']['utm_epsg']}", always_xy=True).transform
    pad = 0.02
    bbox = (cells.lon.min() - pad, cells.lat.min() - pad, cells.lon.max() + pad, cells.lat.max() + pad)
    print(f"Reading {pbf} (whole file is scanned; takes a few minutes)...")
    roads, industrial, skipped = read_osm(pbf, bbox)
    print(f"  {len(roads)} road ways, {len(industrial)} industrial areas in the box ({skipped} boundary objects skipped)")

    lines = [transform(to_utm, g) for _, g in roads]
    labels = [c for c, _ in roads]
    tree = STRtree(lines)
    ind = unary_union([transform(to_utm, g) for g in industrial])  # union: overlapping polygons counted once

    half = cfg["phase2"]["cell_km"] * 500
    road_rows, land_rows = [], []
    for c in cells.itertuples():
        cell = box(c.x_utm - half, c.y_utm - half, c.x_utm + half, c.y_utm + half)
        r = {"cell_id": c.cell_id, **{k: 0.0 for k in CLASSES}}
        for idx in tree.query(cell):
            r[labels[idx]] += lines[idx].intersection(cell).length / 1000
        road_rows.append(r)
        land_rows.append({"cell_id": c.cell_id, "industrial_frac": ind.intersection(cell).area / cell.area})
    rd = pd.DataFrame(road_rows)
    rd["road_total_km"] = rd[list(CLASSES)].sum(axis=1)
    rd.to_csv(GRID_DIR / "layers_roads.csv", index=False)
    ld = pd.DataFrame(land_rows)
    ld.to_csv(GRID_DIR / "layers_landuse.csv", index=False)
    (GRID_DIR / "osm_source.json").write_text(json.dumps(
        {"source": "Geofabrik OpenStreetMap extract", "file": pbf.replace("\\", "/").split("/")[-1],
         "road_ways": len(roads), "industrial_areas": len(industrial)}, indent=2))
    print(f"Roads per cell: total median {rd.road_total_km.median():.1f} km, max {rd.road_total_km.max():.1f}; "
          f"cells with a major road {(rd.road_major_km > 0).sum()} of {len(rd)}")
    print(f"Industrial land: grid mean {100 * ld.industrial_frac.mean():.1f}%, "
          f"cells > 25% industrial: {(ld.industrial_frac > 0.25).sum()}")


if __name__ == "__main__":
    run()
