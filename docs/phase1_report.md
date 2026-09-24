# EcoTrack — Phase 1 Report
## Satellite NO₂ inversion and first fossil-CO₂ estimate for Pune + PCMC

**Project:** Meteorology-informed multi-source satellite estimation of urban fossil-fuel CO₂, Shivajinagar → Talegaon Dabhade corridor, Pune
**Author:** Janhavi Tupe · **Phase:** 1 of 8 (proposal weeks 1–4) · **Date:** 2026-09-24
**Status:** complete. Three proposed design decisions (D8, D11, D12) await the guide's sign-off (§7).

---

## Summary

Phase 1 set out to reproduce the base paper's NO₂-based emission method (Xie et al., 2026) on the Pune corridor, as a standalone floor result. It did that, and went further: it added a second emission-mapping method, tested direct CO₂ satellite data, and used TROPOMI CO to constrain the method's largest error term.

**Headline result.** Pune + Pimpri-Chinchwad emit **0.52 kg/s NOx** at midday [95% CI 0.49–0.56], with an NO₂ lifetime of **1.7 h**. That converts to **2.98 Mt fossil CO₂/yr ± 24% (1σ)**, expressed as a midday October–May rate.

**Key findings**
1. **The method was validated before it was trusted.** On synthetic plumes with known emissions, it recovers the emission within +12% (EMG, a measured bias), −4% (flux divergence) and −1.4% (CO step). The fit is insensitive to the optimiser settings (36 combinations, identical result) and to outlier removal (< 2% change).
2. **The strongest source is central Pune, just south of the corridor.** A second, distinct hotspot sits on Pimpri–Chinchwad, 16.7 km away, at about 75% of Pune's strength. **The corridor emits 21% of the metro's NOx**, a share that is stable (±2.4%) across all sensitivity tests.
3. **Two independent satellite methods agree within 9%** at a matched 25 km radius, and place the main source at the same pixel.
4. **The two official inventories disagree by 3.2×** for the same area (EDGAR 3.6 vs ODIAC 11.8 Mt CO₂/yr). The satellite NOx is 22% below EDGAR's.
5. **Direct CO₂ satellites (OCO-3/OCO-2) cannot detect Pune's plume.** The expected signal (0.02–0.15 ppm) is well below the instrument noise and artefacts (0.5–1 ppm). They give only an upper limit (7–14 Mt/yr) and a detection threshold (~8–15 Mt/yr).
6. **TROPOMI CO does constrain the NOx → CO₂ conversion.** Pune's CO:NOx is 33% above EDGAR's, which requires more household/biomass-type combustion than EDGAR assumes. This narrows the CO₂:NOx ratio from a sector span of 115–393 to **167–197**, and cuts the total uncertainty from **±32% to ±24%**.

**Answer to the research question, for Phase 1:** combining satellite sources measurably improves the estimate. The improvement comes from **TROPOMI CO**, not from direct CO₂ observation, which for a city of Pune's size provides a bound rather than a measurement.

---

## 1. Objective

From the proposal (§7, Phase 1): reproduce the base paper's pipeline on the corridor.
1. QC TROPOMI NO₂.
2. Match it to wind.
3. Locate the source, rotate the plumes and compute line densities.
4. Fit the plume model with Differential Evolution, sensitivity-testing its settings.
5. Convert to CO₂ with an EDGAR NOx:CO₂ ratio, labelled as an assumption.
6. Compare with ODIAC as a plausibility check.

Deliverables: the QC'd dataset, wind-matched observations, plume plots, inversion results, first CO₂ estimates, the ODIAC comparison, and this report.

## 2. Study area and data

| Item | Value |
|---|---|
| Period | 1 Oct 2019 – 31 May 2024, **October–May only** (5 dry seasons, 40 months) |
| Corridor | Old Pune–Mumbai Highway centreline ± 3.5 km, plus Talegaon MIDC: **269 km²** (D9) |
| Clusters | C1 Shivajinagar–Kasarwadi · C2 PCMC · C3 Dehu Road–Talegaon |
| NO₂ | TROPOMI OFFL L3 (Google Earth Engine): **1,004 usable overpasses** on a 0.01° grid over a ~100 km box |
| CO | TROPOMI OFFL L3: **907 overpasses**, same grid |
| Wind | ERA5 hourly at 10 m, 100 m and 850 hPa, matched to each overpass (≤ 30 min) |
| Direct CO₂ | OCO-3 (7 dates) and OCO-2 (1 date) with ≥ 50 good soundings over Pune |
| Inventories | EDGAR v8.1 NOx and CO / v8.0 fossil CO₂ (2019–2022; sectors 2021); ODIAC v2024 (to Dec 2023) |
| Terrain | SRTM elevation, averaged to the same grid |

The pre-Phase-1 feasibility checks all passed or were resolved (details in `feasibility_memo.md`):
- TROPOMI coverage: a median of 26 usable days per month.
- Every cluster shows NO₂ 1.7–2.4× above background in every season.
- The proposal's waypoints, off by up to 4.4 km, were corrected, and the corridor rebuilt on the actual highway (D9).

**Meteorology.** At the overpass time (11:30–13:30 IST), the median wind at 850 hPa is 3.5 m/s and the boundary layer is 1.66 km deep. Winds come from the **east-southeast in October–March**, carrying Pune's plume up the corridor, and **reverse to west-northwest in April–May**.

## 3. Methods

### 3.1 Quality control
- **Filters:** cloud fraction ≤ 0.3 and solar zenith ≤ 70°, plus Earth Engine's own built-in quality filter. The Earth Engine product has no `qa_value` band, so the proposal's "QA ≥ 0.7" can't be applied directly.
- **IQR outlier removal:** each pixel is checked against its own time series using Tukey's far-out fences (k = 3), which removes 0.09% of pixels (D13).
- **Why this variant:** two others were rejected. A whole-scene filter clips the plume core. A local-neighbourhood filter removed 29% of real pixels, because Earth Engine's 1 km grid copies each TROPOMI footprint (~3.5 × 5.5 km) into several cells.

### 3.2 City-scale inversion (EMG, the base paper's method)
1. **Locate the source** as the maximum of the calm-wind composite (187 overpasses, wind < 2 m/s).
2. **Rotate** each windy overpass (781 overpasses, 2–8 m/s at 850 hPa) about that point, so its wind blows along +x.
3. **Build the line density** L(x) by integrating the mean rotated field ±20 km across the wind.
4. **Fit** L(x) = a·EMG(x; x₀, μ, σ) + B with Differential Evolution (population 300, F ∈ [0.5, 1.0], CR = 0.7).
5. **Derive the emission:** lifetime τ = x₀/w and E(NOx) = 1.32 · a/τ.
6. **Uncertainty:** a 200-member bootstrap over overpasses.

### 3.3 Spatial attribution (flux divergence; Beirle et al., 2019)
E = 1.32 · [∇·(V·w) + (V − V_bg)/τ]
- Computed on the mean flux field of 968 overpasses.
- τ comes from the EMG fit; V_bg is the 10th percentile of the mean column.
- Emissions are then summed over the corridor zones, the Pune core, and circles of increasing radius. D10 explains why zone *shares*, not absolute totals, are used.

### 3.4 NOx → CO₂ and inventories
- CO₂ = satellite NOx × EDGAR's CO₂:NOx ratio for the same area, within 25 km of the source.
- EDGAR and ODIAC totals are computed over the same area as plausibility comparisons, never as ground truth.

### 3.5 Direct CO₂ check (OCO-3/OCO-2, exploratory D8)
Plume-model scaling on the 8 dates:
1. The flux-divergence emission map, scaled to the satellite CO₂ estimate, is carried downwind as a Gaussian column plume on each day's ERA5 wind.
2. A weighted regression of observed XCO₂ on the predicted plume (plus a regional gradient) gives a scale factor β. β = 1 means agreement.
3. The dates are combined by inverse-variance weighting, with errors inflated for the scatter between dates.

### 3.6 Sector constraint from TROPOMI CO (D4)
CO is inert over plume timescales, so downwind of the city its line density steps up by E(CO)/w. The estimator:
1. Normalise each column by the relative air mass at that pixel's elevation. The Western Ghats imprint about 6% on the CO column, more than Pune's own signal.
2. Remove each day's median and each pixel's long-term mean. That removes everything fixed in space.
3. Rotate by the wind; take the downwind-minus-upwind line density.
4. E(CO) = step ÷ ⟨1/w⟩.

The observed CO:NOx is then compared with EDGAR's per-sector ratios, re-splitting one sector pair at a time, to infer the sector mix and the matching CO₂:NOx.

### 3.7 Validation
Every estimator was tested on synthetic data with known answers, on the real grid, with realistic noise (`tests/`, 11 tests):

| Estimator | Recovered emission | Notes |
|---|---|---|
| EMG | **+11 to +12%** (τ −16%) | Systematic, from three identified causes; kept in the uncertainty budget, not corrected |
| Flux divergence | **−4%** | Stable across radii; no spurious sources |
| CO step | **−1.4%** | Terrain pattern larger than the plume; terrain alone gives ≈ 0 |
| IQR filter | line density changed 0.9% | Catches 92% of injected spikes |

The DE fit was repeated for 36 combinations of population, F, CR and seed. **All converged to the identical optimum** (spread < 0.001%).

## 4. Results

### 4.1 Where the NOx comes from

![Calm-wind NO₂ composite](../outputs/phase1/figures/calm_composite.png)

The calm-wind NO₂ maximum, the city source, is at **18.485 N, 73.855 E** (Swargate/Camp, central Pune), about 2 km south of the corridor's southern tip.

![Flux-divergence NOx emission map](../outputs/phase1/figures/divergence_map.png)

The flux-divergence map resolves **two distinct hotspots, 16.7 km apart**:

| Hotspot | Location | NOx within 8 km |
|---|---|---|
| Central Pune | 18.485 N, 73.855 E (outside the corridor) | 0.147 kg/s |
| Pimpri–Chinchwad | 18.625 N, 73.795 E (**inside the corridor**) | 0.112 kg/s (~75% of Pune) |

### 4.2 City-scale NOx emission

![EMG line density fit](../outputs/phase1/figures/line_density_main.png)

| Run | n | E(NOx) kg/s [95% CI] | τ (h) | R² |
|---|---|---|---|---|
| **Main (850 hPa, 2–8 m/s)** | **781** | **0.522 [0.486–0.555]** | **1.67 [1.55–1.81]** | 0.991 |
| Easterly regime | 429 | 0.561 | 1.42 | 0.990 |
| Westerly regime | 276 | 0.442 | 2.18 | 0.979 |
| Wind 2–4 / 4–8 m/s | 416 / 365 | 0.478 / 0.506 | 1.97 / 1.62 | 0.994 / 0.985 |
| Wind at 100 m / 10 m | 782 / 675 | 0.456 / 0.347 | 1.82 / 2.35 | 0.981 / 0.977 |

The main result is **16.5 kt NOx/yr as a midday rate**. The wind level is the largest sensitivity. Surface wind is too slow to represent a plume ~1 km deep, so 850 hPa is the physically justified choice. The fit's one misfit, a rise 50–60 km downwind, is PCMC and Talegaon appearing up the corridor in east-southeast winds. That is exactly why flux divergence was needed for attribution.

### 4.3 The two methods agree; the corridor's share is robust

![Flux divergence vs EMG](../outputs/phase1/figures/divergence_vs_emg.png)

- **Agreement:** within 25 km of the source, flux divergence gives **0.570 kg/s** against EMG's **0.522 kg/s**, a difference of 9%.
- **Why flux divergence gives shares, not the city total (D10):** its total doesn't level off with radius, because its lifetime term (~70% of the total) keeps growing. Its absolute totals shift by −16% to +30% with the lifetime and background choices. **Zone shares vary by only ±2.4%.**

| Zone | Share of 25 km total | NOx (kg/s) | Fossil CO₂ (Mt/yr)* |
|---|---|---|---|
| Pune core (outside the corridor) | 29.5% | 0.168 | 0.88 |
| C1 Shivajinagar–Kasarwadi | 10.1% | 0.058 | 0.30 |
| C2 PCMC | 6.5% | 0.037 | 0.19 |
| C3 Dehu Road–Talegaon | 4.5% | 0.025 | 0.13 |
| **Corridor (all three)** | **21.1%** | **0.120** | **0.63** |

\* *City CO₂ (2.98 Mt/yr, §4.5) × share. The corridor zones are 1–2 TROPOMI pixels wide, so some emission smears across zone edges.*

### 4.4 Comparison with inventories

![City CO₂: satellite vs inventories](../outputs/phase1/figures/co2_city_comparison.png)

| Within 25 km of the source | NOx (kt/yr) | Fossil CO₂ (Mt/yr) |
|---|---|---|
| Satellite (midday rate) | 16.5 | 2.83 using EDGAR's ratio · **2.98 using the CO-constrained ratio** |
| EDGAR v8 (2019–2022) | 21.1 | 3.63 |
| ODIAC v2024 (Oct–May) | – | 11.8 |

- **The satellite NOx is 22% below EDGAR.** A midday rate would normally be *higher* than the daily mean, so either EDGAR overestimates Pune's NOx, or the EMG's fitted background absorbs diffuse emissions. This is unresolved.
- **ODIAC is 3.2× EDGAR.** ODIAC allocates emissions using nighttime lights; its concentration of emissions in brightly lit cities is a plausible explanation still to be checked. An inventory disagreement this large is a result in itself: it shows why an independent satellite estimate matters.

### 4.5 NOx → CO₂: the ratio problem, and how TROPOMI CO narrows it

EDGAR's city CO₂:NOx ratio is **172** and stable from year to year (166–176). By sector, though, it ranges from **115 (industry) to 393 (residential)**, so the answer depends on Pune's true sector mix. The base paper identifies this conversion as its largest error term.

**OCO-3/OCO-2 cannot resolve it.** The predicted Pune plume is 0.02–0.15 ppm, against 0.5–1.1 ppm sounding noise and swath-stripe artefacts of 0.5–1 ppm on the snapshot maps.

| Emission prior | Scale factor β (1 = agrees) | 95% upper limit | 3σ detection threshold |
|---|---|---|---|
| Confined to 10 km | 1.02 ± 0.94 | 7.3 Mt/yr | ~8 Mt/yr |
| Spread over 25 km | 2.00 ± 1.81 | 14.1 Mt/yr | ~15 Mt/yr |

The data are *consistent* with the estimate but don't detect the plume. EDGAR's value is consistent in every variant; there is a tentative, non-robust hint that ODIAC's is too high.

![OCO soundings vs predicted plume](../outputs/phase1/figures/oco_dates_r10.png)

**TROPOMI CO can resolve it.** The CO step over Pune is clearly detected:

![CO step over Pune](../outputs/phase1/figures/co_step.png)

| | Value |
|---|---|
| E(CO) | 6.73 kg/s |
| **CO:NOx** | **21.2 mol/mol [18.7–23.8]**, 33% above EDGAR's 16.0 |
| Robustness | 19.5–22.0 across terrain handling and season (no fire-season inflation) |

Re-splitting one pair of sectors at a time to match the observed ratio:

| Scenario | Feasible? | CO₂:NOx [95%] |
|---|---|---|
| High-CO group (residential + crop burning) vs rest | yes (share 18.5% vs EDGAR 11%) | 188 [179–197] |
| Industry vs transport | **no** (needs 154% industry) | – |
| Residential vs industry | yes (24% vs 13%) | 181 [171–192] |
| Residential vs transport | yes (57% vs 33%) | 174 [167–182] |

**The excess CO can't come from industry replacing transport.** It requires more residential/biomass-type combustion than EDGAR assumes. The **CO-constrained CO₂:NOx is 181 (95% range 167–197)**, which gives **2.98 Mt CO₂/yr**.

### 4.6 Uncertainty budget

| Term (1σ) | EDGAR ratio | **CO-constrained** |
|---|---|---|
| Ratio representativeness (the base paper's value) | 25.0% | – |
| CO₂:NOx from the TROPOMI CO scenarios | – | 8.1% |
| EDGAR per-sector ratios (assumed) | – | 10.0% |
| EMG method bias (synthetic test) | 12.0% | 12.0% |
| Wind regime (E-SE vs W-NW) | 11.4% | 11.4% |
| NOx/NO₂ ratio (1.32 ± 0.1) | 7.6% | 7.6% |
| Wind level (850 hPa vs 100 m) | 6.4% | 6.4% |
| Bootstrap (fit + sampling) | 3.3% | 3.3% |
| EDGAR ratio, year to year | 3.1% | 3.1% |
| **Total (root-sum-square)** | **31.9%** | **23.6%** |
| **Fossil CO₂ (Mt/yr, midday rate)** | 2.83 (1.93–3.74) | **2.98 (2.28–3.69)** |

## 5. Deviations from the proposal

| Proposal | What was done | Why | Ref. |
|---|---|---|---|
| Line densities per sub-zone (10 waypoints) | City-scale EMG + flux-divergence attribution to 3 clusters | Waypoints are closer together than one TROPOMI pixel; a single-source fit can't separate adjacent sources | D1, D10 |
| QA ≥ 0.7 | Earth Engine's built-in filter + cloud and solar-zenith cuts | The Earth Engine product has no `qa_value` band | §3.1 |
| "IQR outlier removal" (method unspecified) | Per-pixel time series, k = 3 | The other variants clip the plume or remove 29% of real data | D13 |
| Waypoint-based corridor | Highway centreline ± 3.5 km + Talegaon MIDC | Waypoints were off by up to 4.4 km; Talegaon MIDC lay outside | D9 |
| OCO-3 as an ML feature / independent target | City-scale consistency check, upper limit and detection threshold | No detectable plume at Pune's emission level | D3 → D8 → D11 |
| EDGAR ratio as a fixed assumption | Ratio constrained by TROPOMI CO | Largest error term; CO measures the sector mix | D4, D12 |
| Not in the proposal | Flux divergence, synthetic validation of every estimator, DE settings test, TROPOMI CO | Robustness and attribution | – |

## 6. Limitations

- **Midday October–May rates, not annual totals.** The satellite sees 11:30–13:30 IST and no monsoon months. A diurnal/seasonal adjustment is still to be done before a like-for-like comparison with annual inventories.
- **The EMG bias (+12%) is kept, not corrected.** The headline is therefore likely slightly high; the bias sits in the budget.
- **The CO₂:NOx constraint trusts EDGAR's per-sector ratios** (an assumed 10% term) and re-splits one pair at a time. Secondary CO from VOC oxidation, and the EMG NOx bias, would both push the true ratio higher.
- **Flux divergence assumes one uniform wind per overpass.** ERA5 can't resolve finer structure. Its absolute totals depend on the lifetime and background, which is why only shares are used.
- **The corridor zones are narrow** (1–2 TROPOMI pixels), so emission smears across zone edges.
- **The largest source (central Pune) is outside the corridor.** Corridor columns include NO₂ transported from Pune, especially in October–March east-southeast winds.
- **The Chakan industrial area** (outside the corridor, to the NE) may contribute on NE-wind days.
- **The satellite NOx is 22% below EDGAR**; the cause is unresolved.
- **The OCO analysis rests on 8 dates.** Its combined result leans on one near-calm date, where the plume model is least valid.

## 7. Decisions requiring the guide's sign-off

1. **D8 / D11: how to frame OCO-3/OCO-2.** Proposed: report them as a consistency check with an upper limit (7–14 Mt/yr) and a detection threshold (~8–15 Mt/yr), *not* as an independent emission estimate or an ML feature. Consequence: Experiment B changes meaning (see §8).
2. **D12: headline CO₂ from the TROPOMI-CO-constrained ratio.** Proposed: 2.98 Mt/yr ± 24%, with the EDGAR-ratio value (2.83 ± 32%) reported alongside.
3. **(For information) D10:** city totals from EMG, and the spatial split from flux-divergence shares.

## 8. Implications for Phases 2–3

- **Labels (Phase 3):** the city total can be distributed to 1 km cells using the **satellite-derived flux-divergence shares** (D10), instead of nighttime-light/NDBI/road weights. That removes the circularity D2 guards against: the activity layers can then be model features without also defining the labels.
- **Experiment B (OCO-3):** OCO data can't serve as a per-cell feature (D11). The proposal's "does direct CO₂ observation help?" question is already answered for Pune: it gives a bound, not a measurement. Phase 2 should reframe Experiment B accordingly, for example around TROPOMI CO as the second tracer.
- **TROPOMI CO** is downloaded and validated, and can enter Phase 2 as a gridded layer.

## 9. Next steps

1. Guide review of D8, D11 and D12.
2. Diurnal/seasonal adjustment of the midday rate; a Monte Carlo version of the uncertainty budget.
3. Phase 2 data layers on the 1 km grid: VIIRS, OSM roads, Sentinel-2 NDBI/NDVI (TROPOMI CO, EDGAR and ODIAC are already in hand).

---

## Appendix A — Reproducibility

All thresholds are in `configs/study.yaml`; the code is in `src/ecotrack/`; the tests are in `tests/` (11 pass).

```
python -m ecotrack.acquire.tropomi_cube ; python -m ecotrack.acquire.tropomi_cube --product co
python -m ecotrack.acquire.era5_overpass ; python -m ecotrack.acquire.dem
python -m ecotrack.acquire.edgar ; python -m ecotrack.acquire.odiac
python -m ecotrack.inversion.run_city          # EMG city inversion
python -m ecotrack.inversion.run_divergence    # flux-divergence map and zones
python -m ecotrack.inversion.run_co2           # NOx -> CO2, inventories, budget
python -m ecotrack.inversion.run_oco_check --prior-radius 10 --tag _r10
python -m ecotrack.inversion.run_co_ratio      # TROPOMI CO constraint
python -m ecotrack.inversion.de_sensitivity    # 36 DE settings
python -m pytest
```

| Output | File |
|---|---|
| EMG results | `outputs/phase1/city_fit.json` |
| Flux-divergence totals and map | `outputs/phase1/divergence_totals.json`, `divergence_map.npz` |
| CO₂, inventories, first budget | `outputs/phase1/co2_summary.json` |
| OCO check | `outputs/phase1/oco_check.json`, `oco_check_r10.json` |
| CO ratio, scenarios, revised budget | `outputs/phase1/co_ratio.json` |
| DE sensitivity | `outputs/phase1/de_sensitivity.json` |
| Results before IQR filtering | `outputs/phase1/v1_before_iqr/` |
| All figures | `outputs/phase1/figures/` |

## Appendix B — Supporting documents
- `docs/findings.md`: the complete results record, with every sensitivity table.
- `docs/decisions.md`: D1–D13 with full reasoning.
- `docs/research_log.md`: day-by-day record, including failed approaches and fixes.
- `docs/feasibility_memo.md`: the pre-Phase-1 feasibility checks.

## References
- Beirle, S. et al. (2011). Megacity emissions and lifetimes of nitrogen oxides probed from space. *Science* 333, 1737–1739.
- Beirle, S. et al. (2019). Pinpointing nitrogen oxide emissions from space. *Science Advances* 5, eaax9800.
- Nassar, R. et al. (2017). Quantifying CO₂ emissions from individual power plants from space. *Geophysical Research Letters* 44, 10045–10053.
- Xie et al. (2026). Shandong TROPOMI NO₂ + Differential Evolution inversion. *Remote Sensing* (base paper; full citation per the proposal).
- Crippa, M. et al. EDGAR v8 (JRC); Oda, T. & Maksyutov, S. ODIAC; Copernicus Sentinel-5P TROPOMI; ECMWF ERA5; NASA OCO-2/OCO-3 Lite v11.
