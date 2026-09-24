"""
G4 — Check each configured waypoint against OpenStreetMap (Nominatim geocoder).

Nominatim returns a place's node or area centroid, which for a neighbourhood can itself sit a
few hundred metres from where "the place" really is on the highway. Treat a flag as "look at
the map", not as the answer. After checking, edit configs/study.yaml: correct lat/lon and set
status to e.g. "verified OSM 2026-09-24".

Usage:
    python -m ecotrack.feasibility.g4_verify_waypoints
"""

import json
import math
import time
import urllib.parse
import urllib.request

from ecotrack.config import OUTPUTS
from ecotrack.geometry import waypoints

NOMINATIM = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "EcoTrack-final-year-project/0.1 (academic research)"  # required by Nominatim policy
FLAG_M = 500


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def geocode(name: str):
    query = urllib.parse.urlencode({"q": f"{name}, Pune, Maharashtra, India", "format": "json", "limit": 1})
    req = urllib.request.Request(f"{NOMINATIM}?{query}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        hits = json.load(resp)
    return hits[0] if hits else None


def run():
    report = []
    for w in waypoints():
        hit = geocode(w["name"])
        time.sleep(1.1)  # Nominatim usage policy: max 1 request per second
        if not hit:
            print(f"  {w['name']:18s} no OSM match — check manually")
            report.append({**w, "osm": None})
            continue
        lat, lon = float(hit["lat"]), float(hit["lon"])
        d = haversine_m(w["lat"], w["lon"], lat, lon)
        flag = "CHECK" if d > FLAG_M else "ok"
        print(f"  {w['name']:18s} config {w['lat']:.4f},{w['lon']:.4f}  OSM {lat:.4f},{lon:.4f}  {d:6.0f} m  {flag}")
        report.append({**w, "osm_lat": lat, "osm_lon": lon, "osm_display": hit.get("display_name"),
                       "distance_m": round(d), "flag": flag})

    out = OUTPUTS / "feasibility" / "g4_waypoints.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(f"\nSaved {out}. Now open data/interim/corridor.geojson on geojson.io and check the corridor "
          "covers Bhosari/Chinchwad MIDC and Talegaon MIDC.")


if __name__ == "__main__":
    run()
