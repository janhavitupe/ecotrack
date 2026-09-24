"""
Export a QC'd TROPOMI NO2 mean composite over the corridor to Google Drive.

Run a one-week test before any long pull:
    python -m ecotrack.acquire.tropomi_gee --start 2020-01-01 --end 2020-01-08 --project <gcp-id>
"""

import argparse
import json

import ee

from ecotrack.acquire.ee_utils import ee_bbox, ee_corridor, init_ee, tropomi_qc
from ecotrack.config import DATA_RAW, load_config


def export_composite(start: str, end: str):
    cfg = load_config()
    t = cfg["tropomi"]
    region = ee_bbox()
    coll = ee.ImageCollection(t["collection"]).filterBounds(region).filterDate(start, end)
    n_images = coll.size().getInfo()
    print(f"Found {n_images} TROPOMI NO2 images between {start} and {end}")
    if n_images == 0:
        print("No images found. Check the date range and geometry.")
        return

    coll, has_qa = tropomi_qc(coll, cfg)
    composite = coll.select(t["band"]).mean().clip(region)

    name = f"tropomi_no2_{start}_{end}"
    task = ee.batch.Export.image.toDrive(
        image=composite,
        description=name,
        folder="ecotrack_tropomi",
        region=region,
        scale=t["scale_m"],
        crs="EPSG:4326",
        maxPixels=1e9,
    )
    task.start()
    print(f"Export task started: {name} (https://code.earthengine.google.com/tasks)")

    mean_no2 = composite.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=ee_corridor(), scale=t["scale_m"], maxPixels=1e9
    ).getInfo()
    out_dir = DATA_RAW / "tropomi"
    out_dir.mkdir(parents=True, exist_ok=True)
    log = {
        "start": start,
        "end": end,
        "n_source_images": n_images,
        "qa_band_present": has_qa,
        "corridor_mean_no2_mol_m2": mean_no2,
    }
    (out_dir / f"pull_log_{start}_{end}.json").write_text(json.dumps(log, indent=2))
    print(f"Corridor mean NO2: {mean_no2}  (polluted urban is roughly 1e-5 to 1e-4 mol/m^2)")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--start", required=True, help="YYYY-MM-DD")
    p.add_argument("--end", required=True, help="YYYY-MM-DD (exclusive)")
    p.add_argument("--project", help="GCP project id registered for Earth Engine")
    args = p.parse_args()
    init_ee(args.project)
    export_composite(args.start, args.end)
