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
