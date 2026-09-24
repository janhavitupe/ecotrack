"""
ODIAC v2024 monthly 1 km fossil-fuel CO2, clipped to the Phase 1 cube box.

Read from NASA's US GHG Center raster API (titiler), which crops the cloud-optimised GeoTIFF
server side and returns a NumPy array (band 0 = data, band 1 = mask). ODIAC v2024 runs to
December 2023; study months Jan-May 2024 are not available.

Units per ODIAC documentation: tonnes of carbon per ~1 km cell per month (checked against EDGAR
box totals in the Phase 1 CO2 comparison). Role (proposal §5): plausibility comparison only.
Note that ODIAC distributes emissions with nighttime lights, so it is not independent of VIIRS.

Usage:
    python -m ecotrack.acquire.odiac
"""

import io
import urllib.request

import numpy as np
import pandas as pd

from ecotrack.config import DATA_INTERIM, load_config

API = "https://earth.gov/ghgcenter/api/raster/collections"
COLLECTION = "odiac-ffco2-monthgrid-v2024"
LAST_MONTH = "2023-12"
OUT = DATA_INTERIM / "odiac"


def fetch_month(yyyymm: str, box: dict):
    item = f"{COLLECTION}-odiac2024_1km_excl_intl_{yyyymm}"
    bbox = f"{box['lon_min']},{box['lat_min']},{box['lon_max']},{box['lat_max']}"
    url = f"{API}/{COLLECTION}/items/{item}/bbox/{bbox}.npy?assets=co2-emissions"
    with urllib.request.urlopen(url, timeout=120) as resp:
        arr = np.load(io.BytesIO(resp.read()))
    data, mask = arr[0].astype("float64"), arr[1]
    data[(mask == 0) | (data <= -9998)] = np.nan
    return data


def run():
    cfg = load_config()
    box = cfg["inversion"]["cube_box"]
    OUT.mkdir(parents=True, exist_ok=True)
    months = [m for m in pd.period_range(cfg["study"]["period"]["start"], LAST_MONTH, freq="M")
              if m.month in cfg["study"]["season_months"]]
    for m in months:
        out = OUT / f"{m.strftime('%Y%m')}.npz"
        if out.exists():
            continue
        data = fetch_month(m.strftime("%Y%m"), box)
        ny, nx = data.shape
        lat = np.linspace(box["lat_max"], box["lat_min"], ny, endpoint=False) - (box["lat_max"] - box["lat_min"]) / ny / 2
        lon = np.linspace(box["lon_min"], box["lon_max"], nx, endpoint=False) + (box["lon_max"] - box["lon_min"]) / nx / 2
        np.savez_compressed(out, t_c_per_cell=data, lat=lat, lon=lon)
        print(f"  {m}: box total {np.nansum(data):10,.0f} t C  (max cell {np.nanmax(data):,.0f})")


if __name__ == "__main__":
    run()
