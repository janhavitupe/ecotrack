"""
From "midday October–May rate" to an annual-mean emission (Phase 1 limitation; findings §4.11).

TROPOMI sees Pune only at ~11:30–13:30 IST and we use October–May only. Emissions vary by hour,
weekday and month, so  E_annual = E_observed / F,  with
    F = Σ_s w_s · f_hour,s · f_week,s · f_month,s
  w_s       NOx share of sector s within 25 km of the source (EDGAR 2021, as in run_co2)
  f_hour,s  emission in the actual overpass hours ÷ the daily mean (EDGAR hourly profiles, India,
            per month and day type, weighted by our real overpass-time distribution)
  f_week,s  weekday mix of our overpass days ÷ the weekly mean (≈ 1: TROPOMI samples all weekdays)
  f_month,s the study months (Oct–May, weighted by our overpass count per month) ÷ the annual mean
Profiles: EDGAR temporal profiles (Crippa et al. 2020, Sci. Data 7, 121): `EDGAR_temporal_profiles_r1.xlsx`
(monthly, country/sector/year) and auxiliary tables (hourly per month and day type; weekly).

Caveat (recorded): EDGAR's monthly residential profile for India is heating-shaped (Jan ≈ 17.5%,
Jul ≈ 2.9% of the year); Pune's household fuel use is mostly cooking. A sensitivity run with a
flat residential month profile is included.

Output: outputs/phase1/temporal_adjust.json

Usage:
    python -m ecotrack.inversion.temporal_adjust
"""

import json

import numpy as np
import openpyxl
import pandas as pd

from ecotrack.config import DATA_INTERIM, ROOT
from ecotrack.acquire.tropomi_cube import load_cube
from ecotrack.inversion.run_city import OUT

RAW = ROOT / "data" / "raw" / "edgar"
COUNTRY = "IND"
# Our EDGAR emission sector codes -> the profile tables' activity codes
PROFILE_CODE = {"IND": "IND", "TRO": "TRO", "RCO": "RCO", "ENE": "ENE", "REF_TRF": "REF", "TNR_Other": "TNR",
                "TNR_Aviation_LTO": "TNR", "AGS": "AGS", "AWB": "AWB", "CHE": "CHE", "NMM": "NMM", "NFE": "NFE"}
# Monthly profiles are matched on IPCC 1996 codes (prefix match). India has country-specific monthly rows
# only for residential (1A4) and fires; everything else uses EDGAR world region 7 (India's region).
# (A first version matched on sector *names* and silently fell back to flat for most sectors, and matched
# agricultural soils to "rice cultivation" (4C) — fixed 2026-10-01.)
MONTHLY_IPCC = {"IND": ["1A2"], "TRO": ["1A3b"], "RCO": ["1A4"], "ENE": ["1A1a"], "REF": ["1A1b"],
                "TNR": ["1A3c", "1A3a2"], "AGS": ["4D"], "AWB": ["4F"], "CHE": ["2B"], "NMM": ["2A"], "NFE": ["2C"]}


def overpass_hour_weights():
    """Fraction of usable overpasses in each local (IST) clock hour 0..23, and per study month."""
    _, times, *_ = load_cube(apply_qc=False)
    ist = pd.DatetimeIndex(times) + pd.Timedelta("5h30min")
    hours = np.bincount(ist.hour, minlength=24) / len(ist)
    months = pd.Series(ist.month).value_counts(normalize=True).sort_index()
    weekdays = np.bincount(ist.dayofweek, minlength=7) / len(ist)  # 0 = Monday
    return hours, months, weekdays


def load_profiles():
    hp = pd.read_csv(RAW / "edgar_aux_tables" / "hourly_profiles.csv")
    hp = hp[hp.Country_code_A3 == COUNTRY]
    wk = pd.read_csv(RAW / "edgar_aux_tables" / "weekly_profiles.csv")
    wk = wk[wk.Country_code_A3 == COUNTRY]
    wd = pd.read_csv(RAW / "edgar_aux_tables" / "weekdays.csv", sep=";")
    we = pd.read_csv(RAW / "edgar_aux_tables" / "weekenddays.csv", sep=";")
    wtype = int(we[we.Country_code_A3 == COUNTRY].Weekend_type_id.iloc[0]) if COUNTRY in set(we.Country_code_A3) else 0
    daytype = wd[wd.Weekend_type_id == wtype].set_index("Weekday_id").Daytype_id.to_dict()  # 1..7 -> daytype
    wb = openpyxl.load_workbook(RAW / "EDGAR_temporal_profiles_r1.xlsx", read_only=True)
    region = [r for r in wb["countries and regions"].iter_rows(values_only=True) if r[0] == COUNTRY][0][2]
    rows = [r for r in wb["monthly temporal profiles"].iter_rows(values_only=True) if r[0] in (COUNTRY, region)]
    return hp, wk, daytype, (rows, region)


def monthly_profile(rows_region, code):
    """12 monthly fractions for the sector: the country's own rows if present, else the region's.
    Several sub-activities with the same IPCC prefix are averaged (latest year of each)."""
    rows, region = rows_region
    prefixes = MONTHLY_IPCC.get(code, [])
    for owner in (COUNTRY, region):
        latest = {}
        for r in rows:
            if r[0] == owner and r[2] and any(str(r[2]).startswith(px) for px in prefixes):
                if r[1] not in latest or (r[4] or 0) > (latest[r[1]][4] or 0):
                    latest[r[1]] = r
        if latest:
            prof = np.mean([np.array(r[5:17], dtype=float) / sum(r[5:17]) for r in latest.values()], axis=0)
            label = f"{'India' if owner == COUNTRY else f'region {region}'}: {len(latest)} activities {sorted({str(r[2]) for r in latest.values()})}"
            return prof, label, max(r[4] or 0 for r in latest.values())
    return None


def factors(code, hp, wk, daytype, rows, hours_w, months_w, weekdays_w, flat_month=False):
    h = hp[hp.activity_code == code]
    if h.empty:
        return None
    hour_cols = [f"h{i}" for i in range(1, 25)]  # h1 = 00–01 local
    # f_hour: per study month and weekday, overpass-hour emission share ÷ (1/24), averaged with our sampling weights
    f_hour = 0.0
    for m, wm in months_w.items():
        for dow0, wdw in enumerate(weekdays_w):
            dt = daytype.get(dow0 + 1, 1)
            prof = h[(h.month_id == m) & (h.Daytype_id == dt)][hour_cols].to_numpy()
            if prof.size == 0:
                continue
            f_hour += wm * wdw * float(np.dot(prof[0] / prof[0].sum(), hours_w) * 24)
    w = wk[wk.activity_code == code].set_index("Weekday_id").daily_factor
    f_week = float(sum(weekdays_w[d] * w.get(d + 1, 1 / 7) * 7 for d in range(7))) if len(w) else 1.0
    mp = monthly_profile(rows, code)
    if mp is None or flat_month:
        f_month, src = 1.0, "flat"
    else:
        prof, desc, year = mp
        f_month, src = float(sum(wm * prof[m - 1] * 12 for m, wm in months_w.items())), f"{desc}, year {year}"
    return {"f_hour": f_hour, "f_week": f_week, "f_month": f_month, "F": f_hour * f_week * f_month, "month_src": src}


def run():
    co2 = json.loads((OUT / "co2_summary.json").read_text())
    co_ratio = json.loads((OUT / "co_ratio.json").read_text())
    sectors = {s: v["nox_t"] for s, v in co2["edgar_sectors_2021"].items() if v["nox_t"] > 1 and s in PROFILE_CODE}
    total = sum(sectors.values())
    hours_w, months_w, weekdays_w = overpass_hour_weights()
    hp, wk, daytype, rows = load_profiles()
    print("Overpass hours (IST):", {h: round(float(x), 3) for h, x in enumerate(hours_w) if x > 0})

    out = {}
    for label, flat_rco in (("EDGAR profiles", False), ("flat residential month profile", True)):
        F, per = 0.0, {}
        for s, nox in sectors.items():
            code = PROFILE_CODE[s]
            f = factors(code, hp, wk, daytype, rows, hours_w, months_w, weekdays_w, flat_month=(flat_rco and code == "RCO"))
            if f is None:
                continue
            per[s] = {**f, "w": nox / total}
        wsum = sum(p["w"] for p in per.values())
        F = sum(p["w"] * p["F"] for p in per.values()) / wsum
        e_mid = co2["satellite_nox_kt_yr_midday"]
        out[label] = {"F": F, "sectors": per, "nox_kt_yr_annual": e_mid / F,
                      "co2_mt_yr_annual_edgar_ratio": e_mid / F * co2["ratio_co2_per_nox_mean"] / 1000,
                      "co2_mt_yr_annual_co_ratio": e_mid / F * co_ratio["co2_nox_co_constrained"]["central"] / 1000}
        print(f"\n[{label}] overall F = {F:.3f}  (observed rate / annual mean)")
        for s, p in sorted(per.items(), key=lambda kv: -kv[1]["w"]):
            print(f"  {s:18s} w {p['w']:.3f}  hour {p['f_hour']:.2f}  week {p['f_week']:.3f}  month {p['f_month']:.2f}  -> {p['F']:.2f}   ({p['month_src']})")
        r = out[label]
        print(f"  NOx: {e_mid:.1f} kt/yr (midday Oct–May) -> {r['nox_kt_yr_annual']:.1f} kt/yr annual mean; "
              f"EDGAR {co2['edgar_nox_kt_yr_mean']:.1f}")
        print(f"  CO2: {r['co2_mt_yr_annual_co_ratio']:.2f} Mt/yr annual (CO-constrained ratio); "
              f"{r['co2_mt_yr_annual_edgar_ratio']:.2f} with EDGAR ratio; EDGAR {co2['edgar_co2_mt_yr_mean']:.2f}, ODIAC {co2['odiac_co2_mt_yr_octmay']:.1f}")
    (OUT / "temporal_adjust.json").write_text(json.dumps(out, indent=2, default=float))


if __name__ == "__main__":
    run()
