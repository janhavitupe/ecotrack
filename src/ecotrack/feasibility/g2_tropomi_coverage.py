"""
G2 — TROPOMI NO2 coverage: how many usable overpasses per month over the corridor?

An overpass counts as usable if at least `min_valid_fraction` of corridor pixels survive QC.
This decides whether Phase 4 can use monthly composites or must fall back to seasonal ones.

Usage:
    python -m ecotrack.feasibility.g2_tropomi_coverage --project <gcp-id>
    python -m ecotrack.feasibility.g2_tropomi_coverage --project <gcp-id> --start 2020-01-01 --end 2020-03-01
"""

import argparse
import json

import ee
import pandas as pd

from ecotrack.acquire.ee_utils import ee_corridor, init_ee, tropomi_qc
from ecotrack.config import OUTPUTS, load_config


def month_starts(start: str, end: str, season_months: list[int]):
    for m in pd.date_range(start, end, freq="MS"):
        if m >= pd.Timestamp(end):  # end date is exclusive
            break
        if m.month in season_months:
            yield m.strftime("%Y-%m-%d"), (m + pd.offsets.MonthBegin(1)).strftime("%Y-%m-%d")


def month_stats(m_start: str, m_end: str, corridor, n_total, cfg) -> list[dict]:
    t = cfg["tropomi"]
    coll = ee.ImageCollection(t["collection"]).filterBounds(corridor).filterDate(m_start, m_end)
    if coll.size().getInfo() == 0:
        return []
    coll, _ = tropomi_qc(coll, cfg)

    def per_image(img):
        stats = img.select(t["band"]).reduceRegion(
            reducer=ee.Reducer.count().combine(ee.Reducer.mean(), sharedInputs=True),
            geometry=corridor,
            scale=t["scale_m"],
            maxPixels=1e9,
        )
        return ee.Feature(None, {
            "time": img.date().format("YYYY-MM-dd'T'HH:mm"),
            "n_valid": stats.get(f"{t['band']}_count"),
            "mean_no2": stats.get(f"{t['band']}_mean"),
        })

    feats = ee.FeatureCollection(coll.map(per_image)).getInfo()["features"]
    rows = [f["properties"] for f in feats]
    for r in rows:
        r["valid_fraction"] = (r.get("n_valid") or 0) / n_total
    return rows


def run(start: str, end: str):
    cfg = load_config()
    corridor = ee_corridor()
    n_total = ee.Image.constant(1).reduceRegion(
        ee.Reducer.count(), corridor, cfg["tropomi"]["scale_m"]
    ).get("constant").getInfo()
    print(f"Corridor = {n_total} TROPOMI L3 pixels")

    rows = []
    for m_start, m_end in month_starts(start, end, cfg["study"]["season_months"]):
        month_rows = month_stats(m_start, m_end, corridor, n_total, cfg)
        # GEE's L3 footprints are loose, so filterBounds returns many orbits that never cover the
        # corridor. Count distinct days instead of images: TROPOMI overpasses Pune about once a day.
        usable_days = {r["time"][:10] for r in month_rows if r["valid_fraction"] >= cfg["tropomi"]["min_valid_fraction"]}
        print(f"  {m_start[:7]}: {len(month_rows):3d} images searched, {len(usable_days):2d} usable days")
        rows += month_rows

    out_dir = OUTPUTS / "feasibility"
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "g2_tropomi_overpasses.csv", index=False)

    df["month"] = df.time.str[:7]
    df["date"] = df.time.str[:10]
    usable = df[df.valid_fraction >= cfg["tropomi"]["min_valid_fraction"]]
    monthly = pd.DataFrame({
        "days_with_any_valid_pixel": df[df.n_valid.fillna(0) > 0].groupby("month").date.nunique(),
        "usable_days": usable.groupby("month").date.nunique(),
    }).reindex(sorted(df.month.unique())).fillna(0).astype(int)
    monthly.to_csv(out_dir / "g2_tropomi_monthly.csv")
    summary = {
        "corridor_pixels": n_total,
        "months": int(len(monthly)),
        "median_usable_days_per_month": float(monthly.usable_days.median()),
        "min_usable_days_per_month": int(monthly.usable_days.min()),
        "months_below_5_usable_days": monthly.index[monthly.usable_days < 5].tolist(),
    }
    (out_dir / "g2_tropomi_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print(
        "Read-out guide: >= ~8 usable days in most months -> monthly composites are OK;"
        " otherwise composite by season (Oct-Jan / Feb-May) and say so in Methods."
    )


if __name__ == "__main__":
    cfg = load_config()
    p = argparse.ArgumentParser()
    p.add_argument("--project", help="GCP project id registered for Earth Engine")
    p.add_argument("--start", default=cfg["study"]["period"]["start"])
    p.add_argument("--end", default=cfg["study"]["period"]["end"])
    args = p.parse_args()
    init_ee(args.project)
    run(args.start, args.end)
