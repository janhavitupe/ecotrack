# EcoTrack — Design Decisions

Each entry records what changed from the original proposal, and why. These go almost
unchanged into the Methods and Limitations chapters. Add new entries; never rewrite old
ones. If a decision is reversed, add a new entry that says so.

---

## D1 — Invert NO₂ at cluster scale, not per waypoint (2026-09-23)
**Proposal:** a line-density plus Differential Evolution inversion per sub-zone (Khadki, Pimpri, Chinchwad, …).
**Problem:** TROPOMI pixels are about 3.5 × 5.5 km. Pimpri and Chinchwad are about 1.4 km apart, and Akurdi and Nigdi under 1 km. The wind-rotation line-density method (Xie et al.) was validated on whole cities, so it can't separate sources closer together than a pixel.
**Decision:** invert three clusters (C1 Shivajinagar–Kasarwadi, C2 PCMC, C3 Dehu Road–Talegaon; see `configs/study.yaml`). If gate G3 shows the clusters can't be told apart from background, fall back to a single Pune+PCMC source. Test the flux-divergence method (Beirle et al., 2019) as a second estimator for multiple nearby sources.
**Consequence:** the 1 km map is a downscaling of cluster totals. The report must say this plainly.

## D2 — Label layers and feature layers must not overlap (2026-09-23)
**Problem:** the proposal spreads CO₂ labels over the grid using nighttime lights, NDBI and road density, then gives the same layers to Experiment D as features. D would "win" because the model learns the allocation weights back, not because the layers carry information about emissions. ODIAC doesn't help as an independent check: it spreads emissions using nighttime lights.
**Decision:** a label built from proxy set P may not use P as model features. The code enforces this with a test. Any experiment that needs a proxy in both places is run with a label built from a different proxy set, and the comparison is reported.

## D3 — OCO-3 XCO₂ enhancement as an independent observed target (2026-09-23)
**Decision:** besides the inversion-derived label (L1), use OCO-3 XCO₂ enhancement above a local background on usable overpass days as a second target (L2). L2 is an actual observation, not derived from an inventory. It is the project's only independent validation, even though the sample is small. How much weight it carries depends on gate G1.
**Consequence:** Experiment B is evaluated only on cells and days with real soundings. Interpolated XCO₂ is not used as a per-cell feature, because a mostly invented feature can't show whether OCO-3 adds value.

## D4 — Add TROPOMI CO as a source-type tracer (2026-09-23)
**Problem:** there is no per-cell ground truth separating industrial from traffic emissions.
**Decision:** add TROPOMI CO. The CO:NO₂ ratio differs between traffic and industrial combustion, so it gives physical evidence of source type. Source separation stays an exploratory result, not a validated one.

## D5 — Drop the U-Net; use tree models with honest statistics (2026-09-23)
**Problem:** the corridor has about 230–300 cells × about 40 in-season months, and the data are strongly autocorrelated. Spatial block CV leaves only a few independent blocks.
**Decision:** XGBoost and Random Forest, with a ridge-regression floor. Validate with spatial blocks (`GroupKFold`) and leave-one-season-out. Report bootstrap confidence intervals on the differences between experiments, not point R² alone. Add a shuffled-feature-group negative control.

## D6 — Meteorology from ERA5 hourly (2026-09-23)
**Decision:** use ERA5 hourly wind and boundary-layer height, matched to the TROPOMI overpass (~13:30 local), as the primary source. Its resolution is finer than MERRA-2. MERRA-2 and CAMS are used only for the chemistry proxies.

## D7 — Study period October 2019 – May 2024, October–May seasons only (2026-09-23)
**Decision:** five dry seasons. This starts after TROPOMI's pixel-size change (August 2019) and avoids monsoon cloud gaps. Limitation: no monsoon season, so no full annual cycle.
**To check in G1:** gaps in OCO-3 operations during this window. The instrument was reportedly stowed on the ISS for part of 2023–24; confirm this from the sounding record, not from memory.

## D8 — Use OCO-3 at city/cluster scale, on 7 dates: independent check on the NO₂-derived CO₂ (PROPOSED 2026-09-24, confirm with guide)
**Evidence (G1):** 6 usable corridor days, but 7 strong days (≥50 good soundings) at city scale, 6 of them SAMs. Pune is a SAM target. No data after November 2023.
**Decision:** OCO-3 is **not** a per-cell ML feature or training target. It is too sparse for that; this settles the question D3 left open. Instead, for each of the 7 dates:
1. Estimate the XCO₂ enhancement over Pune/PCMC relative to an upwind background taken from the same SAM.
2. Convert it to a CO₂ emission estimate with a cross-sectional flux (mass-balance) calculation, using ERA5 wind at the overpass time.
3. Compare it with the Phase 1 NO₂-derived CO₂ for the same dates and clusters.

This is the project's one comparison with a direct, non-inventory CO₂ observation, and it tests the base paper's largest error term: the NOx:CO₂ conversion.
**Consequence for the ablation:** Experiment B becomes "does an OCO-3 constraint on cluster totals change the gridded map?", evaluated on these dates, rather than a per-cell feature comparison. Report n = 7 honestly; this is a case study, not a statistic.

**D8 status (2026-09-24, after the exploratory run):** the mass-balance check found **no detectable Pune plume** (predicted 0.02–0.15 ppm vs 0.5–1 ppm noise and swath artefacts). OCO therefore does **not** test the NOx:CO₂ ratio as hoped; see **D11** for the proposed reframing (consistency + upper limit + detection threshold).

**D8 addendum (2026-09-24):** OCO-2 adds one strong date, 2024-01-23: a glint track crossing C1 and C2 with 62 good soundings in the corridor, in the season OCO-3 misses. It is treated as a transect (upwind vs. downwind along the track), not a map. Direct-CO₂ dates: n = 8.

## D9 — Corridor built from the highway centreline plus Talegaon MIDC (2026-09-24)
**Problem (G4):** 6 of the 10 proposal waypoints were more than 500 m from their OpenStreetMap positions; Dehu Road was 4.4 km off. OSM place centres are neighbourhood centroids, not points on the road, so a line through them zigzags (e.g. Nigdi's centre lies east of Akurdi's).
**Decision:**
- **Waypoints** = OSM place centres, used only as labels and cluster centres.
- **Corridor centreline** = each waypoint snapped to the nearest point of the OSM-tagged Old Pune–Mumbai Highway, in road order: 30.2 km, a median 200 m from the actual highway. Talegaon stays at its place centre because OSM's highway tagging stops near Dehu Road.
- **Corridor** = centreline ± 3.5 km, **plus a 2.5 km circle over Talegaon MIDC**. The MIDC lies ~5 km north of Talegaon town, 1.5–1.8 km outside the buffer, and the proposal names it as a source. The radius is 2.5 km because a 2 km circle left a gap and the corridor would have been two separate pieces.
- Result: one polygon, **269 km²**. MIDC Bhosari 99% inside; Talegaon-area industrial land 77% inside (the rest is small scattered units to the SW).
**Not included:** the Chakan industrial area (off-corridor, to the NE). It is a possible upwind source on NE-wind days; note in Limitations.
**Rejected alternative:** a routed driving line (OSRM) through the snapped points. It gave 42 km with only 46% on the highway (U-turns on the dual carriageway).
First-corridor results are archived in `outputs/feasibility/v1_waypoint_corridor/`; G1 summaries, G2, G3 and ERA5 were rerun on the D9 corridor.

## D10 — Flux divergence for spatial attribution; EMG for the city total (2026-09-24)
**Evidence:** the single-source EMG fits well (R² 0.99), but its line density rises again 50–60 km downwind (PCMC up the corridor), so it can't separate sources. The flux-divergence map resolves two hotspots 16.7 km apart (central Pune; Pimpri–Chinchwad) and agrees with the EMG city total within 9% at 25 km. However, its absolute totals are dominated (~70%) by the lifetime term and depend on the background choice.
**Decision:**
- **City total** = EMG estimate (0.52 kg/s NOx), the base paper's method, with bootstrap CI and the synthetic bias (+12%) in the uncertainty budget.
- **Spatial distribution** = flux-divergence map, used for **shares** between zones rather than absolute totals: corridor share, cluster shares, and the Pune-core vs PCMC ratio. Verified across the 6 sensitivity runs (τ ×0.7/×1.3/÷0.84, background p5/p25, 100 m wind): corridor share of the 25 km total 0.206–0.216 (±2.5%), C2/Pune-core ratio 0.212–0.231, while the absolute corridor total ranges 0.100–0.155 kg/s (−16% to +30%).
- Report both estimators side by side. The agreement at matched area is the validation; the non-plateau is a stated limitation.
**Consequence for Phase 3 (labels):** the city total is distributed to 1 km cells using flux-divergence shares, in place of (or compared with) the activity-weighted allocation in the proposal. That also helps D2: labels no longer depend on nighttime lights, NDBI or road density, which can therefore stay as model features without circularity.

## D11 — OCO-3/OCO-2 cannot independently constrain Pune's CO₂; reframe D8 as a detectability result (2026-09-24, PROPOSED)
**Evidence (exploratory D8 run):** the predicted Pune plume is 0.02–0.15 ppm, against 0.5–1.1 ppm sounding scatter and 0.5–1 ppm swath-stripe artefacts on the SAM dates. The combined scale factor is 1.01 ± 0.93 (10 km prior) or 2.00 ± 1.80 (25 km prior), with between-date χ² 11–14. There is no detection, and the result leans heavily on one near-calm OCO-2 date where the plume model is invalid.
**Decision (proposed):** report the OCO analysis as
1. **consistency:** the OCO data agree with the NO₂-based and EDGAR estimates;
2. **an upper limit:** E < 7–14 Mt CO₂/yr (95%, depending on the spatial prior);
3. **a detection threshold:** ~8–15 Mt/yr for 8 dates;
4. a tentative, non-robust hint that ODIAC's 11.8 Mt/yr is too high.

It is **not** an independent emission estimate and does **not** validate the EDGAR CO₂:NOx ratio. This answers the proposal's primary research question honestly for this corridor: *direct CO₂ observation from current satellites adds a bound, not a measurement, for a city of Pune's size.* The proposal's §11 explicitly counts such a result as valid.
**Consequence:** the NOx → CO₂ ratio remains the dominant uncertainty and is untested by observation. The best remaining lever is TROPOMI CO (D4) to constrain the sector mix, and hence which sector ratio (115–393) applies. Worth trying before finalising: per-swath offsets in the OCO regression.

## D12 — Use the TROPOMI-CO-constrained CO₂:NOx ratio (2026-09-24, PROPOSED)
**Evidence (D4 run):** the TROPOMI CO step over Pune is clearly detected: CO:NOx = 21.1 mol/mol [18.6–23.7], robust to terrain handling and season, and 32% above EDGAR's 16.0 for the same area. Re-splitting sector pairs shows the excess can't come from industry replacing transport (infeasible); it needs more high-CO (residential/biomass-type) combustion. All feasible scenarios give CO₂:NOx 167–196 (central 181) instead of EDGAR's fixed 172 or the unconstrained sector span 115–393.
**Decision (proposed):** the CO₂ conversion uses the CO-constrained ratio (181; 95% range 167–196). The base paper's 25% representativeness term is replaced by the scenario half-range (8.1%) plus an assumed 10% for EDGAR's per-sector ratios. **Headline: 2.99 Mt CO₂/yr ± 23% (1σ, midday rate)**; the EDGAR-ratio value (2.84 ± 32%) is kept alongside for comparison.
**Why it matters:** this is where multi-source data measurably improve the estimate (primary research question): adding TROPOMI CO cuts the dominant error term by about two thirds and the total from 31.5% to 23.1%. It also answers D11: OCO couldn't test the ratio, but CO can constrain it.
**Caveats:** trusts EDGAR's per-sector CO:NOx and CO₂:NOx ratios; secondary CO from VOC oxidation and the EMG NOx bias would both push the true ratio higher; single-pair mixing is a simplification.
**D4 status:** done. TROPOMI CO works as a source-type tracer for Pune.

**D12 numbers after IQR filtering (2026-09-24):** CO:NOx 21.2 [18.7–23.8]; CO₂:NOx 181 (167–197); **2.98 Mt CO₂/yr ± 23.6%** (EDGAR-ratio variant 2.83 ± 31.9%).

## D13 — IQR outlier removal: per-pixel time series, Tukey k = 3 (2026-09-24)
**Proposal:** "IQR outlier removal" (Phase 1 step 1), method not specified.
**Evidence:** on the synthetic plume with injected spikes (`tests/test_qc.py`):
- "domain" (per-overpass whole-box fences) clips the plume core (line density −7%);
- "local" (deviation from a 7 px median) looked best;
- "temporal" k = 3 catches 92% of spikes with a 0.9% line-density change.

On **real** data, "local" removed **29%** of pixels (22% even at k = 3). GEE's 1 km L3 grid copies each ~3.5 × 5.5 km TROPOMI pixel into several cells, so local deviations are ~0 except at footprint edges, which the fences flag.
**Decision:** "temporal", k = 3 (Tukey far-out), applied to NO₂ when the cube is loaded. It removes **0.09%** of real pixels. Every Phase 1 result moved < 2% (city NOx 0.524 → 0.522 kg/s). Pre-filter results are archived in `outputs/phase1/v1_before_iqr/`.
**Lesson for the Methods chapter:** QC choices were checked for removal rates on real data, not only on synthetic data.

## D14 — Chemistry proxy: TROPOMI HCHO + ERA5 temperature/radiation, not MERRA-2/CAMS O₃ (2026-10-01)
**Proposal:** "Atmospheric chemistry proxy: O₃, VOC-related fields (MERRA-2 / CAMS)".
**Problem:** reanalysis chemistry is coarse (~0.5°), much coarser than the 1 km grid. TROPOMI's O₃ product (checked in GEE: `COPERNICUS/S5P/OFFL/L3_O3`) is a *total* column dominated by the stratospheric ozone layer, so it carries almost no city-level photochemical information.
**Decision:** use **TROPOMI tropospheric HCHO** (formaldehyde, the standard satellite indicator of reactive VOCs; `COPERNICUS/S5P/OFFL/L3_HCHO`, same QC and grid as NO₂) plus **ERA5 2 m temperature and surface solar radiation** at the overpass (the photochemistry drivers). These are the same pipeline and resolution as the other satellite layers.
**Caveat:** HCHO is noisy for single overpasses, so monthly means are used; it's a proxy, not a chemistry model (proposal §9 already says so).

## D15 — The 1 km grid: UTM 43N squares, kept if ≥ 50% inside the corridor (2026-10-01)
**Decision:** 1 km × 1 km squares in UTM 43N, aligned to whole kilometres; a cell is kept if ≥ 50% of its area is inside the D9 corridor. **268 cells** (C1 91, C2 63, C3 114 by nearest waypoint), total 268 km² vs a corridor of 269 km². Each cell records its fraction inside the corridor, its cluster, and its distance to the Phase 1 source. Built by `src/ecotrack/grid.py` → `data/interim/grid/cells.csv` / `cells.geojson`.
**Why UTM:** cells are true 1 km² everywhere, so per-km² densities (roads, emissions) are comparable across cells.

## D16 — Phase 3 labels: seasonal flux-divergence labels + an NO₂-independent CO test + circularity-aware evaluation (2026-10-01, PROPOSED)
**Evidence:** seasonal city NOx is resolvable (between/within-season ratio 2.3); the corridor share is stable (19.7–22.8%); monthly fits are too noisy.
**Problem:** D10's flux-divergence-share labels are derived from NO₂, which is also a feature → circular for Experiment A, just as the proposal's activity-weighted labels are circular for Experiment D.
**Proposal:**
1. Primary label = seasonal city CO₂ (EMG × 181) × multi-year FD share.
2. Test a CO-flux-divergence label (independent of NO₂).
3. Remove each label's construction inputs from its features, or report that experiment as a "construction baseline".
4. Evaluate on spatial blocks, cluster hold-out, aggregated seasonal totals, and season-to-season change.

Full note: `docs/phase3_design.md`. **Awaiting the guide.**

**D16 update (2026-10-01): L-co feasibility test passed** (`run_co_divergence.py`). Static-pattern removal is required (terrain × directional mean wind otherwise fakes −70 mol/s). Real data: 25 km total 248 mol/s vs the CO step 240 (1.03); r = 0.75 with the NO₂ map; corridor share 14.5% [10.9–18.7] vs 21.1% for NO₂. So the CO label is feasible at ~5 km scale, and the two tracers place different shares in the corridor (an exploratory industrial-vs-residential signal).

## D17 — Report the annual-mean equivalent alongside the midday rate (2026-10-01)
**Problem:** the satellite rate is a midday (11:30–13:30 IST), October–May rate, while inventories are annual means, so comparisons weren't like-for-like (a Phase 1 limitation).
**Decision:** convert with E_annual = E_observed / F, where F = Σ sector NOx share × overpass-hour factor × weekday factor × Oct–May month factor. The factors come from the EDGAR temporal profiles (Crippa et al., 2020), matched on IPCC codes (India residential, region 7 otherwise), weighted by our real overpass-time, weekday and month distribution. **F = 1.231** (1.197 with a flat residential month profile, since EDGAR's India residential profile is heating-shaped and Pune mostly cooks). **Annual mean: NOx 13.4–13.8 kt/yr; fossil CO₂ 2.42–2.49 Mt/yr** (CO-constrained ratio). Both are reported; the satellite-vs-EDGAR NOx gap becomes −36% like-for-like. Code: `src/ecotrack/inversion/temporal_adjust.py`.

## D18 — Monte Carlo uncertainty with explicit handling of the known method bias (2026-10-01)
**Problem:** the RSS budget assumes independent, symmetric Gaussian errors and treats the EMG's *known* +11–12% overestimate as a symmetric uncertainty.
**Decision:** a 200,000-draw Monte Carlo through the full chain (bootstrap E_NOx; wind level/regime; NOx/NO₂; CO-constrained CO₂:NOx; per-sector 10%; EDGAR year; temporal factor F for annual means), with lognormal multiplicative errors (`src/ecotrack/inversion/mc_budget.py`). The **headline** keeps the symmetric bias treatment (conservative): **annual 2.45 Mt CO₂/yr [95%: 1.54–3.90]; midday 2.98 [1.94–4.54]**. The **bias-corrected** variant (÷ 1 + b, b ~ N(0.115, 0.03)) is reported as a sensitivity: annual 2.20 [1.46–3.31].
**Consequence:** ODIAC (11.8) lies outside the satellite 95% range in every variant; EDGAR (3.63) lies inside the symmetric range and outside the bias-corrected one.

## D19 — EMG fit window ≤ 45 km downwind with a sloped background (2026-10-01)
**Evidence:** the original main fit (flat background, fit to 60 km downwind) gave E(NOx) = 0.522 kg/s. A sloped background (B + c·x) on the same window gave 0.740 (+42%, τ 0.89 h). Investigating:
- **Synthetic data** (true background flat): flat and sloped give the same E bias (+11–12%); the sloped model's τ is closer to the truth (−6% vs −16%). The sloped model is not biased.
- **Real data, by fit window:** 60 km: flat 0.522 / sloped 0.740; **45 km: flat 0.591 / sloped 0.663**; 30 km: flat 0.609 / sloped 0.651.

Beyond ~45 km the downwind profile contains **PCMC and Talegaon, a second source** (east-southeast winds), which violates the EMG's single-source assumption. With a flat background, the fit absorbs that tail as slow decay (long τ → low E). Inside 30–45 km both background models converge (0.59–0.66).
**Decision:** fit the EMG up to **45 km downwind** with a **sloped background** (config `inversion.fit_along_max_km: 45`, `background_slope: true`). The remaining spread (flat 45 km, sloped 30 km) becomes a new budget term, *EMG structure (D19)*. The original flat-60 km fit is kept as a documented sensitivity case. Pre-D19 results are archived in `outputs/phase1/v2_before_d19/`. Synthetic recovery with the D19 configuration: E +11.3–11.5% (unchanged), τ −6 to −15%.
**Consequence:** the city NOx rises ~20%. Every downstream number changes (CO₂, the CO:NOx ratio and so the CO₂:NOx ratio, the satellite-vs-EDGAR gap), so the whole chain is rerun. The flux-divergence *shares* (D10) are unaffected; FD absolute totals change through τ.

## D20 — Roads: GRIP4 as a documented fallback for v1; OpenStreetMap for v2 (2026-10-01)
**Problem:** the proposal specifies OpenStreetMap roads, but Overpass (and two mirrors) returned 504/429 for hours and Geofabrik was down. Only 16 of 35 tiles were downloaded after several resumable passes.
**Decision:** feature table **v1** uses **GRIP4** (Global Roads Inventory Project, Meijer et al. 2018; GEE `projects/sat-io/open-datasets/GRIP4/South-East-Asia`). Types 1–2 → major, 3–4 → mid, 5 → minor, computed per cell in Earth Engine (`src/ecotrack/acquire/roads_grip.py`). The source is recorded in `feature_table_v1.meta.json`. **When the OSM download completes, v2** uses OSM as primary and keeps GRIP4 as `grip_*` cross-check columns.
**Caveat:** GRIP4's local roads are sparse and older (source year ~2014): `road_minor_km` median 0.07 km/cell, so minor-road density is the weakest v1 feature.
**Resolved (2026-10-04):** Overpass still failed, but Geofabrik was back. The India western-zone extract (`western-zone-261003.osm.pbf`, MD5 verified) is read locally with pyosmium (`acquire/osm_pbf.py`). **Feature table v2** uses OSM roads (GRIP4 kept as `grip_*`: Spearman 0.84 major, 0.59 minor; OSM minor-road median 4.2 vs 0.07 km) and adds **`industrial_frac`** (OSM `landuse=industrial`) from the same file. v1 is kept unchanged.

**D19 results (2026-10-01, full chain rerun):** main E(NOx) **0.663 kg/s [0.620–0.715]**, τ 1.09 h [0.96–1.23], R² 0.998. Quality-rule fallbacks: westerly regime (sloped τ 0.42 h, bootstrap 0.80–3.96 → flat 0.484) and season 2023–24 (sloped τ 0.75 h, bootstrap 0.75–2.37 → flat 0.663). The first D19 rerun without the rule gave a spurious ±52% budget. Budget structure term 5.4%; wind-level term drops to 0.8%. DE: all 24 converged fits identical (0.6627); the 12 CR = 0.3 runs didn't converge within maxiter for 6 parameters (within 3% of optimal cost). **Downstream:** CO:NOx 16.7 [14.7–18.8] (EDGAR 16.0); CO₂:NOx 163 (148–180); CO₂ midday 3.40 Mt/yr; annual MC **2.79 [1.79–4.36]**; satellite NOx annual −17 to −19% vs EDGAR (was −36%).

**D12 status after D19:** the CO constraint stands (CO₂:NOx now 163, 95% 148–180, vs EDGAR 172), but its **interpretation is revised**: the pre-D19 conclusion "more household/biomass burning than EDGAR" came from an underestimated NOx and is **withdrawn**. Post-D19 CO:NOx agrees with EDGAR's within 4%, and all four sector scenarios are feasible.
