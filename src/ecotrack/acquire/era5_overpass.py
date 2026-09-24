"""
Phase 1 input: ERA5 wind and boundary-layer height at each usable TROPOMI overpass.

For every overpass that passed G2 (valid_fraction >= min_valid_fraction), take the ERA5 hour
nearest the overpass and sample it at each cluster centroid. Winds are kept at three levels:
10 m, 100 m and 850 hPa. Pune is ~560 m above sea level, so 850 hPa is ~1 km above ground,
inside the afternoon boundary layer: the level that best represents plume transport. Which
level (or average) the inversion uses is a Phase 1 sensitivity test, not fixed here.

Usage (after g2_tropomi_coverage has produced outputs/feasibility/g2_tropomi_overpasses.csv):
    python -m ecotrack.acquire.era5_overpass
"""

import argparse

import ee
import numpy as np
import pandas as pd

from ecotrack.acquire.ee_utils import init_ee
from ecotrack.config import DATA_INTERIM, OUTPUTS, load_config
from ecotrack.geometry import cluster_zones

COLLECTION = "ECMWF/ERA5/HOURLY"
BANDS = {
    "u_component_of_wind_10m": "u10", "v_component_of_wind_10m": "v10",
    "u_component_of_wind_100m": "u100", "v_component_of_wind_100m": "v100",
    "u_component_of_wind_850hPa": "u850", "v_component_of_wind_850hPa": "v850",
    "boundary_layer_height": "blh",
}
ERA5_SCALE_M = 27830  # 0.25 degree native grid
CHUNK = 150           # ERA5 hours per Earth Engine request


def usable_overpasses(cfg) -> pd.DataFrame:
    df = pd.read_csv(OUTPUTS / "feasibility" / "g2_tropomi_overpasses.csv")
    df = df[df.valid_fraction >= cfg["tropomi"]["min_valid_fraction"]].copy()
    df["time_utc"] = pd.to_datetime(df.time)
    df["era5_hour"] = df.time_utc.dt.round("h")
    return df[["time_utc", "era5_hour", "valid_fraction", "mean_no2"]]


def cluster_points() -> ee.FeatureCollection:
    return ee.FeatureCollection([
        ee.Feature(ee.Geometry.Point([poly.centroid.x, poly.centroid.y]), {"cluster": name})
        for name, poly in cluster_zones().items()
    ])


def sample_hours(hours: list[pd.Timestamp], points: ee.FeatureCollection) -> list[dict]:
    ids = [h.strftime("%Y%m%dT%H") for h in hours]
    coll = ee.ImageCollection(COLLECTION).filter(ee.Filter.inList("system:index", ids)).select(
        list(BANDS), list(BANDS.values())
    )

    def per_image(img):
        return img.sampleRegions(collection=points, scale=ERA5_SCALE_M, geometries=False).map(
            lambda f: f.set("era5_index", img.get("system:index"))
        )

    feats = coll.map(per_image).flatten().getInfo()["features"]
    return [f["properties"] for f in feats]


def add_derived(df: pd.DataFrame) -> pd.DataFrame:
    for lvl in ("10", "100", "850"):
        u, v = df[f"u{lvl}"], df[f"v{lvl}"]
        df[f"ws{lvl}"] = np.hypot(u, v)
        # Meteorological convention: direction the wind blows FROM, degrees clockwise from north.
        df[f"wd{lvl}"] = (270 - np.degrees(np.arctan2(v, u))) % 360
    return df


def run():
    cfg = load_config()
    over = usable_overpasses(cfg)
    hours = sorted(over.era5_hour.unique())
    print(f"{len(over)} usable overpasses -> {len(hours)} distinct ERA5 hours")
    points = cluster_points()

    rows = []
    for i in range(0, len(hours), CHUNK):
        chunk = [pd.Timestamp(h) for h in hours[i: i + CHUNK]]
        rows += sample_hours(chunk, points)
        print(f"  sampled {min(i + CHUNK, len(hours))}/{len(hours)} hours")

    met = pd.DataFrame(rows)
    met["era5_hour"] = pd.to_datetime(met.pop("era5_index"), format="%Y%m%dT%H")
    met = add_derived(met)
    out = over.merge(met, on="era5_hour", how="left")

    missing = out.u850.isna().sum()
    if missing:
        print(f"WARNING: {missing} overpass-cluster rows have no ERA5 match")
    path = DATA_INTERIM / "era5" / "overpass_met.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False)
    print(f"Saved {path} ({len(out)} rows)")

    summary = out.groupby("cluster")[["ws10", "ws100", "ws850", "blh"]].describe(percentiles=[0.1, 0.5, 0.9])
    print(summary.loc[:, (slice(None), ["10%", "50%", "90%"])].round(1).to_string())


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    init_ee()
    run()
