"""
G1 — OCO-3 / OCO-2 feasibility: how many good-quality XCO2 soundings fall on the corridor?

Why not just count granules: Lite files are one file per day covering the whole globe, so a
bounding-box granule search returns almost every day and says nothing about coverage. We
have to open each file and count the soundings that actually fall in the box.

Only the small per-sounding arrays are streamed (not whole files). Results are appended as
we go, so an interrupted run resumes where it stopped.

Usage (Earthdata login via ~/.netrc, env vars, or an interactive prompt):
    python -m ecotrack.feasibility.g1_oco_soundings --product oco3 --start 2019-10-01 --end 2020-05-31
    python -m ecotrack.feasibility.g1_oco_soundings --product oco3           # full study period
    python -m ecotrack.feasibility.g1_oco_soundings --product oco3 --summarize-only
"""

import argparse
import json
import re
import warnings
from datetime import datetime

import earthaccess
import h5py
import numpy as np
import pandas as pd
from shapely import contains_xy

from ecotrack.config import DATA_INTERIM, OUTPUTS, load_config
from ecotrack.geometry import bbox, cluster_zones, corridor_polygon

# earthaccess 0.17 warns about its own internal use of DataGranule.size() on every file.
warnings.filterwarnings("ignore", category=FutureWarning, module="earthaccess")

FIELDS = ["sounding_id", "time", "latitude", "longitude", "xco2", "xco2_uncertainty", "xco2_quality_flag"]


def _version_key(v: str) -> float:
    m = re.match(r"[\d.]+", v or "")
    return float(m.group().rstrip(".")) if m else -1.0


def search_granules(short_name, version, start, end, box, pad, season_months):
    results = earthaccess.search_data(
        short_name=short_name,
        version=version,
        temporal=(start, end),
        bounding_box=(box["lon_min"] - pad, box["lat_min"] - pad, box["lon_max"] + pad, box["lat_max"] + pad),
    )
    # Several processing versions can coexist, and the newest often covers only recent years
    # (e.g. OCO-2 11.3r from 2024, 11.2r before). Keep the newest version available per day.
    by_day = {}
    for g in results:
        v = g["umm"]["CollectionReference"].get("Version")
        if version and v != version:
            continue
        day = g["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"][:10]
        if int(day[5:7]) not in season_months:
            continue
        if day not in by_day or _version_key(v) > _version_key(by_day[day][0]):
            by_day[day] = (v, g)
    kept = sorted((day, v, g) for day, (v, g) in by_day.items())
    used = pd.Series([v for _, v, _ in kept]).value_counts().to_dict()
    print(f"{short_name}: in-season days per version used {used}; {len(kept)} days total")
    return kept


def read_box(fobj, box, pad) -> pd.DataFrame:
    with h5py.File(fobj, "r") as h5:
        lat = h5["latitude"][:]
        lon = h5["longitude"][:]
        sel = (
            (lat >= box["lat_min"] - pad) & (lat <= box["lat_max"] + pad)
            & (lon >= box["lon_min"] - pad) & (lon <= box["lon_max"] + pad)
        )
        if not sel.any():
            return pd.DataFrame(columns=FIELDS + ["operation_mode"])
        # Read only the contiguous span containing the hits, then mask inside it.
        idx = np.flatnonzero(sel)
        lo, hi = idx.min(), idx.max() + 1
        mask = sel[lo:hi]
        df = pd.DataFrame({f: h5[f][lo:hi][mask] for f in FIELDS})
        # OCO-3 modes (check the dataset's attributes): 0 nadir, 1 glint, 2 target, 3 transition, 4 SAM
        mode = "Sounding/operation_mode"
        df["operation_mode"] = h5[mode][lo:hi][mask] if mode in h5 else -1
    return df


def scan(product: str, start: str, end: str):
    cfg = load_config()
    o = cfg["oco"]
    prod = o["products"][product]
    box, pad = bbox(), o["search_pad_deg"]
    out_dir = DATA_INTERIM / "oco"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows_csv = out_dir / f"{product}_soundings.csv"
    done_txt = out_dir / f"{product}_scanned.txt"
    done = set(done_txt.read_text().split()) if done_txt.exists() else set()

    earthaccess.login()
    granules = search_granules(
        prod["short_name"], prod["version"], start, end, box, pad, cfg["study"]["season_months"]
    )
    todo = [(d, v, g) for d, v, g in granules if g["meta"]["native-id"] not in done]
    print(f"{len(todo)} granules left to scan ({len(granules) - len(todo)} already done)")

    consecutive_denied = 0
    for i, (day, version, g) in enumerate(todo, 1):
        gid = g["meta"]["native-id"]
        try:
            (fobj,) = earthaccess.open([g])
            df = read_box(fobj, box, pad)
        except Exception as exc:  # network hiccups: skip now, retried on the next run
            print(f"  [{i}/{len(todo)}] {day} FAILED ({exc.__class__.__name__}: {exc}) — will retry next run")
            consecutive_denied = consecutive_denied + 1 if re.search(r"\b40[13]\b", str(exc)) else 0
            if consecutive_denied >= 3:
                raise SystemExit(
                    "\nAccess denied 3 times in a row: this is an account problem, not the network.\n"
                    "At https://urs.earthdata.nasa.gov (logged in as the same user as your _netrc):\n"
                    "  1. Applications > Authorized Apps must list 'NASA GESDISC DATA ARCHIVE'\n"
                    "     (if it is listed, revoke it and approve it again, accepting the EULA);\n"
                    "  2. your e-mail address must be verified and your profile complete.\n"
                    "Then re-run this command; it resumes where it stopped."
                )
            continue
        consecutive_denied = 0
        if len(df):
            df.insert(0, "granule", gid)
            df.insert(1, "version", version)
            df.to_csv(rows_csv, mode="a", header=not rows_csv.exists(), index=False)
        with open(done_txt, "a") as f:
            f.write(gid + "\n")
        print(f"  [{i}/{len(todo)}] {day}: {len(df)} soundings near corridor")

    summarize(product)


def summarize(product: str):
    cfg = load_config()
    o = cfg["oco"]
    rows_csv = DATA_INTERIM / "oco" / f"{product}_soundings.csv"
    done_txt = DATA_INTERIM / "oco" / f"{product}_scanned.txt"
    n_scanned = len(set(done_txt.read_text().split())) if done_txt.exists() else 0
    if not rows_csv.exists():
        print(f"No {product} soundings near the corridor in {n_scanned} scanned days.")
        return

    df = pd.read_csv(rows_csv).drop_duplicates("sounding_id")
    df["date"] = pd.to_datetime(df["time"], unit="s").dt.date
    box = bbox()
    df["in_bbox"] = df.latitude.between(box["lat_min"], box["lat_max"]) & df.longitude.between(box["lon_min"], box["lon_max"])
    df["in_corridor"] = contains_xy(corridor_polygon(), df.longitude.values, df.latitude.values)
    for name, poly in cluster_zones().items():
        df[f"in_{name}"] = contains_xy(poly, df.longitude.values, df.latitude.values)
    good = df[df.xco2_quality_flag == o["good_quality_flag"]]

    per_day = good[good.in_corridor].groupby("date").size()
    usable = per_day[per_day >= o["min_good_soundings_per_day"]]
    # City-scale view: SAMs often centre just off the 7 km-wide corridor, so also count the bbox.
    per_day_bbox = good[good.in_bbox].groupby("date").agg(
        n=("sounding_id", "size"), sam_share=("operation_mode", lambda s: round(float((s == 4).mean()), 2))
    )
    month = pd.to_datetime(good.date)
    summary = {
        "product": product,
        "generated": datetime.now().isoformat(timespec="seconds"),
        "days_scanned": n_scanned,
        "soundings_near_corridor_all_quality": int(len(df)),
        "good_soundings_in_bbox": int(good.in_bbox.sum()),
        "good_soundings_in_corridor": int(good.in_corridor.sum()),
        "good_soundings_per_cluster": {n: int(good[f"in_{n}"].sum()) for n in cluster_zones()},
        "days_with_any_good_corridor_sounding": int(len(per_day)),
        f"usable_days_(>={o['min_good_soundings_per_day']}_good_in_corridor)": int(len(usable)),
        "usable_dates": [str(d) for d in usable.index],
        "bbox_days_with_>=50_good": {
            str(d): {"n": int(r.n), "sam_share": r.sam_share}
            for d, r in per_day_bbox[per_day_bbox.n >= 50].iterrows()
        },
        "good_corridor_soundings_by_operation_mode": {
            str(k): int(v) for k, v in good[good.in_corridor].operation_mode.value_counts().items()
        },
        "good_corridor_soundings_by_season_month": {
            str(k): int(v) for k, v in good[good.in_corridor].groupby(month[good.in_corridor].dt.strftime("%Y-%m")).size().items()
        },
    }
    out = OUTPUTS / "feasibility" / f"g1_{product}_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k != "usable_dates"}, indent=2))
    print(f"\nSaved {out}")
    print(
        "Read-out guide (a judgement call, record it in docs/decisions.md):\n"
        "  >= ~15 usable days  -> OCO-3 can serve as an independent validation target (label L2)\n"
        "  ~5-15 usable days   -> case-study / constraint on cluster totals only\n"
        "  < ~5 usable days    -> qualitative only; Experiment B reframed, try OCO-2 as well"
    )


if __name__ == "__main__":
    cfg = load_config()
    p = argparse.ArgumentParser()
    p.add_argument("--product", choices=list(cfg["oco"]["products"]), default="oco3")
    p.add_argument("--start", default=cfg["study"]["period"]["start"])
    p.add_argument("--end", default=cfg["study"]["period"]["end"])
    p.add_argument("--summarize-only", action="store_true")
    args = p.parse_args()
    if args.summarize_only:
        summarize(args.product)
    else:
        scan(args.product, args.start, args.end)
