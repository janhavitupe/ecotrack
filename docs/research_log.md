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
- Docs synced after the OCO result: `findings.md` §4.7 + key finding 12 + limitations + next steps; D11 added; D8 annotated with its outcome; an update box added to the feasibility memo (it had promised OCO would test the NOx:CO₂ ratio); README stage and layout updated.

## 2026-09-24 (D4 — TROPOMI CO)
- User instruction: **always update the docs** in the same turn as each result (saved as a standing rule).
- `tropomi_cube.py` generalised to `--product co` (GEE `COPERNICUS/S5P/OFFL/L3_CO`, band `CO_column_number_density`; pre-filtered qa > 0.5, **no cloud_fraction band**; our extra QC: solar zenith ≤ 70°). Settings in `configs/study.yaml → tropomi_co`. Test month January 2020: 24 overpasses, 95% valid, median 0.037 mol/m².
- **Terrain problem found:** the January CO maximum sits in the NW corner (Konkan, near sea level), not over Pune. A total column scales with the air mass above the ground; the Pune plateau (~560 m) vs Konkan (~0 m) gives a ~6% pattern, larger than Pune's expected ~2% CO signal. Fix: SRTM elevation on the cube grid (`src/ecotrack/acquire/dem.py`: 14–1180 m, median 642 m), smoothed to the ~5 km CO footprint; column / exp(−z/H), H = 8.4 km (sensitivity 7.5 / 9.5 km).
- **CO step estimator** (`src/ecotrack/inversion/run_co_ratio.py`): terrain-normalise → remove each day's box median → remove each pixel's long-term mean (drops every static pattern, including the city's direction-averaged dome) → rotate by wind → step = L(20–40 km downwind) − L(20–40 km upwind) → E_CO = step / ⟨1/w⟩.
  - Synthetic test (`tests/test_co_step.py`): inert source 100 mol/s recovered as **98.6 (−1.4%)**, with a static terrain pattern larger than the plume; **terrain only → −0.8 mol/s (≈0)**.
- EDGAR v8.1 CO downloaded (totals 2019–22: 342–359 kt in the box; 2021 sectors). **Assumption corrected:** I had grouped road transport as "high-CO". EDGAR gives Pune road transport a *low* CO:NOx (box: 8.9 kt CO vs 7.8 kt NOx); the high-CO sectors are residential (125 kt CO / 2.7 kt NOx) and industry. The mixing model now groups sectors by EDGAR's own ratios (above the city average = high-CO), not by assumption. Whether EDGAR's low Indian road-transport CO is realistic is itself an inventory assumption to note.
- **TROPOMI CO cube:** 40 months, 907 overpasses (0 errors); 608 windy (2–8 m/s) used.
- **D4 result: the CO plume is detected.** Step 65.0 mol/m → **E(CO) = 6.73 kg/s; CO:NOx = 21.1 mol/mol [95% CI 18.6–23.7]** (NOx from EMG). Clean step across the city (−10 to +20 km), flat downwind plateau; slight decline beyond 40 km, probably across-wind window truncation (makes the step conservative, i.e. low).
  - Robust: H 7.5 / 9.5 km → 21.3 / 20.9; no terrain correction → 19.5; Oct–Jan 21.9 vs Feb–May (fire season) 20.4. No sign of fire inflation.
  - **EDGAR (same 25 km area) CO:NOx = 16.0 → observed is 32% higher.** EDGAR sector CO:NOx (mol/mol) / CO₂:NOx (t/t): industry 9.9 / 115, road transport 1.95 / 174, residential 77.9 / 393, power 0.38 / 284.
  - Scenario check (one sector pair re-split, others at EDGAR shares): **industry vs transport is INFEASIBLE** (would need 153% industry). Feasible: high-CO group vs rest → CO₂:NOx 188 [179–196]; residential vs industry → 180 [170–191] (residential 24% vs EDGAR 13% of pair); residential vs transport → 174 [167–182] (56% vs 33%). **The excess CO requires more residential/biomass-type (high-CO) combustion than EDGAR assumes.**
  - **CO-constrained CO₂:NOx = 181 (95% range 167–196)** vs EDGAR 172 → **city fossil CO₂ 2.99 Mt/yr** (was 2.84 with the EDGAR ratio).
  - **Uncertainty budget revised: 31.5% → 23.1% (1σ).** The base paper's 25% representativeness term is replaced by the CO-scenario half-range (8.1%) plus an assumed 10% for EDGAR's per-sector ratios.
  - Caveats: secondary CO from VOC oxidation in the plume and the EMG +12% NOx bias would both raise the true CO:NOx further (toward more residential and a higher CO₂:NOx); the mixing model trusts EDGAR's per-sector ratios; residential CO₂ here is fossil only (EDGAR's framing), with biomass CO₂ excluded as biogenic.
- Docs updated for D4/D12: findings §4.8 + key finding 13 + D12 row + limitations + next steps + reproduce/outputs; decisions D12; README stage; memo update box.
- **Phase 1 completeness check against the proposal:** 3 items open: (1) IQR outlier removal (step 1) not implemented; (2) DE settings not sensitivity-tested (step 4); (3) Phase 1 report not written. Per-sub-zone line densities → cluster-scale flux divergence is a documented deviation (D1/D10). README corrected from 'Phase 1 complete' to 'substantively complete, 3 items open'; listed in findings §4.9.

## 2026-09-24 (closing Phase 1 open items)
- **IQR outlier removal** (proposal step 1), `src/ecotrack/qc.py`. Three variants were tested on the synthetic plume with 0.5% injected spikes (reference: clean E +11.5%, τ −16.4%; spikes with no filter +10.4% / −15.7%):
  - temporal k=1.5 → E +7.7%, τ −20.8% (distorts the plume)
  - domain k=1.5 → E −4.3%, τ −5.4% (clips the plume core; looks "better" only by accident)
  - local k=1.5 → E +9.8%, τ −15.3% (≈ clean)
- First chose "local" and started the full rerun. **Stopped it: "local" removed 28.96% of REAL pixels** (1.4% synthetic). Cause: GEE's 1 km L3 grid copies each ~3.5 × 5.5 km TROPOMI pixel into several cells, so local deviations are ~0 (median |dev| 0.66 µmol/m², ~2% of signal) except at footprint edges, which the fences flag. The synthetic noise (independent per cell) couldn't show this. **Lesson: check QC removal rates on real data, not only synthetic.**
- Real-data removal rates (150 overpasses): local 29.4% (k=1.5) / 22.0% (k=3) / 13.9% (k=10); domain 4.2% / 0.7%; **temporal 2.4% (k=1.5) / 0.11% (k=3)**.
- **Chosen: temporal, k = 3** (Tukey far-out): 0.11% of real pixels removed; on synthetic data it catches 92% of spikes with a 0.9% line-density change (local 1.8%, domain 7.3%). Config `tropomi.iqr`; applied to NO₂ in `load_cube()`. Tests rewritten (`tests/test_qc.py`, 3 tests); suite 11/11.
- Pre-IQR Phase 1 outputs archived in `outputs/phase1/v1_before_iqr/`. The aborted local-filter run gave E(NOx) 0.527 vs 0.524 kg/s. That shows the inversion is insensitive to the filter, but a filter that removes 29% of the data isn't defensible.
- **Full Phase 1 rerun with the temporal k=3 IQR filter** (`outputs/phase1_rerun_iqr.log`; 0.09% of pixels removed on the full cube):
  - EMG main E(NOx) **0.522 kg/s [0.486–0.555]**, τ 1.67 h [1.55–1.81] (was 0.524 / 1.68). Easterly 0.561, westerly 0.442, 2–4 m/s 0.478, 4–8 m/s 0.506, 100 m 0.456, 10 m 0.347.
  - Flux divergence: corridor 0.120 [0.116–0.125]; r25 0.570; shares 20.8–21.8% across sensitivity runs. Hotspots within 8 km: Pune 0.147, PCMC 0.112.
  - CO₂ (EDGAR ratio) **2.83 Mt/yr ± 31.9%**; wind regime term 10.4 → 11.4%.
  - OCO: β 2.00 ± 1.81 (25 km prior), 1.02 ± 0.94 (10 km prior); upper limits 14.1 / 7.3 Mt/yr unchanged; without the calm date 0.65 ± 1.93.
  - CO: CO:NOx **21.2 [18.7–23.8]**; CO₂:NOx 181 (167–197); **2.98 Mt CO₂/yr ± 23.6%**.
- **DE settings sensitivity (proposal step 4):** 36 fits (NP 150/300 × F dithered[0.5,1]/0.5/0.9 × CR 0.3/0.7/0.9 × 2 seeds), all converged to **E 0.5220 kg/s, τ 1.672 h; spread 1.4 × 10⁻⁶ relative**. The fit's optimum doesn't depend on the optimiser settings (`src/ecotrack/inversion/de_sensitivity.py`; vectorised cost for speed, same algorithm).
- Docs updated: findings (all post-IQR numbers, DE result, D13 row, open-items checklist), README stage, memo box, decisions (D12 numbers note, D13). **Phase 1: only the report remains.**
- **Phase 1 report written** (`docs/phase1_report.md`, for the guide): summary, methods, results with figures, deviations table, limitations, decisions needing sign-off (D8, D11, D12), implications for Phases 2–3, reproducibility appendix. **Phase 1 complete**, pending the guide's sign-off on D8/D11/D12. README and findings §4.9/§8 updated.
- **Learning guide written** (`docs/guide/`, 11 files: start-here, big picture, science basics, data A–Z, tools/setup, feasibility steps, Phase 1 methods with worked examples on real numbers, 25 mistakes/fixes, a 3-level replication walkthrough with expected values, glossary, 28 viva Q&As). Requested by the user to be able to understand and replicate the project independently. Linked from the README.

## 2026-10-01
- Guide chapter 11 added (`docs/guide/11_code_walkthrough.md`): how to read the code (start from `run()`), the file-level data-flow diagram, an 8-session reading order, hands-on REPL snippets, tracing the headline number back to its source, common code patterns. Linked from `00_START_HERE.md`.
- **Phase 2 started.** GEE availability checked: VIIRS monthly night lights (`NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG`, `avg_rad` + `cf_cvg`, to 2026-08), Sentinel-2 SR harmonized (6 images over Pune in January 2021), TROPOMI HCHO and O₃ L3 (the annual VIIRS V22 query returned nothing for 2021; the monthly product is used). → **D14:** chemistry proxy = TROPOMI HCHO + ERA5 temperature/radiation (TROPOMI O₃ is a stratosphere-dominated total column).
- **1 km grid built** (`src/ecotrack/grid.py`, config `phase2`): **268 cells** (C1 91, C2 63, C3 114), 268 km² vs a 269 km² corridor (D15).
- **Grid layers from GEE** (`src/ecotrack/acquire/grid_layers_gee.py`): monthly VIIRS radiance, TROPOMI HCHO, ERA5 t2m and solar radiation at 07 UTC; seasonal Sentinel-2 NDVI/NDBI (SCL-masked median).
  - **Bug, caught on the first months:** VIIRS and HCHO came back NaN for all 268 cells, while ERA5 worked. For a *single-band* image, `reduceRegions(mean)` names the output property `mean`, not the band name. Fix: `ee.Reducer.mean().setOutputs(names)`. Bad rows deleted; rerun started.
- **OSM roads** (`src/ecotrack/acquire/roads_osm.py`): road length per cell by class (major / mid / minor). The first run failed: Overpass refused 0.1° tiles 4 times (rate limit/timeout under load). A single small test query returned 200 afterwards → tiles 0.05° with 5 s pauses; rerun started. Assumption noted: today's OSM map is used for all study years.
- GEE band-name fix confirmed: 2019-10 → VIIRS median 14.2 nW/cm²/sr, HCHO 1.74e-4 mol/m², t2m 27.9 °C, no missing cells.
- OSM roads failed again at 0.05° tiles (repeated 504 Gateway Timeout from overpass-api.de; 4 tiles done). The downloader now **caches each tile** (`data/interim/osm_road_tiles/`, resumable) and **rotates across mirrors** (overpass-api.de, overpass.kumi.systems, overpass.private.coffee). Rerunning, with up to 3 passes.
- Feature-table builder written (`src/ecotrack/features.py`): cell × month table v1 with 16 features + `ref_*` inventory columns (EDGAR/ODIAC: comparison only, never features; D2/§5) + QA (missing audit, histograms, spot checks). Waiting on the GEE and roads layers.
- **GEE grid layers, first full run:** VIIRS and HCHO complete (40 months × 268 cells, 0 missing); the VIIRS median rises 15.6 (2019) → 23.6 nW/cm²/sr (2024), consistent with growth (possibly also sensor/processing drift, to note). Sentinel-2 complete for 5 seasons (40–47 scenes each; median NDVI 0.28–0.30, NDBI 0.02–0.03).
  - **Bug:** ERA5 t2m/ssrd missing in 7,560 of 10,720 rows. Reducing a 27.8 km raster at its native scale over 1 km polygons leaves most cells with no pixel centre. Fix: sample at 1 km (each cell takes its ERA5 cell value). Monthly layers re-fetched; the buggy file is kept as `layers_monthly_era5bug.csv` to check that VIIRS/HCHO are unchanged.
- OSM: the mirrors also returned 504 on the first attempts; the cached, multi-pass run continues.
- **ERA5 re-fetch at 1 km: 0 missing**; ~16 distinct ERA5 values per month across the corridor; VIIRS and HCHO bit-identical to the first run (max difference 0.0).
- Geofabrik (the alternative OSM source) was also down (502/timeouts) while our internet was fine (Google 200 in 2 s). The OSM infrastructure is struggling today; the cached roads job keeps retrying.
- **Draft feature table built without roads** (`data/processed/feature_table_v1_draft_noroads.csv`): **10,720 rows = 268 cells × 40 months**, 12 of 16 features complete with **0 missing**. Ranges: NO₂ 2.2–10.6e-5 mol/m² (C1 highest, C3 lowest, as in Phase 1); CO_norm 0.033–0.052 (bimodal, seasonal); HCHO 0.7–3.8e-4; VIIRS 1.9–63; NDVI 0.13–0.60; NDBI −0.16–0.19; t2m 23–36 °C; solar 2.2–3.5 MJ/m²/h (≈ 600–960 W/m²). Meteorology is uniform within a month (one ERA5 cell scale). EDGAR ref columns are blocky (~16 distinct values over 268 cells: 0.1° resolution). QA outputs: `outputs/phase2/qa_feature_table_v1.json`, `qa_histograms.png`.
- Fixed a Windows console crash: "→" can't print to a piped cp1252 console; prints switched to ASCII.
- Roads download job hit the background time limit with **9 of ~42 tiles cached** (errors seen: 504 ×9, 429 ×2, read timeouts ×3 across the three mirrors). Switched to **light queries**: one query per road class with `out skel geom` (geometry only; the class is known from the query), cached per tile and class; the 9 full-tile caches are reused. Restarted (resumable).
- **Data dictionary** written (`docs/data_dictionary.md`): every feature-table column with role (ID/context/feature/QA/reference), meaning, source, processing, units and time step; reference columns marked as never features or labels. Linked from the README.
- **Seasonal emissions (Phase 3 groundwork, `src/ecotrack/inversion/run_seasonal.py`):** EMG per Oct–May season (bootstrap 100) + flux-divergence corridor share:
  - E(NOx) kg/s [95% CI]: 2019–20 **0.405** [0.345–0.465] · 2020–21 0.538 [0.459–0.638] · 2021–22 0.568 [0.513–0.653] · 2022–23 0.502 [0.453–0.574] · 2023–24 **0.621** [0.538–0.682]. All R² ≥ 0.97.
  - **Between-season SD 0.081 kg/s vs typical within-season 1σ 0.036 → ratio 2.3: seasons are resolvable**, so Phase 3 labels can vary by season. The corridor share is stable at 19.7–22.8%.
- **COVID lockdown check (preliminary):** EMG for 25 Mar – 31 May 2020 gives 0.062 kg/s vs 0.384 for Mar–May of other years (−84%), but that fit is **unreliable** (R² 0.62, μ at bound, τ 8.8 h): the weak plume degenerates the EMG. Pre-lockdown Oct 2019 – Feb 2020 (0.581) vs Oct–Feb of other seasons (0.625): a normal −7%. The **direction** (a large drop) is clear; the magnitude needs a model-free check (city-minus-rural NO₂ excess by year, including the April–May 2021 Maharashtra restrictions). That check was blocked by the next item.
- **C: drive critically full (76 MB free)** → Windows "insufficient system resources" when starting Python. Found: pip cache 5.1 GB, Temp 6.7 GB, Downloads 3.3 GB. Asked the user to run `pip cache purge` and Disk Cleanup (not deleted by me: user's system outside the project).
- Roads: 12 of 35 tiles complete earlier; the light per-class download is still running (429/504 from servers).
- **Design issue for Phase 3 (to discuss with the guide):** flux-divergence-share labels (D10) are derived from NO₂, which is also a model feature → a circularity similar to D2's, via NO₂ instead of activity proxies. A design note with options is being drafted.
- **COVID check, model-free (confirmed):** city NO₂ excess (≤ 10 km minus a 35–45 km ring), 25 Mar – 31 May: 2020 **7.8** µmol/m², 2021 **21.5**, 2022 27.3, 2023 29.3, 2024 34.3 → **2020 −74%, 2021 −29%** vs the 2022–24 mean. Both lockdown periods are detected, in order of severity; growth 2022→2024 is visible. Added to findings §4.9 (new) and the Phase 3 note.
- **Phase 3 design note** written (`docs/phase3_design.md`, for the guide): label options (activity-weighted, FD-share, CO-based, inventory = ruled out), the NO₂ circularity of FD labels, proposal **D16** (seasonal FD labels + NO₂-independent CO-label test + circularity-aware evaluation), and 4 questions for the guide. Linked from the README; D16 added to decisions and findings.
- Roads: 13 of 35 tiles complete; the job keeps hitting the background time limit and is restarted each time (resumable). C: free space now ~1 GB (still critical; user asked to purge the pip cache).
- C: free space now **6.1 GB** after the user's cleanup (was 76 MB).
- **L-co feasibility (CO flux divergence, `src/ecotrack/inversion/run_co_divergence.py`):**
  - Synthetic, isotropic random winds: raw 97.7/100 at 25 km, terrain-only ≈ 0. **But with Pune's real winds** (mean wind ~1 m/s of 3.4 mean speed): raw 26.6/100 and terrain-only **−70** (terrain × directional mean wind fakes a divergence); **static-pattern removal fixes it: 88.4/100 (−12%), terrain-only −2.5.** Lesson: synthetic tests need the real wind distribution.
  - Real data (748 overpasses): totals 91/150/207/248/262/272 mol/s at 10–35 km (levels off); **25 km 248 mol/s (6.94 kg/s) vs the CO step 240 → 1.03**; bootstrap 217–280; r = 0.75 with the NO₂ FD map (5 km smoothing); **corridor share CO 14.5% [10.9–18.7] vs NO₂ 21.1%**. Main CO peak 18.455 N 73.835 E (central/south Pune); edge peaks are boundary artefacts.
  - Interpretation: L-co is feasible at ~5 km (noisier). Exploratory source-separation hint: corridor CO:NOx ≈ 15 vs the city's 21.2 → industrial corridor (low CO:NOx) vs residential core (high CO). Findings §4.10 (new), D16 update, Phase 3 note §5b + question 2 updated.
- Phase 1 report: addendum §10 added (seasonal resolution, COVID check, CO flux-divergence map) so the guide-facing report isn't incomplete.
- **Midday → annual-mean adjustment (D17, `src/ecotrack/inversion/temporal_adjust.py`):** EDGAR temporal profiles downloaded (`EDGAR_temporal_profiles_r1.xlsx` monthly; `auxiliary_tables.rar` hourly + weekly, extracted with Windows' built-in tar.exe; the folder can't be named `aux`, a reserved Windows name). Overpass hours IST: 12h 34%, 13h 57%, 14h 9%.
  - First run: name-based monthly matching fell back to flat for most sectors and matched AGS to "rice cultivation". **Fixed:** IPCC-code matching (India 1A4 for residential; region 7 otherwise).
  - **F = 1.231** (industry 1.08, road transport 1.60, residential 1.39, power 1.09); **flat residential month profile → 1.197** (EDGAR's India residential profile is heating-shaped: Jan 17.5%, Jul 2.9%).
  - **Annual mean: NOx 13.4–13.8 kt/yr; CO₂ 2.42–2.49 Mt/yr** (CO ratio), 2.30–2.37 (EDGAR ratio). Satellite vs EDGAR NOx: **−36% like-for-like**.
  - Docs: findings §4.11 (new) + key finding 16 + limitations + next steps; D17; Phase 1 report addendum item 4; guide chapter 6 §6.11.
- Roads job killed by the time limit again (15/35 tiles); restarted in the background.
- **Monte Carlo budget (D18, `src/ecotrack/inversion/mc_budget.py`, 200k draws, lognormal):**
  - symmetric: midday CO₂ **2.98 [1.94–4.54]** (68%: −19/+24%); annual **2.45 [1.54–3.90]**; NOx annual 13.5 [9.0–20.4];
  - bias-corrected: annual **2.20 [1.46–3.31]**.
  - ODIAC 11.8 outside the 95% range in both treatments; EDGAR 3.63 inside the symmetric range, outside the bias-corrected one. The medians reproduce the RSS point estimates.
  - Docs: findings §4.12 (new) + key finding 17 + limitations + next steps + reproduce; D18; Phase 1 report addendum item 5; README headline (now annual mean with a 95% range); guide §6.10b.
- **Sloped-background test → a major correction (D19).** EMG sloped vs flat at 60 km: 0.740 vs 0.522 kg/s. Synthetic: both +11–12% (τ −6% sloped vs −16% flat). Real by window: 60 km 0.522/0.740, **45 km 0.591/0.663**, 30 km 0.609/0.651 (flat/sloped). The far-downwind tail holds PCMC/Talegaon (a second source) → the original main fit was biased low ~20%. **Adopted: window ≤ 45 km, sloped background**; the structure spread becomes a budget term; flat-60 km kept as a sensitivity case. Code: optional slope `c` in `emg_model`/`fit_emg` (default flat, so the original tests still describe the original method), `fit_window()` in `run_city`, D19 variants appended to the city results, the budget term in `run_co2`, MC factor in `mc_budget`; a new parametrised test for the D19 configuration (13 tests pass). Pre-D19 outputs archived (`outputs/phase1/v2_before_d19/`). **Full chain rerun started.**
- **First D19 rerun exposed unconstrained fits:** with the 6-parameter (sloped) model, small subsets can make the slope and the plume decay degenerate. Westerly regime: E 1.173 kg/s, τ 0.42 h, bootstrap 0.80–3.96. Season 2023–24: E 0.983, τ 0.75 h, bootstrap 0.75–2.37. The westerly fit inflated the "wind regime" budget term to 43% → total ±52% (spurious). The main fit was healthy (E 0.663 [0.620–0.715], τ 1.09 h, R² 0.998), and the wind-level sensitivity dropped to 0.8% (100 m: 0.673).
  - **Quality rule added (`run_city.fit_subset`):** a sloped fit is *unconstrained* if τ < 0.6 h or its bootstrap 95% range spans > ×2; then the subset is refitted flat over the same window and flagged `fallback_flat`. Run stopped and the full chain restarted.
- **Roads fallback (D20):** OSM at 16/35 tiles after hours of 504/429. **GRIP4** found in the GEE community catalogue (219 segments in a 2 × 2 km test box near Pimpri; GP_RTP 1–5; source year ~2014). `roads_grip.py` computes length per class per cell in Earth Engine in minutes: total median 2.6 km, max 20.7; 145/268 cells with a major road; **minor-road median 0.07 km (sparse)**.
- **Feature table v1 built** (`data/processed/feature_table_v1.csv` + `.meta.json`, road_source = GRIP4): 10,720 rows, 16 features, **0 missing**. The draft-without-roads file was deleted (superseded). The features builder now prefers OSM, falls back to GRIP4, and keeps GRIP as `grip_*` when both exist. Docs: findings §4b, data dictionary, README, D20.
- **D19 full rerun complete** (with the quality rule): main 0.663 [0.620–0.715] kg/s, τ 1.09 h; westerly → flat fallback 0.484; 2023–24 → flat fallback 0.663; seasons 0.434/0.602/0.733/0.666/0.663 (ratio 2.8); FD 25 km 0.787; CO:NOx **16.7 [14.7–18.8]** (EDGAR 16.0); CO₂:NOx **163 (148–180)**; CO₂ midday 3.40 (CO ratio) / 3.60 (EDGAR ratio); RSS 23.0% / 30.9%; annual F 1.197–1.231 → NOx 17.0–17.5 kt, CO₂ 2.76–2.84; **MC annual 2.79 [1.79–4.36]** (bias-corrected 2.51 [1.69–3.69]); EDGAR inside, ODIAC outside; OCO β 0.81 ± 0.74 / 1.57 ± 1.44 (EDGAR β 1.01).
- **DE settings test under D19:** 24 converged fits identical (0.6627); 12 CR = 0.3 runs hit maxiter (6 parameters), within 3% of optimal cost → the script now reports converged-only stats; rerunning.
- **Conclusion withdrawn:** the "more household/biomass burning than EDGAR" interpretation (pre-D19 CO:NOx 21.2) was an artefact of the underestimated NOx.
- **Docs updated for D19:** findings §1 rewritten + new §4.0 (current tables; §4.3–4.12 kept as the pre-D19 record) + decisions/limitations rows; decisions (D19 results, D12 status); Phase 1 report (revision notice, new Summary, addendum item 6); Phase 3 note (seasonal numbers, ratio 163); README headline; guide ch.1, ch.6 (§6.12 + summary table), ch.7 (#26–27), ch.10 (Q5, Q18–Q20, new Q27b).
- Guide ch.8 (replication) updated to the current post-D19 expected outputs and Level 2 hand calculations; ch.6 gets a reading note (§6.5–6.10 use the original numbers to teach the arithmetic) and the summary renumbered to §6.13 with current values.
- DE sensitivity rerun (D19): **24 of 36 converged, E spread 0.0003%**; all 12 unconverged runs used CR = 0.3 (6-parameter model, maxiter reached). Guide ch.6 section order fixed (6.11 D19, 6.12 annual mean, 6.13 summary).
- `data/processed/feature_table_v1.csv` (+ meta) is committed as a frozen deliverable; raw/interim stay ignored. Guide ch.3 updated accordingly.

## 2026-10-04
- **Docs completeness audit** (user asked whether all docs reflect the full process). The core records (research log, decisions D1–D20, findings) were complete; **the learning guide lagged**: written before Phase 2 and the later Phase 1 work, and only patched for D19. Fixed:
  - **new guide chapter 12** (Phase 2 step by step: grid, availability checks, D14, GEE layers + 2 bugs, the roads saga + GRIP4/D20, features, QA, snags);
  - ch.0 (index); ch.3 (HCHO, VIIRS, Sentinel-2, GRIP4, EDGAR CO, EDGAR temporal profiles); ch.4 (new code files, openpyxl, config keys);
  - ch.6 (§6.14 seasons + COVID, §6.15 CO map); ch.7 (mistakes #28–37); ch.9 (~22 new terms); ch.10 (Q29–Q34); ch.11 (full pipeline incl. Phase 2, reading order 10 sessions);
  - findings §9 and Phase 1 report Appendix A gain the newer scripts.
