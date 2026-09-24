"""
Surface elevation on the Phase 1 cube grid (SRTM 30 m, averaged to 0.01 degree).

Needed for D4: a total CO column scales with the air mass above the ground, so the Western Ghats
(Konkan near sea level vs the Pune plateau at ~560 m) imprint a ~6% terrain pattern on TROPOMI CO,
larger than Pune's own signal. Dividing by the relative air mass exp(-z/H) removes it.

Usage:
    python -m ecotrack.acquire.dem
"""

import ee
import numpy as np

from ecotrack.acquire.ee_utils import init_ee
from ecotrack.acquire.tropomi_cube import grid
from ecotrack.config import DATA_INTERIM, load_config

OUT = DATA_INTERIM / "dem_cube_grid.npz"


def run():
    cfg = load_config()
    lat, lon, transform, rect = grid(cfg)
    srtm = ee.Image("USGS/SRTMGL1_003").select("elevation")
    mean = (srtm.reduceResolution(ee.Reducer.mean(), maxPixels=4096)
            .reproject(crs="EPSG:4326", crsTransform=transform))
    arr = np.array(mean.sampleRectangle(region=rect, defaultValue=0).get("elevation").getInfo(), dtype="float64")
    assert arr.shape == (len(lat), len(lon)), arr.shape
    np.savez_compressed(OUT, elevation_m=arr, lat=lat, lon=lon)
    print(f"Saved {OUT}: elevation {arr.min():.0f}-{arr.max():.0f} m (median {np.median(arr):.0f} m)")


if __name__ == "__main__":
    init_ee()
    run()
