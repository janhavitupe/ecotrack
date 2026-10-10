# EcoTrack — Phase 3 Design Note: Building the CO₂ Labels

**For:** faculty guide review · **Author:** Janhavi Tupe · **Date:** 2026-10-01 · **Status:** proposal (D16), **implemented 2026-10-09**

> **Update (2026-10-09):** the design below is built: `labels_v1.csv` with L-fd and L-co. Results are in
> [phase3_report.md](phase3_report.md). One change from this note came out of the data: **CO cannot resolve
> season-to-season totals** (between/within 0.49), so L-co is spatial-only (**D21**, proposed). The primary label is a
> config switch, so the guide's answer to §6 needs no rebuild.

## 1. What Phase 3 has to produce

A **label** (the "answer" the ML models learn to predict) for every 1 km cell and time step: fossil
CO₂ emission. No direct measurement of CO₂ at 1 km exists. Every possible label is *constructed*, so
the question is how to construct it without making Phases 4–6 circular.

## 2. What the data now allow (new evidence)

| Question | Finding | Source |
|---|---|---|
| Can labels vary in time? | **Yes, by season.** City NOx per season (post-D19): 0.434 / 0.602 / 0.733 / 0.666 / 0.663 kg/s (2019–20 → 2023–24). The between-season spread is **2.8× the within-season uncertainty** | `run_seasonal.py` |
| Is the spatial split stable? | **Yes.** The corridor share is 20.0–22.4% in every season (and ±2.4% under all Phase 1 sensitivity tests) | `run_seasonal.py`, D10 |
| Monthly labels? | Not advisable: ~25 overpasses per month gives noisy EMG fits (a weak-plume month gave R² 0.62) | COVID check |
| City CO₂:NOx | 163 (148–180), constrained by TROPOMI CO (post-D19) | D12, D19 |

## 3. The circularity problem

**The proposal's design rule (D2):** a layer used to build a label must not also be a model feature,
or the model just learns the construction recipe back.
- **Proposal's label (activity-weighted allocation):** spreads city CO₂ with night-lights + NDBI + roads.
  These are exactly Experiment D's features. **Circular for Experiment D.**
- **Our planned label (D10, flux-divergence shares):** spreads city CO₂ with the emission map derived from
  TROPOMI **NO₂**, and NO₂ is Experiment A's feature (and in every later experiment). **Circular for Experiment A**,
  though less directly. The label is a physics transform (flux divergence with wind and lifetime) of the NO₂
  field, not the column itself, but the two are strongly related by construction.

There is no fully independent 1 km label for Pune. The design has to **limit and expose** the circularity
rather than pretend it isn't there.

## 4. Options

| Option | Label | Circular with | Pros | Cons |
|---|---|---|---|---|
| **L-act** (proposal) | City CO₂ × activity weights (NTL, NDBI, roads) | Experiment D | Simple; as proposed | Experiment D "wins" by construction; weights are a guess |
| **L-fd** (D10) | Seasonal city CO₂ (EMG × 163) × flux-divergence share | Experiment A (NO₂) | Satellite physics; robust shares; seasonal | Effective resolution ~5 km (TROPOMI); NO₂-linked |
| **L-co** (tested, feasible at ~5 km) | Seasonal city CO₂ × **CO**-based shares (flux divergence of terrain-normalised, static-removed CO) | none of the features (if CO is removed from the features) | Independent of NO₂ and of the activity layers; city total matches the CO step within 3%; r = 0.75 with the NO₂ map | Noisier (corridor share 14.5% [10.9–18.7]); −12% synthetic bias; corridor share differs from NO₂ (14.5% vs 21.1%), so the labels' spatial pattern depends on the tracer |
| **L-inv** | EDGAR/ODIAC maps | – | – | **Ruled out:** inventories are never truth (proposal §5) |

## 5. Proposal (D16): two labels + circularity-aware evaluation

1. **Primary label = L-fd**, seasonal. y(cell, season) = E_NOx(season) × 163 × FD-share(cell),
   using the multi-year FD share pattern (stable) scaled by each season's city total.
   - Uncertainty per label is carried from the bootstrap + the budget (§4.6 of the Phase 1 report).
2. **Test L-co** as a second, NO₂-independent label. If the CO-based map is usable (decided by a synthetic
   test + a noise check, as for every other method), run the ablation on both labels.
3. **Leave-construction-inputs-out rule:** for each label, the inputs used to build it are removed from the
   features, or the result is flagged:
   - with L-fd, Experiment A (NO₂ only) is reported as the **"construction baseline"**, not as evidence that NO₂ "works";
   - the scientific question becomes **whether B/C/D add skill *beyond* it**;
   - with L-co, CO is dropped from the features.
4. **Evaluation beyond R²:**
   - spatial-block CV and leave-one-cluster-out (D5);
   - aggregated predictions compared with the physics city totals per season;
   - season-to-season change predicted vs observed;
   - with L-fd, the independent TROPOMI-CO city CO₂ as an external check.

## 5b. Feasibility result for L-co (2026-10-01)
- Synthetic test with Pune's real winds: static-pattern removal is essential. Raw: −70 mol/s fake signal from terrain; static-removed: ≈ 0, and a source recovered at −12%.
- Real data: 25 km total 248 mol/s vs the CO step 240 (ratio 1.03); levels off with radius; r = 0.75 with the NO₂ map.
- **The corridor share differs: CO 14.5% vs NO₂ 21.1%.** A CO-based label would put *less* CO₂ in the corridor than an NO₂-based one. That's physically plausible (industrial corridor = low CO:NOx), and it means the label's spatial pattern depends on which tracer builds it. That's itself an argument for running the ablation on **both** labels.

## 6. Questions for the guide

1. Is **L-fd** acceptable as the primary label, given the circularity is stated and the A-baseline is reframed?
2. L-co passed a feasibility test (§5b). Should it become the **second label**, with the ablation run on both? Its corridor share differs from L-fd's (14.5% vs 21.1%).
3. Is **seasonal** (5 time steps × 268 cells = 1,340 labelled samples) an acceptable resolution, instead of monthly?
4. Together with D8/D11 (OCO framing) and D12 (CO-constrained ratio), do these change the ablation design
   enough to update Experiment B? Proposal: B becomes "+ TROPOMI CO", since OCO can't be a per-cell feature.

## Appendix — supporting numbers
- Seasonal EMG fits: R² ≥ 0.97 each; n = 135–165 windy overpasses per season.
- **COVID check (model-free, confirmed):** the city NO₂ excess for 25 Mar – 31 May dropped **−74% in 2020** (national lockdown)
  and **−29% in 2021** (Maharashtra restrictions) vs 2022–24. The pipeline responds to real changes, which supports
  seasonal labels. (The EMG fit for the 2020 window alone is degenerate and not used.)
