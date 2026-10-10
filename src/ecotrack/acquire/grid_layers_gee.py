"""
Phase 2 — Earth Engine layers averaged onto the 1 km grid cells.

Monthly (study months), per cell:
  viirs_rad     VIIRS DNB monthly stray-light-corrected radiance (nW/cm²/sr); months with no
                cloud-free coverage (cf_cvg < min_cf_cvg) are masked
  hcho          TROPOMI tropospheric HCHO (mol/m²), QC'd like NO₂, monthly mean (D14)
  t2m_k         ERA5 2 m temperature at 07 UTC (~overpass), monthly mean (K)
  ssrd_j_m2     ERA5 surface solar radiation downwards accumulated over the 07 UTC hour (J/m²)
Seasonal (one composite per Oct–May season), per cell:
  ndvi, ndbi    Sentinel-2 SR median composite, SCL cloud/shadow masked
                NDVI = (B8 − B4)/(B8 + B4); NDBI = (B11 − B8)/(B11 + B8)

Outputs: data/interim/grid/layers_monthly.csv, layers_seasonal.csv (resumable per month/season).

Usage:
    python -m ecotrack.acquire.grid_layers_gee              # both
    python -m ecotrack.acquire.grid_layers_gee --only monthly
"""

import argparse
import json

import ee
import pandas as pd

from ecotrack.acquire.ee_utils import init_ee
from ecotrack.config import load_config
from ecotrack.feasibility.g2_tropomi_coverage import month_starts
from ecotrack.grid import GRID_DIR


CHUNK = 400  # cells per request: the regional grid (~2,900 cells, D22) is too large for one request at 20 m


def cells_fc(chunk=CHUNK):
    """The grid cells as a list of small FeatureCollections, each built from only its own cells.
    (One collection of all cells would upload every polygon, ~1.5 MB for the regional grid, in
    every request, even when the request uses only a slice of them.)"""
    feats = json.loads((GRID_DIR / "cells.geojson").read_text())["features"]
    return [ee.FeatureCollection([ee.Feature(ee.Geometry(f["geometry"]), f["properties"]) for f in feats[i:i + chunk]])
            for i in range(0, len(feats), chunk)]


def cells_bounds():
    """Bounding rectangle of the grid (client-side), for filterBounds."""
    xs, ys = [], []
    for f in json.loads((GRID_DIR / "cells.geojson").read_text())["features"]:
        for x, y in f["geometry"]["coordinates"][0]:
            xs.append(x); ys.append(y)
    return ee.Geometry.Rectangle([min(xs), min(ys), max(xs), max(ys)])


def reduce(img, chunks, scale, names):
    # A single-band image reduces to a property called "mean", not the band name: name outputs explicitly.
    reducer = ee.Reducer.mean().setOutputs(names) if len(names) == 1 else ee.Reducer.mean()
    rows = []
    for part in chunks:
        for f in img.reduceRegions(collection=part, reducer=reducer, scale=scale).getInfo()["features"]:
            p = f["properties"]
            rows.append({"cell_id": p["cell_id"], **{nm: p.get(nm) for nm in names}})
    return rows


def monthly_image(m_start, m_end, cfg):
    p2 = cfg["phase2"]
    v = p2["viirs"]
    viirs = ee.ImageCollection(v["collection"]).filterDate(m_start, m_end).first()
    viirs = ee.Image(ee.Algorithms.If(viirs, viirs, ee.Image.constant([0, 0]).rename([v["band"], "cf_cvg"]).selfMask()))
    viirs_b = viirs.select(v["band"]).updateMask(viirs.select("cf_cvg").gte(v["min_cf_cvg"])).rename("viirs_rad")

    h = p2["hcho"]
    hc = (ee.ImageCollection(h["collection"]).filterDate(m_start, m_end)
          .map(lambda i: i.select(h["band"]).updateMask(
              i.select("cloud_fraction").lte(h["cloud_fraction_max"]).And(i.select("solar_zenith_angle").lte(h["solar_zenith_max"]))))
          .mean().rename("hcho"))

    era = (ee.ImageCollection("ECMWF/ERA5/HOURLY").filterDate(m_start, m_end)
           .filter(ee.Filter.calendarRange(7, 7, "hour"))
           .select(["temperature_2m", "surface_solar_radiation_downwards"], ["t2m_k", "ssrd_j_m2"]).mean())
    return viirs_b, hc, era


def run_monthly(cfg, fc):
    out = GRID_DIR / "layers_monthly.csv"
    done = set(pd.read_csv(out).month) if out.exists() else set()
    for m_start, m_end in month_starts(cfg["study"]["period"]["start"], cfg["study"]["period"]["end"], cfg["study"]["season_months"]):
        month = m_start[:7]
        if month in done:
            continue
        viirs, hcho, era = monthly_image(m_start, m_end, cfg)
        df = pd.DataFrame(reduce(viirs, fc, 463.83, ["viirs_rad"]))
        df = df.merge(pd.DataFrame(reduce(hcho, fc, 1113.2, ["hcho"])), on="cell_id")
        # Sample ERA5 at 1 km: at its native 27.8 km scale most 1 km cells contain no pixel centre
        # and come back empty (7,560 of 10,720 rows in the first run). Each cell takes its ERA5 cell value.
        df = df.merge(pd.DataFrame(reduce(era, fc, 1000, ["t2m_k", "ssrd_j_m2"])), on="cell_id")
        df.insert(1, "month", month)
        df.to_csv(out, mode="a", header=not out.exists(), index=False)
        print(f"  {month}: viirs median {df.viirs_rad.median():.1f}, hcho median {df.hcho.median():.2e}, "
              f"t2m {df.t2m_k.median() - 273.15:.1f} °C  (missing viirs {df.viirs_rad.isna().sum()}, hcho {df.hcho.isna().sum()})")


def run_seasonal(cfg, fc):
    out = GRID_DIR / "layers_seasonal.csv"
    done = set(pd.read_csv(out).season) if out.exists() else set()
    s2 = cfg["phase2"]["sentinel2"]
    y0 = int(cfg["study"]["period"]["start"][:4])
    y1 = int(cfg["study"]["period"]["end"][:4])
    region = cells_bounds()
    for y in range(y0, y1):
        season = f"{y}-{str(y + 1)[2:]}"
        if season in done:
            continue

        def prep(img):
            scl = img.select("SCL")
            keep = ee.Image(0)
            for c in s2["keep_scl"]:
                keep = keep.Or(scl.eq(c))
            img = img.updateMask(keep)
            ndvi = img.normalizedDifference(["B8", "B4"]).rename("ndvi")
            ndbi = img.normalizedDifference(["B11", "B8"]).rename("ndbi")
            return ndvi.addBands(ndbi)

        coll = (ee.ImageCollection(s2["collection"]).filterBounds(region)
                .filterDate(f"{y}-10-01", f"{y + 1}-06-01")
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", s2["max_cloud_pct"])))
        n = coll.size().getInfo()
        comp = coll.map(prep).median()
        df = pd.DataFrame(reduce(comp, fc, 20, ["ndvi", "ndbi"]))
        df.insert(1, "season", season)
        df["n_scenes"] = n
        df.to_csv(out, mode="a", header=not out.exists(), index=False)
        print(f"  {season}: {n} scenes; ndvi median {df.ndvi.median():.3f}, ndbi median {df.ndbi.median():.3f}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--only", choices=["monthly", "seasonal"])
    a = p.parse_args()
    init_ee()
    cfg = load_config()
    fc = cells_fc()
    if a.only in (None, "monthly"):
        run_monthly(cfg, fc)
    if a.only in (None, "seasonal"):
        run_seasonal(cfg, fc)
