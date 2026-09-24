"""
Phase 1, steps 5-6 — NOx -> fossil CO2 conversion, inventory comparison, first uncertainty budget.

CO2 = E_NOx(satellite, EMG) x R, with R = EDGAR fossil CO2 / EDGAR NOx over the same area.
The ratio is an ASSUMPTION inherited from the inventory (proposal §5 design rule): it varies by
sector, fuel and technology, and is the base paper's largest error term.

Comparison area = within 25 km of the EMG source, where the flux-divergence total matches EMG.
Corridor and cluster CO2 = city CO2 x flux-divergence shares (D10).

Outputs: outputs/phase1/co2_summary.json and figures/co2_*.png

Usage (after run_city, run_divergence, acquire.edgar, acquire.odiac):
    python -m ecotrack.inversion.run_co2
"""

import glob
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from shapely import contains_xy

from ecotrack.config import DATA_INTERIM
from ecotrack.geometry import corridor_polygon
from ecotrack.inversion.emg import SECONDS_PER_YEAR
from ecotrack.inversion.run_city import BLUE, FIG, INK, ORANGE, OUT

RADIUS_KM = 25
C_TO_CO2 = 44.0095 / 12.011
AQUA = "#1baf7a"
SECTOR_NAMES = {"IND": "Industry (combustion)", "TRO": "Road transport", "RCO": "Residential & commercial",
                "ENE": "Power generation", "CHE": "Chemicals", "REF_TRF": "Refineries & transformation",
                "AGS": "Agricultural soils", "AWB": "Agricultural waste burning", "TNR_Other": "Off-road / rail",
                "TNR_Aviation_LTO": "Aviation (landing/take-off)", "NEU": "Non-energy use", "PRU_SOL": "Solvents",
                "NMM": "Non-metallic minerals", "NFE": "Non-ferrous metals"}


def fine_mask(lat, lon, res, region_fn, sub=10):
    """Fraction of each (lat, lon) cell inside a region, by sub x sub point sampling."""
    frac = np.zeros((len(lat), len(lon)))
    offs = (np.arange(sub) + 0.5) / sub - 0.5
    for a in offs:
        for b in offs:
            la = lat[:, None] + a * res
            lo = lon[None, :] + b * res
            frac += region_fn(np.broadcast_to(la, frac.shape), np.broadcast_to(lo, frac.shape))
    return frac / sub**2


def edgar(species, year, sector="TOTALS"):
    f = DATA_INTERIM / "edgar" / f"{species}_{year}_{sector}.npz"
    if not f.exists():
        return None
    d = np.load(f)
    return d["lat"], d["lon"], d["emissions_t"]


def run():
    city = json.loads((OUT / "city_fit.json").read_text())
    div = json.loads((OUT / "divergence_totals.json").read_text())
    src = tuple(city["source"] if "source" in city else (city["source_lat"], city["source_lon"]))
    main = city["results"][0]
    e_nox = main["emission"]["e_nox_kg_s"]
    boot = main["bootstrap"]

    in_circle = lambda la, lo: np.hypot(*_offs(la, lo, src)) <= RADIUS_KM
    in_corridor = lambda la, lo: contains_xy(corridor_polygon(), lo, la)

    # --- EDGAR: ratio over the comparison area, per year and per sector ---------------------------
    lat_e, lon_e, _ = edgar("NOx", 2021)
    w_city = fine_mask(lat_e, lon_e, 0.1, in_circle)
    w_corr = fine_mask(lat_e, lon_e, 0.1, in_corridor)
    years = {}
    for y in (2019, 2020, 2021, 2022):
        nox, co2 = edgar("NOx", y)[2], edgar("CO2", y)[2]
        years[y] = {"nox_t": float((nox * w_city).sum()), "co2_t": float((co2 * w_city).sum()),
                    "nox_corridor_t": float((nox * w_corr).sum()), "co2_corridor_t": float((co2 * w_corr).sum())}
        years[y]["ratio"] = years[y]["co2_t"] / years[y]["nox_t"]
    sectors = {}
    for s in SECTOR_NAMES:
        n, c = edgar("NOx", 2021, s), edgar("CO2", 2021, s)
        nt = float((n[2] * w_city).sum()) if n else 0.0
        ct = float((c[2] * w_city).sum()) if c else 0.0
        if nt > 1 or ct > 100:
            sectors[s] = {"nox_t": nt, "co2_t": ct, "ratio": ct / nt if nt > 1 else None}
    ratios = np.array([v["ratio"] for v in years.values()])
    r_main = float(ratios.mean())
    # Combustion-only ratio: drop NOx that has no fossil CO2 counterpart (soils, crop burning)
    non_fossil_nox = sum(sectors.get(s, {}).get("nox_t", 0) for s in ("AGS", "AWB"))
    r_comb = years[2021]["co2_t"] / (years[2021]["nox_t"] - non_fossil_nox)

    # --- ODIAC over the same area (Oct-May months, 2019-2023) ---------------------------------------
    files = sorted(glob.glob(str(DATA_INTERIM / "odiac" / "*.npz")))
    d0 = np.load(files[0])
    lat_o, lon_o = d0["lat"], d0["lon"]
    lon2d, lat2d = np.meshgrid(lon_o, lat_o)
    m_city = in_circle(lat2d, lon2d)
    m_corr = in_corridor(lat2d, lon2d)
    odiac_city = np.mean([np.nansum(np.load(f)["t_c_per_cell"][m_city]) for f in files]) * 12 * C_TO_CO2
    odiac_corr = np.mean([np.nansum(np.load(f)["t_c_per_cell"][m_corr]) for f in files]) * 12 * C_TO_CO2

    # --- Satellite CO2 ------------------------------------------------------------------------------
    per_yr = SECONDS_PER_YEAR / 1e6  # kg/s -> kt/yr
    nox_kt = e_nox * per_yr
    co2_mt = nox_kt * r_main / 1000
    shares = {k: div["totals_kg_s"][k] / div["totals_kg_s"]["r25km"]
              for k in ("corridor", "C1_shivajinagar_kasarwadi", "C2_pcmc", "C3_dehu_talegaon", "pune_core")}

    # --- Uncertainty budget (relative, 1 sigma) -----------------------------------------------------
    budget = {
        "EMG fit + sampling (bootstrap)": boot["e_nox_rel_std"],
        "Wind level (850 hPa vs 100 m, half-difference)": abs(city["results"][5]["emission"]["e_nox_kg_s"] - e_nox) / e_nox / 2,
        "Wind regime (E-SE vs W-NW, half-difference)": abs(city["results"][1]["emission"]["e_nox_kg_s"] - city["results"][2]["emission"]["e_nox_kg_s"]) / e_nox / 2,
        "EMG method bias (synthetic test; systematic, kept uncorrected)": 0.12,
        "NOx/NO2 ratio (1.32 +/- 0.1)": 0.10 / 1.32,
        "EDGAR CO2:NOx ratio (year-to-year + combustion-only choice)": float(np.hypot(ratios.std() / r_main, abs(r_comb - r_main) / r_main)),
        "EDGAR ratio representativeness (Xie et al. 2026 value, ~25%)": 0.25,
    }
    total_rel = float(np.sqrt(sum(v**2 for v in budget.values())))

    summary = {
        "comparison_area": f"within {RADIUS_KM} km of source {src}",
        "satellite_nox_kg_s": e_nox, "satellite_nox_kt_yr_midday": nox_kt,
        "satellite_nox_kt_yr_ci95": boot["e_nox_kt_yr_ci95"],
        "edgar_by_year": years, "edgar_sectors_2021": sectors,
        "ratio_co2_per_nox_mean": r_main, "ratio_combustion_only_2021": r_comb,
        "satellite_co2_mt_yr_midday": co2_mt,
        "satellite_co2_mt_yr_range_1sigma": [co2_mt * (1 - total_rel), co2_mt * (1 + total_rel)],
        "edgar_co2_mt_yr_mean": float(np.mean([v["co2_t"] for v in years.values()]) / 1e6),
        "edgar_nox_kt_yr_mean": float(np.mean([v["nox_t"] for v in years.values()]) / 1e3),
        "odiac_co2_mt_yr_octmay": float(odiac_city / 1e6),
        "shares_of_city": shares,
        "zone_co2_mt_yr": {k: co2_mt * s for k, s in shares.items()},
        "corridor_inventories_mt_yr": {"edgar": float(np.mean([v["co2_corridor_t"] for v in years.values()]) / 1e6),
                                       "odiac": float(odiac_corr / 1e6)},
        "uncertainty_budget_rel_1sigma": budget, "uncertainty_total_rel_1sigma": total_rel,
        "notes": ["'Midday' rates: TROPOMI overpass 11:30-13:30 IST, Oct-May; not annual totals.",
                  "ODIAC in tonnes C/cell/month (US GHG Center docs), converted x44/12; spatial proxy includes nighttime lights.",
                  "EDGAR NOx is expressed as NO2 mass, matching the satellite convention."],
    }
    (OUT / "co2_summary.json").write_text(json.dumps(summary, indent=2))
    report(summary)
    figures(summary)


def _offs(la, lo, src):
    dx = (lo - src[1]) * 111.320 * np.cos(np.radians(src[0]))
    dy = (la - src[0]) * 110.574
    return dx, dy


def report(s):
    print(f"Comparison area: {s['comparison_area']}")
    print(f"Satellite NOx: {s['satellite_nox_kg_s']:.3f} kg/s = {s['satellite_nox_kt_yr_midday']:.1f} kt/yr (midday rate)")
    print(f"EDGAR NOx (same area, 2019-22 mean): {s['edgar_nox_kt_yr_mean']:.1f} kt/yr  -> satellite/EDGAR = "
          f"{s['satellite_nox_kt_yr_midday'] / s['edgar_nox_kt_yr_mean']:.2f}")
    print("EDGAR CO2/NOx ratio by year:", {y: round(v["ratio"], 1) for y, v in s["edgar_by_year"].items()},
          f"mean {s['ratio_co2_per_nox_mean']:.1f}; combustion-only {s['ratio_combustion_only_2021']:.1f}")
    print("EDGAR 2021 sectors (same area):")
    for k, v in sorted(s["edgar_sectors_2021"].items(), key=lambda kv: -kv[1]["co2_t"]):
        r = f"{v['ratio']:.0f}" if v["ratio"] else "-"
        print(f"  {SECTOR_NAMES[k]:30s} NOx {v['nox_t']:8,.0f} t  CO2 {v['co2_t']:11,.0f} t  ratio {r}")
    print(f"\nSATELLITE fossil CO2: {s['satellite_co2_mt_yr_midday']:.2f} Mt/yr (midday rate), "
          f"±{100 * s['uncertainty_total_rel_1sigma']:.0f}% (1 sigma) -> "
          f"{s['satellite_co2_mt_yr_range_1sigma'][0]:.2f}-{s['satellite_co2_mt_yr_range_1sigma'][1]:.2f}")
    print(f"EDGAR CO2 (same area): {s['edgar_co2_mt_yr_mean']:.2f} Mt/yr;  ODIAC (Oct-May, x12): {s['odiac_co2_mt_yr_octmay']:.2f} Mt/yr")
    print("Zone CO2 (Mt/yr, via FD shares):", {k: round(v, 3) for k, v in s["zone_co2_mt_yr"].items()})
    print("Corridor CO2 in inventories (Mt/yr):", {k: round(v, 3) for k, v in s["corridor_inventories_mt_yr"].items()})
    print("Uncertainty budget (1 sigma):")
    for k, v in s["uncertainty_budget_rel_1sigma"].items():
        print(f"  {k:62s} {100 * v:5.1f}%")
    print(f"  {'TOTAL (root-sum-square)':62s} {100 * s['uncertainty_total_rel_1sigma']:5.1f}%")


def figures(s):
    # City CO2: satellite vs inventories
    fig, ax = plt.subplots(figsize=(6.6, 2.8))
    rows = [("Satellite (TROPOMI NO₂ × EDGAR ratio)", s["satellite_co2_mt_yr_midday"], BLUE, s["satellite_co2_mt_yr_range_1sigma"]),
            ("EDGAR v8.0", s["edgar_co2_mt_yr_mean"], ORANGE, None),
            ("ODIAC v2024 (Oct–May)", s["odiac_co2_mt_yr_octmay"], AQUA, None)]
    for i, (label, val, col, rng) in enumerate(rows):
        ax.barh(i, val, color=col, height=0.55)
        if rng:
            ax.plot(rng, [i, i], color=INK, lw=1.5)
        ax.text(max(val, rng[1] if rng else val) + 0.2, i, f"{val:.1f}", va="center", fontsize=9, color=INK)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows]); ax.invert_yaxis(); ax.grid(axis="y", visible=False)
    ax.set_xlabel("Fossil CO₂ (Mt/yr)")
    fig.suptitle(f"Pune + PCMC fossil CO₂, within {RADIUS_KM} km (satellite ±1σ)", fontsize=11, x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(FIG / "co2_city_comparison.png"); plt.close(fig)

    # Uncertainty budget
    b = s["uncertainty_budget_rel_1sigma"]
    items = sorted(b.items(), key=lambda kv: kv[1])
    fig, ax = plt.subplots(figsize=(7, 0.42 * len(items) + 1.3))
    ax.barh(range(len(items)), [100 * v for _, v in items], color=BLUE, height=0.55)
    for i, (_, v) in enumerate(items):
        ax.text(100 * v + 0.4, i, f"{100 * v:.0f}%", va="center", fontsize=9, color=INK)
    ax.set_yticks(range(len(items)), [k for k, _ in items]); ax.grid(axis="y", visible=False)
    ax.set_xlabel("Relative uncertainty (1σ, %)")
    fig.suptitle(f"Uncertainty budget: total ±{100 * s['uncertainty_total_rel_1sigma']:.0f}% (1σ, root-sum-square)", fontsize=11, x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(FIG / "co2_uncertainty_budget.png"); plt.close(fig)


if __name__ == "__main__":
    run()
