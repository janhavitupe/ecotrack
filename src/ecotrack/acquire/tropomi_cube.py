"""
Phase 1 input: per-overpass TROPOMI NO2 arrays over a ~100 km box around Pune (the "cube").

Only overpasses that pass G2's usability test (QC'd valid fraction over the corridor >=
min_valid_fraction) are kept. Each is reprojected onto one fixed 0.01 degree grid, so every
day lines up pixel-for-pixel. Saved one file per month (data/interim/tropomi/cube/YYYY-MM.npz),
so an interrupted run resumes where it stopped.

Usage:
    python -m ecotrack.acquire.tropomi_cube
    python -m ecotrack.acquire.tropomi_cube --start 2020-01-01 --end 2020-02-01   # test month
"""

import argparse
import glob

import ee
import numpy as np
import pandas as pd

from ecotrack.acquire.ee_utils import ee_corridor, init_ee, tropomi_qc
from ecotrack.config import DATA_INTERIM, load_config
from ecotrack.feasibility.g2_tropomi_coverage import month_starts

CUBE_DIR = DATA_INTERIM / "tropomi" / "cube"
FILL = -9999.0
BATCH = 8  # images per getInfo call (~9k pixels each)


def grid(cfg):
    inv = cfg["inversion"]
    b, res = inv["cube_box"], inv["cube_res_deg"]
    lon = np.round(np.arange(b["lon_min"] + res / 2, b["lon_max"], res), 5)
    lat = np.round(np.arange(b["lat_max"] - res / 2, b["lat_min"], -res), 5)  # north -> south, like the array rows
    transform = [res, 0, b["lon_min"], 0, -res, b["lat_max"]]
    # Box edges sit on pixel boundaries; pull them in by a quarter pixel so sampleRectangle
    # doesn't include the neighbouring row/column.
    q = res / 4
    rect = ee.Geometry.Rectangle([b["lon_min"] + q, b["lat_min"] + q, b["lon_max"] - q, b["lat_max"] - q], None, False)
    return lat, lon, transform, rect


def month_images(m_start, m_end, cfg, corridor, n_total):
    """QC'd images in the month whose corridor valid fraction passes G2's threshold."""
    t = cfg["tropomi"]
    coll = ee.ImageCollection(t["collection"]).filterBounds(corridor).filterDate(m_start, m_end)
    if coll.size().getInfo() == 0:
        return ee.ImageCollection([]), 0
    coll, _ = tropomi_qc(coll, cfg)

    def with_fraction(img):
        n = img.select(t["band"]).reduceRegion(ee.Reducer.count(), corridor, t["scale_m"], maxPixels=1e9).get(t["band"])
        return img.set("valid_fraction", ee.Number(n).divide(n_total))

    coll = coll.map(with_fraction).filter(ee.Filter.gte("valid_fraction", t["min_valid_fraction"]))
    return coll, coll.size().getInfo()


def fetch(coll, n, cfg):
    band = cfg["tropomi"]["band"]
    lat, lon, transform, rect = grid(cfg)
    imgs = coll.toList(n)
    arrays, times, fracs = [], [], []
    for i in range(0, n, BATCH):
        batch = ee.List(imgs.slice(i, min(i + BATCH, n)))

        def sample(img):
            img = ee.Image(img)
            arr = (img.select(band).unmask(FILL)
                   .reproject(crs="EPSG:4326", crsTransform=transform)
                   .sampleRectangle(region=rect, defaultValue=FILL))
            return ee.Feature(None, {"no2": arr.get(band), "time": img.date().millis(),
                                     "valid_fraction": img.get("valid_fraction")})

        for f in ee.FeatureCollection(batch.map(sample)).getInfo()["features"]:
            p = f["properties"]
            a = np.array(p["no2"], dtype="float32")
            a[a <= FILL + 1] = np.nan
            if a.shape != (len(lat), len(lon)):
                raise ValueError(f"unexpected array shape {a.shape}, expected {(len(lat), len(lon))}")
            arrays.append(a)
            times.append(p["time"])
            fracs.append(p["valid_fraction"])
    order = np.argsort(times)
    return (np.stack(arrays)[order], np.array(times, dtype="int64")[order], np.array(fracs)[order])


def run(start: str, end: str):
    cfg = load_config()
    corridor = ee_corridor()
    n_total = ee.Image.constant(1).reduceRegion(ee.Reducer.count(), corridor, cfg["tropomi"]["scale_m"]).get("constant")
    lat, lon, _, _ = grid(cfg)
    CUBE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Cube grid: {len(lat)} x {len(lon)} pixels")

    for m_start, m_end in month_starts(start, end, cfg["study"]["season_months"]):
        out = CUBE_DIR / f"{m_start[:7]}.npz"
        if out.exists():
            continue
        coll, n = month_images(m_start, m_end, cfg, corridor, n_total)
        if n == 0:
            np.savez_compressed(out, no2=np.empty((0, len(lat), len(lon)), "float32"),
                                time_ms=np.empty(0, "int64"), valid_fraction=np.empty(0), lat=lat, lon=lon)
            print(f"  {m_start[:7]}: 0 usable overpasses")
            continue
        no2, t, frac = fetch(coll, n, cfg)
        np.savez_compressed(out, no2=no2, time_ms=t, valid_fraction=frac, lat=lat, lon=lon)
        print(f"  {m_start[:7]}: {n} overpasses saved")


def load_cube():
    """Concatenate all monthly files -> (no2[t, y, x] mol/m2, times (UTC), lat, lon, valid_fraction)."""
    files = sorted(glob.glob(str(CUBE_DIR / "*.npz")))
    if not files:
        raise FileNotFoundError("No cube files; run python -m ecotrack.acquire.tropomi_cube first")
    parts = [np.load(f) for f in files]
    no2 = np.concatenate([p["no2"] for p in parts])
    times = pd.to_datetime(np.concatenate([p["time_ms"] for p in parts]), unit="ms")
    frac = np.concatenate([p["valid_fraction"] for p in parts])
    return no2, times, parts[0]["lat"], parts[0]["lon"], frac


if __name__ == "__main__":
    cfg = load_config()
    p = argparse.ArgumentParser()
    p.add_argument("--start", default=cfg["study"]["period"]["start"])
    p.add_argument("--end", default=cfg["study"]["period"]["end"])
    args = p.parse_args()
    init_ee()
    run(args.start, args.end)
