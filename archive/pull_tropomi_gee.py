"""
EcoTrack — Phase 1, Step 1: first TROPOMI NO2 pull for the corridor.

This is deliberately the FIRST script you should run. It answers one question:
"Does the pipeline work end-to-end on a small slice of real data?"
Do not try to pull the full study period on the first run. Test on ~1 week first.

SETUP (one-time):
    pip install earthengine-api geemap geopandas
    earthengine authenticate      # opens a browser login, one time only

USAGE:
    python pull_tropomi_gee.py --start 2025-01-01 --end 2025-01-08 --test
"""

import argparse
import json
import os

import ee

from corridor_geometry import BBOX, WAYPOINTS


def init_ee(project_id: str = None):
    """
    Initialize Earth Engine. If you have a GCP project registered for EE,
    pass its id; otherwise ee.Initialize() alone works for most personal accounts.
    """
    try:
        if project_id:
            ee.Initialize(project=project_id)
        else:
            ee.Initialize()
    except Exception:
        print("Not authenticated yet — running ee.Authenticate() now.")
        ee.Authenticate()
        ee.Initialize(project=project_id) if project_id else ee.Initialize()


def get_corridor_geometry():
    """Use the simple bounding box for the first test pull (fast, no extra deps)."""
    return ee.Geometry.Rectangle(
        [BBOX["lon_min"], BBOX["lat_min"], BBOX["lon_max"], BBOX["lat_max"]]
    )


def pull_tropomi_no2(start_date: str, end_date: str, geometry, out_dir: str = "./data/raw/tropomi"):
    """
    Pull TROPOMI tropospheric NO2 column density for the corridor and date range.
    Applies the Phase 1 QC rules from the project plan:
        - cloud fraction <= 0.3
        - qa_value >= 0.7
    (solar zenith and IQR filtering are done later, at the per-pixel/observation
    stage once you move from the OFFL L3 mosaic to raw L2 swaths, if you need
    per-observation-level QC rather than the pre-gridded L3 product.)
    """
    os.makedirs(out_dir, exist_ok=True)

    collection = (
        ee.ImageCollection("COPERNICUS/S5P/OFFL/L3_NO2")
        .filterBounds(geometry)
        .filterDate(start_date, end_date)
    )

    n_images = collection.size().getInfo()
    print(f"Found {n_images} TROPOMI NO2 images between {start_date} and {end_date}")

    if n_images == 0:
        print("No images found. Check date range and geometry before proceeding.")
        return

    no2 = collection.select("tropospheric_NO2_column_number_density")
    qa = collection.select("qa_value")
    cloud = collection.select("cloud_fraction")

    # Composite mean over the window, masked by QC thresholds per-pixel
    def qc_mask(img):
        img_qa = img.select("qa_value")
        img_cloud = img.select("cloud_fraction")
        mask = img_qa.gte(0.7).And(img_cloud.lte(0.3))
        return img.updateMask(mask)

    no2_composite = (
        collection.map(qc_mask)
        .select("tropospheric_NO2_column_number_density")
        .mean()
        .clip(geometry)
    )

    # Export as GeoTIFF to Google Drive (simplest path for a first test).
    # Switch to Export.image.toCloudStorage or getDownloadURL for smaller test areas
    # if you don't want to touch Drive.
    task = ee.batch.Export.image.toDrive(
        image=no2_composite,
        description=f"tropomi_no2_{start_date}_{end_date}",
        folder="ecotrack_tropomi",
        region=geometry,
        scale=1000,          # ~1km, matches your eventual modeling grid
        crs="EPSG:4326",
        maxPixels=1e9,
    )
    task.start()
    print(
        f"Export task started: tropomi_no2_{start_date}_{end_date}\n"
        f"Check status at https://code.earthengine.google.com/tasks\n"
        f"Output will land in Google Drive folder 'ecotrack_tropomi'."
    )

    # Also log a small non-spatial summary immediately so you have something
    # to inspect without waiting for the export to finish.
    mean_no2 = no2_composite.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=geometry, scale=1000, maxPixels=1e9
    ).getInfo()
    log_entry = {
        "start_date": start_date,
        "end_date": end_date,
        "n_source_images": n_images,
        "mean_no2_mol_per_m2": mean_no2,
        "bbox": BBOX,
    }
    log_path = os.path.join(out_dir, f"pull_log_{start_date}_{end_date}.json")
    with open(log_path, "w") as f:
        json.dump(log_entry, f, indent=2)
    print(f"Saved pull summary to {log_path}")
    print(f"Mean NO2 over corridor bbox: {mean_no2}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    parser.add_argument("--project", default=None, help="GCP project id for Earth Engine, if you have one")
    parser.add_argument("--test", action="store_true", help="Flag for a short test pull (no behavior change yet, just a reminder)")
    args = parser.parse_args()

    init_ee(args.project)
    geom = get_corridor_geometry()
    pull_tropomi_no2(args.start, args.end, geom)
