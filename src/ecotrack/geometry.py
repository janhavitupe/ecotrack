"""
Study-area geometry: waypoints, corridor polygon, cluster zones.

Why a corridor polygon instead of a square box: a box over this stretch pulls in hill and
agricultural land with no traffic/industrial relevance. A buffered highway line keeps every
grid cell relevant to the research question.

Waypoints live in configs/study.yaml. Do not run Phase 1 analysis until every waypoint has
status "verified" (see ecotrack.feasibility.g4_verify_waypoints).

Usage:
    python -m ecotrack.geometry          # prints waypoints, writes data/interim/corridor.geojson
"""

import json

import pyproj
from shapely.geometry import LineString, Point, mapping
from shapely.ops import transform

from ecotrack.config import DATA_INTERIM, load_config

_cfg = load_config()
_utm = f"EPSG:{_cfg['region']['utm_epsg']}"
_to_utm = pyproj.Transformer.from_crs("EPSG:4326", _utm, always_xy=True).transform
_to_wgs84 = pyproj.Transformer.from_crs(_utm, "EPSG:4326", always_xy=True).transform


def waypoints() -> list[dict]:
    return _cfg["waypoints"]


def bbox() -> dict:
    return _cfg["region"]["bbox"]


def corridor_polygon(buffer_km: float | None = None):
    """Highway centreline buffered by buffer_km (buffered in UTM metres), returned in WGS84.
    Falls back to the waypoint line if the config has no centreline."""
    buffer_km = _cfg["region"]["corridor_buffer_km"] if buffer_km is None else buffer_km
    if _cfg.get("centreline"):
        line = LineString([(lon, lat) for lat, lon in _cfg["centreline"]])
    else:
        line = LineString([(w["lon"], w["lat"]) for w in waypoints()])
    area = transform(_to_utm, line).buffer(buffer_km * 1000)
    for extra in _cfg.get("extra_areas", []):
        centre = transform(_to_utm, Point(extra["lon"], extra["lat"]))
        area = area.union(centre.buffer(extra["radius_km"] * 1000))
    return transform(_to_wgs84, area)


def cluster_zones() -> dict:
    """Cluster name -> WGS84 polygon: union of cluster_radius_km circles around its waypoints."""
    by_name = {w["name"]: w for w in waypoints()}
    radius_m = _cfg["cluster_radius_km"] * 1000
    zones = {}
    for cluster, members in _cfg["clusters"].items():
        circles = [
            transform(_to_utm, Point(by_name[m]["lon"], by_name[m]["lat"])).buffer(radius_m)
            for m in members
        ]
        union = circles[0]
        for c in circles[1:]:
            union = union.union(c)
        zones[cluster] = transform(_to_wgs84, union)
    return zones


def save_corridor_geojson(path=DATA_INTERIM / "corridor.geojson"):
    features = [
        {
            "type": "Feature",
            "properties": {"name": "corridor", "buffer_km": _cfg["region"]["corridor_buffer_km"]},
            "geometry": mapping(corridor_polygon()),
        }
    ]
    features += [
        {"type": "Feature", "properties": {"name": name, "kind": "cluster"}, "geometry": mapping(poly)}
        for name, poly in cluster_zones().items()
    ]
    features += [
        {
            "type": "Feature",
            "properties": {"name": w["name"], "category": w["category"], "status": w["status"]},
            "geometry": {"type": "Point", "coordinates": [w["lon"], w["lat"]]},
        }
        for w in waypoints()
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, indent=2)
    print(f"Saved corridor, clusters and waypoints to {path}")


if __name__ == "__main__":
    for w in waypoints():
        print(f"  {w['name']:18s} {w['lat']:.4f}, {w['lon']:.4f}  [{w['category']}] ({w['status']})")
    area_km2 = transform(_to_utm, corridor_polygon()).area / 1e6
    print(f"\nCorridor area: {area_km2:.0f} km^2 (~{area_km2:.0f} grid cells at 1 km)")
    save_corridor_geojson()
