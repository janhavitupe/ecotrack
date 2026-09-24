"""
EcoTrack — Study area definition
Corridor: Shivajinagar -> Talegaon Dabhade, along the Old Mumbai-Pune Highway (MSH-4 / old NH4)

WHY A CORRIDOR POLYGON INSTEAD OF A SQUARE BOUNDING BOX:
A square box over this stretch would include a lot of hill/agricultural land north and
south of the highway that has no traffic or industrial relevance. A buffered line
(a "corridor polygon") keeps every grid cell relevant to the research question.

IMPORTANT — before trusting these coordinates for anything scientific:
The waypoint coordinates below are approximate (sourced from general place knowledge +
one verified point for Talegaon Dabhade). TASK 1 of Week 1 (see WEEK1_CHECKLIST.md) is
to verify/refine every waypoint against OpenStreetMap and record the corrected values
here with a comment showing the source and date. Do not run Phase 1 analysis on
unverified coordinates.
"""

import json

try:
    from shapely.geometry import LineString, mapping
    from shapely.ops import transform
    import pyproj
    HAVE_GEO_LIBS = True
except ImportError:
    HAVE_GEO_LIBS = False


# ---------------------------------------------------------------------------
# 1. Waypoints along the Old Mumbai-Pune Highway, Shivajinagar -> Talegaon Dabhade
#    Format: (name, lat, lon, category)
#    category is used later to tag which experiment sub-zone each point belongs to
# ---------------------------------------------------------------------------
WAYPOINTS = [
    ("Shivajinagar",       18.5308, 73.8478, "traffic_urban_core"),
    ("Khadki",             18.5642, 73.8508, "traffic_defense_industrial"),
    ("Dapodi",             18.5793, 73.8309, "industrial"),
    ("Kasarwadi",          18.5975, 73.8258, "industrial"),
    ("Pimpri",             18.6298, 73.8131, "industrial_traffic"),
    ("Chinchwad",          18.6298, 73.7997, "industrial_traffic"),
    ("Akurdi",             18.6480, 73.7670, "industrial"),
    ("Nigdi",              18.6553, 73.7639, "traffic"),
    ("Dehu Road",          18.7167, 73.7500, "traffic_cantonment"),
    ("Talegaon Dabhade",   18.7213, 73.6873, "industrial_traffic"),  # verified via India Post record
]

# Rough overall bounding box (buffer already included) for quick data-pull queries
# where a simple rectangle is good enough (e.g. first TROPOMI test pull).
BBOX = {
    "lat_min": 18.50,
    "lat_max": 18.75,
    "lon_min": 73.65,
    "lon_max": 73.87,
}

# Corridor buffer width in km — how far off the highway centerline to include.
# 3-4 km captures MIDC industrial plots set back from the road without pulling in
# unrelated hill terrain. Adjust after Week 1 ground-truthing.
CORRIDOR_BUFFER_KM = 3.5


def build_corridor_polygon(buffer_km: float = CORRIDOR_BUFFER_KM):
    """
    Build a buffered polygon around the waypoint line, in WGS84 (lat/lon).
    Requires shapely + pyproj. Returns a GeoJSON-style dict.
    """
    if not HAVE_GEO_LIBS:
        raise ImportError(
            "Install shapely and pyproj first: pip install shapely pyproj"
        )

    coords_lonlat = [(lon, lat) for _, lat, lon, _ in WAYPOINTS]
    line = LineString(coords_lonlat)

    # Project to a local metric CRS (UTM zone 43N covers Pune) to buffer in real km,
    # then project back to WGS84 for storage/use in GEE, QGIS, etc.
    project_to_utm = pyproj.Transformer.from_crs(
        "EPSG:4326", "EPSG:32643", always_xy=True
    ).transform
    project_to_wgs84 = pyproj.Transformer.from_crs(
        "EPSG:32643", "EPSG:4326", always_xy=True
    ).transform

    line_utm = transform(project_to_utm, line)
    buffered_utm = line_utm.buffer(buffer_km * 1000)
    buffered_wgs84 = transform(project_to_wgs84, buffered_utm)

    return mapping(buffered_wgs84)


def save_corridor_geojson(path: str = "corridor.geojson"):
    polygon = build_corridor_polygon()
    feature_collection = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": "Shivajinagar-Talegaon Dabhade corridor",
                    "buffer_km": CORRIDOR_BUFFER_KM,
                },
                "geometry": polygon,
            }
        ]
        + [
            {
                "type": "Feature",
                "properties": {"name": name, "category": category},
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
            }
            for name, lat, lon, category in WAYPOINTS
        ],
    }
    with open(path, "w") as f:
        json.dump(feature_collection, f, indent=2)
    print(f"Saved corridor + waypoints to {path}")


if __name__ == "__main__":
    print("Waypoints:")
    for name, lat, lon, category in WAYPOINTS:
        print(f"  {name:20s} {lat:.4f}, {lon:.4f}  [{category}]")
    print(f"\nBounding box (for quick pulls): {BBOX}")

    if HAVE_GEO_LIBS:
        save_corridor_geojson()
    else:
        print(
            "\nshapely/pyproj not installed — skipping polygon build.\n"
            "Run: pip install shapely pyproj"
        )
