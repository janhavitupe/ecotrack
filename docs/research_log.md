# EcoTrack — Research Log

One dated entry per working day: what was run, what came out, what broke, what was decided.
This log is the raw material for the Methods chapter.

---

## 2026-09-23
- Study period fixed: October 2019 – May 2024, October–May seasons only (D7).
- Reviewed the proposal and recorded design changes D1–D6 in `docs/decisions.md` (cluster-scale inversion, no overlap between label and feature layers, OCO-3 as independent target, TROPOMI CO, tree models instead of the U-Net, ERA5 hourly).
- Set up the repo: `configs/study.yaml`, the `src/ecotrack` package, feasibility scripts G1–G4.
- Next: run G4, then G2 and G1 (see `docs/week1_checklist.md`).
- Environment: `.venv` (Python 3.11). The C: drive was full, so pip was run with TMP and PIP_CACHE_DIR on D:.
- G4 first pass (Nominatim): 4 of 10 waypoints within 500 m; 6 flagged. Dehu Road is off by 4.4 km: the config point (18.7167, 73.7500) is probably Dehu town, while OSM's Dehu Road cantonment is at about 18.680, 73.734. Also flagged: Talegaon (2.1 km), Nigdi, Chinchwad, Pimpri, Kasarwadi (1.3–1.5 km). Check each on the map before editing `configs/study.yaml`. Corridor area at a 3.5 km buffer: 260 km².
- G2 test, January 2020: 25 of 31 days usable (≥50% of the 221 corridor pixels pass QC). GEE's L3 footprints are loose (439 images returned for one month), so G2 now counts distinct usable days, not images. Fixed an off-by-one where the exclusive end month was also processed. Full-period G2 run started.
- G1 first attempt: the Earthdata login is valid, but GES DISC returns 403 / `error=access_denied`, so the account isn't authorized for the GES DISC archive yet. The search found 195 in-season OCO-3 Lite v11r days for 2019-10 to 2020-05, with a gap from 2019-10-20 to 2019-11-26 (early-mission outage?). G1 now stops after 3 consecutive access errors.
- **G2 result (full period, 40 months): PASS.** Median 26 usable days per month, minimum 13 (October 2019 and October 2020; October is the weakest month, likely late-monsoon cloud). No month below 5. Decision: monthly composites are viable (to be recorded as D8 once G1/G3 are in).
- The GEE `COPERNICUS/S5P/OFFL/L3_NO2` product has **no `qa_value` band**; GEE pre-filters on qa during its HARP L3 conversion. Methods must say our QC is cloud_fraction ≤ 0.3 plus SZA ≤ 70° on top of GEE's built-in qa filter, not qa ≥ 0.7 applied by us. If Phase 1 needs pixel-level qa control, use the L2 swaths from Copernicus Data Space.

## 2026-09-24
- GES DISC access fixed: the account had approved "GESDISC Test Data Archive" (the test server) instead of "NASA GESDISC DATA ARCHIVE".
- **G1, OCO-3 season 2019–20 (195 distinct days scanned):** 72 good-quality soundings inside the corridor, on only **2 days**, both above the 20-sounding "usable" threshold:
  - 2019-10: 25 soundings in **mode 4 = Snapshot Area Map (SAM)**. OCO-3 did a dedicated SAM over the Pune area. Check whether Pune is a regular SAM target; if so, later seasons may add more.
  - 2020-04: 47 soundings in mode 0 = nadir.
  - Quality filtering removes most soundings (1237 near the corridor at any quality vs. 122 good in the bbox).
  - The per-cluster counts add up to more than the corridor total because the 5 km cluster circles overlap and extend past the corridor.
- The OCO-3 progress file had 41 duplicate lines from a restarted run; the summary now counts distinct days.
- Started in background: the full OCO-3 period, the full OCO-2 period, and G3.
- **G3 result (5 seasons): PASS.** NO₂ enhancement over regional background (10th percentile of the regional box):
  - C1 Shivajinagar–Kasarwadi: 2.23–2.38×
  - C2 PCMC: 2.09–2.25×
  - C3 Dehu–Talegaon: 1.67–1.76×
  - All seasons are ≥1.5×, and the ranking is the same every season. Background: 2.5–3.3e-5 mol/m².
  - Caveat: C1 > C2 is consistent with central-Pune spillover. C3's enhancement may partly be PCMC outflow carried downwind. The ratios show there is a signal, not that the clusters can be separated; Phase 1's wind-rotated line densities test whether they can. The 2021–22 composite map was exported to Drive/ecotrack_feasibility for visual inspection.
- OCO-2 G1 run restarted: it had picked only version 11.3r, which covers 2024 only. It now picks the newest version per day (11.2r for 2019–2023, 11.3r for 2024), giving 1,177 in-season days.
- **G1 OCO-3 result (full period, 893 distinct days, 0 failed downloads):**
  - Corridor-only: 236 good soundings over 10 days, of which 6 are usable (≥20). Nothing usable after November 2022.
  - City scale (bbox): **7 strong days with ≥50 good soundings**: 2019-10-14, 2020-12-20, 2020-12-24, 2021-01-01, 2022-01-27, 2022-11-21 (all SAM) and 2020-04-21 (nadir). The 2020-12-20/24 SAMs have more than 1,100 good soundings each in the padded box.
  - **Pune is an OCO-3 SAM target**: SAMs on at least 9 dates between 2019 and 2023. Several were lost to quality filtering (e.g. 2021-05: 427 soundings, 0 good; pre-monsoon cloud).
  - OCO-3 gap confirmed: only 15 in-season days of data after Oct 2023; nothing from Dec 2023 to May 2024.
  - Most good soundings fall outside the 7 km-wide corridor, so corridor-cell counting undersells OCO-3. It is a city-scale instrument here.
- Proposed D8 (see decisions.md), to discuss with the guide.
- Drafted `docs/feasibility_memo.md` (OCO-2 and G4 still pending).
- **ERA5 matched to all 1,028 usable TROPOMI overpasses** (`src/ecotrack/acquire/era5_overpass.py` → `data/interim/era5/overpass_met.csv`). Overpasses are at 06–08 UTC (11:30–13:30 IST); 50 days have two usable orbits.
  - C2 and C3 share one ERA5 0.25° cell, so in practice there is one wind per overpass for the corridor.
  - Median wind speed: 2.5 m/s at 10 m, 3.2 at 100 m, 3.5 at 850 hPa. Median boundary-layer height 1.66 km (10th–90th percentile 1.06–2.94 km).
  - 850 hPa speed classes: 192 calm (<2 m/s), 429 at 2–4, 334 at 4–7, 73 above 7. Enough calm cases for source location and 2–7 m/s cases for the rotation fit.
  - **Wind regimes:** Oct–Mar from E–SE (central Pune upwind of PCMC and C3; pollution carried along the corridor). Apr–May from W–NW (reversed). This supports the G3 caveat that C1 > C2 and C3's enhancement are partly inherited from upwind. It also means each cluster is seen from both sides, which helps separate them in Phase 1. Consider running the inversion separately for the two regimes.
- **G1 OCO-2 result (1,177 days: first pass, plus a retry of the 159 days lost to a network outage; 0 failures after the retry):** only **1 strong day**, 2024-01-23: a glint-mode track crossing C1 and C2, with 62 good soundings in the corridor and 93 in the bbox. It usefully falls in the 2023–24 season, when OCO-3 has no data. As expected, OCO-2's narrow track rarely crosses the corridor. D8's direct-CO₂ set becomes 7 OCO-3 dates + 1 OCO-2 transect = 8.
- G4 map tool: `python -m ecotrack.feasibility.g4_map` → `outputs/feasibility/g4_map.html`. It shows draggable waypoints, OSM positions, the corridor, the clusters and 259 OSM industrial-land polygons.
- **MIDC Bhosari is 100% inside the current 3.5 km corridor**, so no buffer change is needed for it. The Chakan industrial area is outside (off-corridor, to the NE); it is a possible upwind source on NE-wind days, to note in Limitations.
- **G4 done → D9.** The user accepted OSM place centres for all 10 waypoints via the map tool. Built the corridor from the highway-snapped centreline plus Talegaon MIDC (269 km², one polygon). Extended the bbox to 73.62–73.89 E, 18.50–18.82 N. Rerunning G1 summaries, G2, G3 and ERA5 on the new corridor.
- **Rerun on the D9 corridor (269 km², 230 TROPOMI pixels):**
  - G2: unchanged (median 26 usable days/month, min 13).
  - G3: C1 2.22–2.37×, C2 2.10–2.25×, C3 1.71–1.81× (C3 slightly up: it now includes Talegaon MIDC).
  - OCO-3: unchanged (6 corridor days, 7 bbox days).
  - OCO-2: 60 corridor soundings on 2024-01-23 (was 62).
  - ERA5: 1,031 overpasses.
  The map step first failed with an Overpass 504; regenerated on retry, now with the centreline drawn. Memo updated to final draft.

## 2026-09-24 (Phase 1 start)
- TROPOMI cube: 1,004 usable overpasses (Oct 2019 – May 2024), 0.01° grid, 90 × 95 px over 73.35–74.30 E, 18.15–19.05 N (`src/ecotrack/acquire/tropomi_cube.py`). All matched to ERA5 within 30 min.
- **Synthetic recovery test** (`tests/test_emg.py`, 2 seeds, 200 simulated overpasses): E recovered **+11–12%**, τ **−16–17%**, R² 0.99. Separated the bias: across-wind window truncation ~2%, averaging days with different wind speeds ~6%, remainder (2 km binning near the source) ~4%. This is a measured method bias; it goes into the uncertainty budget.
- **City-scale EMG inversion** (`src/ecotrack/inversion/run_city.py`, 850 hPa wind, 2–8 m/s, DE with NP 300):
  - Source (calm composite max, n = 187): **18.485 N, 73.855 E**, central Pune (Swargate/Camp), ~2 km south of the corridor tip. PCMC shows as a secondary NO₂ ridge along the corridor.
  - **Main: E(NOx) = 0.52 kg/s [95% CI 0.49–0.56] (≈16.5 kt/yr at midday rate), τ = 1.7 h [1.55–1.82], x₀ = 25 km, w = 4.1 m/s, R² 0.99, n = 781.**
  - Sensitivity: easterly regime 0.56 kg/s (τ 1.4 h), westerly 0.45 (τ 2.1 h); wind 2–4 m/s 0.48, 4–8 m/s 0.51; wind level 100 m 0.46, 10 m 0.35. **The wind level is the largest single sensitivity** (10 m surface wind is too slow for a ~1 km-deep plume, so 850 hPa is the physically preferred level).
  - The line density rises again 50–60 km downwind: a secondary source (PCMC/Talegaon up the corridor in E-SE wind). A single EMG can't separate it, so cluster attribution needs flux divergence (D1).
- **Flux-divergence emission map** (`src/ecotrack/inversion/divergence.py`, `run_divergence.py`; 968 overpasses, 850 hPa wind, τ = 1.68 h from EMG, background = 10th percentile of the mean column, NOx/NO₂ 1.32):
  - Synthetic test (`tests/test_divergence.py`): source total recovered at **−4%** (0.48 vs 0.50 mol/s), stable across 15/25/35 km radii; no spurious source at the box corners (|total| < 10% of E).
  - **Two distinct hotspots resolved:** central Pune (18.485 N, 73.855 E; matches the EMG calm-max source exactly) and **PCMC (18.625 N, 73.795 E, Pimpri–Chinchwad core, inside the corridor)**, 16.7 km apart. PCMC's peak intensity is 73% of Pune's. Within 8 km of each peak: Pune 0.147 kg/s, PCMC 0.111 kg/s.
  - Zone totals (kg/s NOx, 95% bootstrap CI): Pune core outside the corridor 0.168 [0.163–0.177]; C1 0.057 [0.056–0.060]; C2 0.037 [0.035–0.039]; C3 0.025 [0.023–0.028]; **corridor 0.119 [0.115–0.124] (~3.8 kt/yr midday rate)**. The corridor zones are only 1–2 TROPOMI pixels wide, so emissions smear across zone edges; circle totals around the hotspots are the fairer comparison.
  - **Consistency with EMG:** total within 25 km of the source = 0.57 kg/s vs EMG 0.52 (+9%). The cumulative total does **not** plateau (0.47 at 20 km → 0.70 at 35 km). Decomposition: the flux term plateaus at ~0.16 kg/s, but the lifetime (sink) term keeps growing (~70% of the 25 km total): NO₂ 30–35 km out is still ~24% above the p10 background. **Absolute FD totals depend on τ and the background choice.**
  - Sensitivity (corridor): τ ×0.7 → 0.155; τ ×1.3 → 0.100; τ/0.84 (synthetic-bias corrected) → 0.106; background p5/p25 → 0.123/0.113; wind level 100 m → 0.119.
  - Shares are robust: corridor share of the 25 km total 0.206–0.216 across all sensitivity runs (absolute 0.100–0.155 kg/s). Recorded in D10.
- **Inventories downloaded** (both clipped to the cube box; global files deleted):
  - EDGAR v8.1 AP NOx + v8.0 GHG fossil CO₂ (same FT2022 activity data): totals 2019–2022 plus all sectors for 2021 (`src/ecotrack/acquire/edgar.py`).
  - ODIAC v2024 via the US GHG Center raster API: 35 Oct–May months, Oct 2019 – Dec 2023 (`src/ecotrack/acquire/odiac.py`). Units confirmed from the GHG Center user notebook: **tonnes C per 1 km cell per month** (×44/12 for CO₂).
  - Whole-box totals: EDGAR ≈ 7 Mt CO₂/yr vs ODIAC ≈ 18 Mt CO₂/yr (2.6×).
- **NOx → CO₂ and inventory comparison** (`src/ecotrack/inversion/run_co2.py`; comparison area = within 25 km of the source):
  - Satellite NOx 16.5 kt/yr (midday rate) [95% CI 15.5–17.6] vs **EDGAR NOx 21.1 kt/yr → satellite/EDGAR = 0.78**. A midday rate would normally exceed the daily mean, so this points to EDGAR NOx being high for Pune, or to the EMG background absorbing diffuse emissions. Unresolved.
  - EDGAR CO₂/NOx ratio **172** (2019 176, 2020 166, 2021 171, 2022 176); combustion-only 175. By sector (2021): industry 115, road transport 174, residential/commercial 393, power 284. **The city ratio depends strongly on the sector mix.**
  - **Satellite fossil CO₂ = 2.84 Mt/yr (midday rate) ± 32% (1σ) → 1.95–3.74 Mt/yr.** EDGAR 3.63 Mt/yr; **ODIAC 11.8 Mt/yr (3.2× EDGAR in the same area)**. The satellite CO₂ is not independent of EDGAR (it uses EDGAR's ratio); it differs from EDGAR only through the NOx difference.
  - Zone CO₂ via flux-divergence shares (Mt/yr): Pune core 0.84, C1 0.29, C2 0.18, C3 0.13, **corridor 0.60** (share 20.9%). Inventory corridor totals: EDGAR 1.15, ODIAC 4.04 Mt/yr.
  - **Uncertainty budget (1σ):** ratio representativeness 25% (the base paper's value) · EMG synthetic bias 12% (systematic, kept uncorrected) · wind regime 10% · NOx/NO₂ 7.6% · wind level 6.3% · bootstrap 3.3% · EDGAR ratio year/choice 3.1% → **31.5% total**. The 25% term may be optimistic given sector ratios of 115–393; the D8 OCO-3 comparison tests exactly this term.
- **D8 check, exploratory** (`src/ecotrack/inversion/run_oco_check.py`): plume-model scaling of OCO-3/OCO-2 XCO₂ on the 8 dates. The emission prior is the flux-divergence map scaled to 2.84 Mt/yr, with a Gaussian column plume carried by ERA5 850 hPa wind at the OCO overpass hour; weighted regression with a linear background gradient.
  - Overpass times vary widely (08:52–16:04 IST; ISS orbit). 167–917 good soundings within 45 km per date; single-sounding scatter 0.5–1.1 ppm.
  - **The predicted Pune plume is tiny:** max 0.02–0.07 ppm on most dates (prior spread over 25 km), 0.04–0.15 ppm if confined to 10 km. The one exception is 0.2–0.4 ppm on the near-calm OCO-2 date (0.6 m/s wind, where the steady-state plume model isn't valid).
  - **Combined scale factor β:** 2.00 ± 1.80 (25 km prior) / **1.01 ± 0.93 (10 km prior)**; β = 1 means agreement with the NO₂-based estimate. Between-date reduced χ² 11–14: the dates disagree far more than their error bars allow.
  - **Not a detection.** SNR ≈ 1. The maps show swath-to-swath stripes of 0.5–1 ppm on the SAM dates (retrieval artefacts), 10–20× the predicted plume. The 2020-12-24 SAM shows a positive patch along the predicted plume (β 4.95 ± 0.84) but it can't be separated from the swath pattern.
  - **Upper limits (95%, one-sided):** E < 7.3 Mt/yr (10 km prior) to 14.1 Mt/yr (25 km prior); without the near-calm OCO-2 date, 10.8–28 Mt/yr. The near-calm date carries most of the weight: dropping it doubles the uncertainty.
  - **Detection threshold (3σ) with these 8 dates: ~8–15 Mt CO₂/yr.** Pune's ~3–4 Mt/yr (satellite or EDGAR) is below it.
  - vs inventories: EDGAR (β 1.28) is consistent in every variant. ODIAC (β 4.14) is 3.3σ off with the 10 km prior and all dates, but only 1.2σ with the 25 km prior. **A tentative hint that ODIAC is too high, not robust.**
  - A possible improvement: per-swath offset terms in the regression, to absorb the stripe artefacts.
