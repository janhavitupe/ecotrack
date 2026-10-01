"""
Monte Carlo uncertainty budget for the city fossil-CO₂ estimate (replaces the root-sum-square
budget's independent-Gaussian shortcut; findings §4.8 / D12).

Each draw multiplies through the whole chain:
    CO₂_midday = E_NOx(bootstrap draw) × wind_level × wind_regime × method_bias × (NOx/NO₂ ratio / 1.32)
                 × CO₂:NOx(CO-constrained draw) × per-sector ratio factor × EDGAR year factor
    CO₂_annual = CO₂_midday / F(temporal profiles, D17)
Error terms are multiplicative and lognormal (emissions can't go negative), with σ as in the RSS budget.
Two treatments of the EMG synthetic bias (+11–12%, a *known* overestimate):
  "symmetric"      : ±12% uncertainty around 1 (as in the RSS budget; no correction)
  "bias-corrected" : divide by (1 + b), b ~ N(0.115, 0.03): the synthetic tests' mean and spread
Outputs: outputs/phase1/mc_budget.json, figures/mc_budget.png

Usage (after run_city, run_co2, run_co_ratio, temporal_adjust):
    python -m ecotrack.inversion.mc_budget
"""

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from ecotrack.inversion.emg import SECONDS_PER_YEAR
from ecotrack.inversion.run_city import BLUE, FIG, INK, ORANGE, OUT, SURFACE

N = 200_000
SEED = 7


def lognormal(rng, sigma, n):
    """Multiplicative factor with median 1 and log-sd ≈ the relative 1σ."""
    return np.exp(rng.normal(0.0, np.log1p(sigma), n))


def run():
    rng = np.random.default_rng(SEED)
    city = json.loads((OUT / "city_fit.json").read_text())
    co2 = json.loads((OUT / "co2_summary.json").read_text())
    cor = json.loads((OUT / "co_ratio.json").read_text())
    tmp = json.loads((OUT / "temporal_adjust.json").read_text())
    budget = co2["uncertainty_budget_rel_1sigma"]
    main = city["results"][0]

    # E_NOx: resample the bootstrap's 95% CI as a lognormal (the per-draw values aren't stored)
    lo, med, hi = main["bootstrap"]["e_nox_kg_s_ci95"]
    sig_boot = (np.log(hi) - np.log(lo)) / (2 * 1.96)
    e_nox = main["emission"]["e_nox_kg_s"] * np.exp(rng.normal(0, sig_boot, N))

    wl = lognormal(rng, budget["Wind level (850 hPa vs 100 m, half-difference)"], N)
    wr = lognormal(rng, budget["Wind regime (E-SE vs W-NW, half-difference)"], N)
    nox_ratio = rng.normal(1.32, 0.10, N) / 1.32
    yr = lognormal(rng, budget["EDGAR CO2:NOx ratio (year-to-year + combustion-only choice)"], N)
    lo_r, hi_r = cor["co2_nox_co_constrained"]["range_95"]
    ratio = np.exp(rng.normal(np.log(cor["co2_nox_co_constrained"]["central"]), (np.log(hi_r) - np.log(lo_r)) / (2 * 1.96), N))
    sector = lognormal(rng, 0.10, N)
    struct = lognormal(rng, budget.get("EMG structure: background model & fit window (D19)", 0.0), N)
    f_lo, f_hi = tmp["flat residential month profile"]["F"], tmp["EDGAR profiles"]["F"]
    F = rng.uniform(f_lo, f_hi, N) * lognormal(rng, 0.10, N)  # profile choice + ~10% generic-profile uncertainty

    per_year = SECONDS_PER_YEAR / 1e9  # kg/s -> Mt/yr
    results = {}
    for label, bias in (("symmetric", lognormal(rng, 0.12, N)),
                        ("bias-corrected", 1.0 / (1.0 + rng.normal(0.115, 0.03, N)))):
        nox_mid = e_nox * wl * wr * bias * nox_ratio * struct         # kg/s NOx
        co2_mid = nox_mid * per_year * ratio * sector * yr            # Mt/yr CO2 (midday rate)
        co2_ann = co2_mid / F
        q = lambda a: [float(v) for v in np.percentile(a, [2.5, 16, 50, 84, 97.5])]
        results[label] = {"nox_midday_kt_yr": q(nox_mid * SECONDS_PER_YEAR / 1e6), "co2_midday_mt_yr": q(co2_mid),
                          "co2_annual_mt_yr": q(co2_ann), "nox_annual_kt_yr": q(nox_mid * SECONDS_PER_YEAR / 1e6 / F)}
        r = results[label]
        print(f"[{label}]  percentiles 2.5 / 16 / 50 / 84 / 97.5")
        for k in ("nox_midday_kt_yr", "co2_midday_mt_yr", "nox_annual_kt_yr", "co2_annual_mt_yr"):
            print(f"  {k:18s} " + " / ".join(f"{v:6.2f}" for v in r[k]))
        c = r["co2_midday_mt_yr"]
        print(f"  midday CO2 1-sigma range relative to median: -{100 * (1 - c[1] / c[2]):.0f}% / +{100 * (c[3] / c[2] - 1):.0f}%")

    edgar, odiac = co2["edgar_co2_mt_yr_mean"], co2["odiac_co2_mt_yr_octmay"]
    for label, r in results.items():
        a = r["co2_annual_mt_yr"]
        r["edgar_inside_95"] = bool(a[0] <= edgar <= a[4])
        r["odiac_inside_95"] = bool(a[0] <= odiac <= a[4])
    out = {"n_draws": N, "seed": SEED, "results": results, "edgar_co2_mt_yr": edgar, "odiac_co2_mt_yr": odiac,
           "rss_total_rel_1sigma": cor["uncertainty_total_rel_1sigma_revised"]}
    (OUT / "mc_budget.json").write_text(json.dumps(out, indent=2))
    print(f"EDGAR {edgar:.2f} Mt inside the annual 95% range: {[results[k]['edgar_inside_95'] for k in results]}; "
          f"ODIAC {odiac:.1f}: {[results[k]['odiac_inside_95'] for k in results]}")

    fig, ax = plt.subplots(figsize=(7, 3.2))
    rows = [("Midday rate, symmetric", results["symmetric"]["co2_midday_mt_yr"], BLUE),
            ("Annual mean, symmetric", results["symmetric"]["co2_annual_mt_yr"], BLUE),
            ("Annual mean, bias-corrected", results["bias-corrected"]["co2_annual_mt_yr"], ORANGE)]
    for i, (lab, q, col) in enumerate(rows):
        ax.plot([q[0], q[4]], [i, i], color=col, lw=1.5)
        ax.plot([q[1], q[3]], [i, i], color=col, lw=5, solid_capstyle="butt")
        ax.plot(q[2], i, "o", color=col, ms=8, mec=SURFACE, mew=2)
        ax.text(q[4] + 0.1, i, f"{q[2]:.2f} [{q[0]:.2f}–{q[4]:.2f}]", va="center", fontsize=8, color=INK)
    ax.axvline(edgar, color=INK, ls="--", lw=1); ax.text(edgar, -0.5, " EDGAR", fontsize=8, color=INK, va="bottom")
    ax.set_yticks(range(len(rows)), [r[0] for r in rows]); ax.invert_yaxis(); ax.grid(axis="y", visible=False)
    ax.set_xlabel("Fossil CO₂, Pune + PCMC within 25 km (Mt/yr)"); ax.set_xlim(left=0)
    fig.suptitle(f"Monte Carlo uncertainty ({N:,} draws): median, 68% (thick) and 95% (thin) ranges", fontsize=10, x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(FIG / "mc_budget.png"); plt.close(fig)


if __name__ == "__main__":
    run()
