"""
G3 — Is there an NO2 enhancement over the corridor clusters that stands clearly above background?

For each season (Oct-May) we build a QC'd mean composite and compare each cluster's mean
tropospheric NO2 with a regional background (a low percentile over a wide rural box). If the
clusters can't be told apart from background, the cluster-scale inversion is not viable and
the inversion falls back to one whole-city source.

Also exports one seasonal composite map to Drive for visual inspection.

Usage:
    python -m ecotrack.feasibility.g3_no2_signal --project <gcp-id>
"""

import argparse
import json

import ee

from ecotrack.acquire.ee_utils import ee_bbox, ee_clusters, init_ee, tropomi_qc
from ecotrack.config import OUTPUTS, load_config

BACKGROUND_PERCENTILE = 10


def seasons(cfg):
    y0 = int(cfg["study"]["period"]["start"][:4])
    y1 = int(cfg["study"]["period"]["end"][:4])
    return [(f"{y}-10-01", f"{y + 1}-06-01") for y in range(y0, y1)]


def run(export_year: int | None):
    cfg = load_config()
    t = cfg["tropomi"]
    region = ee_bbox(cfg["region"]["regional_bbox"])
    clusters = ee_clusters()
    results = {}

    for start, end in seasons(cfg):
        coll = ee.ImageCollection(t["collection"]).filterBounds(region).filterDate(start, end)
        coll, _ = tropomi_qc(coll, cfg)
        comp = coll.select(t["band"]).mean()

        bg = comp.reduceRegion(
            ee.Reducer.percentile([BACKGROUND_PERCENTILE]), region, t["scale_m"], maxPixels=1e9
        ).getInfo()
        background = list(bg.values())[0]
        season = f"{start[:4]}-{end[2:4]}"
        results[season] = {"background_p10": background, "clusters": {}}
        for name, geom in clusters.items():
            stats = comp.reduceRegion(
                ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True), geom, t["scale_m"]
            ).getInfo()
            mean = stats.get(f"{t['band']}_mean")
            results[season]["clusters"][name] = {
                "mean": mean,
                "std": stats.get(f"{t['band']}_stdDev"),
                "enhancement_ratio": (mean / background) if mean and background else None,
            }
        ratios = {k: round(v["enhancement_ratio"] or 0, 2) for k, v in results[season]["clusters"].items()}
        print(f"  {season}: background {background:.2e} mol/m2, enhancement ratios {ratios}")

        if export_year and start.startswith(str(export_year)):
            ee.batch.Export.image.toDrive(
                image=comp.clip(region), description=f"g3_no2_season_{season}",
                folder="ecotrack_feasibility", region=region, scale=t["scale_m"], crs="EPSG:4326",
            ).start()
            print(f"  Exported composite map for {season} to Drive/ecotrack_feasibility")

    out = OUTPUTS / "feasibility" / "g3_no2_signal.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    print(f"Saved {out}")
    print(
        "Read-out guide: ratios consistently >= ~1.5 per cluster -> cluster-scale inversion is worth"
        " attempting; ~1.0-1.3 -> treat Pune+PCMC as one source. Inspect the exported map as well:"
        " the enhancement should sit on PCMC, not only on central Pune."
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--project", help="GCP project id registered for Earth Engine")
    p.add_argument("--export-year", type=int, default=2021, help="season start year to export as a map (0 = none)")
    args = p.parse_args()
    init_ee(args.project)
    run(args.export_year or None)
