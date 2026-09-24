# EcoTrack — Feasibility Memo (Weeks 0–2)

**Project:** Meteorology-informed multi-source satellite estimation of urban fossil-fuel CO₂, Shivajinagar → Talegaon Dabhade corridor, Pune
**Author:** Janhavi Tupe  **Date:** 2026-09-24  **Status:** Final draft for guide review

---

## 1. Purpose

Before building the full pipeline, four go/no-go checks were run to test the proposal's key
assumptions against real data. Each check had a threshold set in advance (`configs/study.yaml`). This memo
reports the results and the design changes that follow from them.

Study period: **October 2019 – May 2024, October–May seasons only** (40 months).
Corridor: the Old Pune–Mumbai Highway centreline buffered by ±3.5 km, plus Talegaon MIDC: **269 km²** (about 270 grid cells at 1 km; see D9).

## 2. Results

| Check | Question | Result | Verdict |
|---|---|---|---|
| **G2** TROPOMI coverage | Enough cloud-free NO₂ overpasses per month for monthly composites? | Median **26 usable days per month**; minimum 13 (October 2019 and October 2020); no month below 5 | **PASS**: monthly composites viable |
| **G3** NO₂ signal | Is the NO₂ over each cluster clearly above regional background? | Enhancement over the 10th-percentile background, all 5 seasons: C1 Shivajinagar–Kasarwadi **2.22–2.37×**, C2 PCMC **2.10–2.25×**, C3 Dehu–Talegaon **1.71–1.81×** | **PASS**: cluster-scale inversion worth attempting |
| **G1a** OCO-3 XCO₂ | Enough direct CO₂ observations over the corridor? | Corridor: 6 usable days. City scale: **7 strong days** (≥50 good soundings), 6 of them Snapshot Area Maps (SAMs). No data after November 2023 | **PARTIAL**: case study, not ML target |
| **G1b** OCO-2 XCO₂ | Can OCO-2 fill the gaps? | 1,177 days scanned: **1 strong day** (2024-01-23, glint track crossing C1/C2: 60 good soundings in corridor) | **MARGINAL**: adds one transect, which fills the 2023–24 OCO-3 gap |
| **G4** Geometry | Are the waypoint coordinates correct, and does the corridor cover the named industrial estates? | 6 of 10 waypoints were >500 m off (Dehu Road 4.4 km). Corrected to OSM positions; corridor rebuilt on the actual highway (median 200 m error). Talegaon MIDC was outside and has been added. MIDC Bhosari 99% inside | **FIXED**: D9 |

### Notable findings
- **Pune is an OCO-3 SAM target.** OCO-3 mapped the Pune area in dedicated snapshot mode on at least 9 dates in 2019–2023. The best are 2020-12-20 and 2020-12-24, each with more than 1,100 good-quality soundings in the surrounding area. Most of these fall just outside the narrow corridor, so OCO-3 is a city-scale instrument here, not a grid-cell one.
- **Earth Engine's TROPOMI product has no `qa_value` band.** Quality filtering happens inside Earth Engine's own processing. The Methods chapter will describe the QC as Earth Engine's built-in quality filter plus cloud fraction ≤ 0.3 and solar zenith ≤ 70°.
- **Wind at overpass time (ERA5, 850 hPa):** median 3.5 m/s; 192 calm and 763 moderate (2–7 m/s) overpasses, enough for Phase 1's source location and rotation fit. Winds come from the **east-southeast in October–March** (central Pune upwind of PCMC) and **reverse to west-northwest in April–May**. Each cluster is therefore seen from both upwind and downwind sides, which helps separate the clusters.
- **October is the weakest month** for TROPOMI coverage (13–25 usable days), probably because of late-monsoon cloud.
- **G3 caveats:** C1's enhancement may include spillover from central Pune, and C3's may include PCMC pollution carried downwind. G3 shows there is a signal, not that the three clusters are separate sources. Phase 1's wind-rotated line densities test that.

## 3. Design changes from the proposal

Full reasoning is in `docs/decisions.md`.

| # | Change | Reason |
|---|---|---|
| D1 | NO₂ inversion over **3 clusters**, not 10 waypoints | Waypoints are closer together than one TROPOMI pixel (3.5 × 5.5 km); G3 confirms each cluster has a signal |
| D2 | **Layers used to build CO₂ labels are excluded from model features** | Otherwise Experiment D "wins" by learning the allocation weights back, a circular result |
| D4 | Add **TROPOMI CO** | CO:NO₂ ratio is a physical indicator of traffic vs. industrial sources |
| D5 | Drop the U-Net; use XGBoost/RF with spatial-block CV and bootstrap CIs | About 260 cells × 40 months is too little data for a deep model |
| D6 | ERA5 hourly wind and boundary-layer height as primary meteorology | Finer resolution; matches the TROPOMI overpass time |
| D9 | Corridor = highway centreline ± 3.5 km + Talegaon MIDC | Proposal waypoints were up to 4.4 km off; Talegaon MIDC lay outside the original buffer |
| **D8** *(proposed)* | **OCO-3 (7 dates) + OCO-2 (1 date) used for a city-scale mass-balance CO₂ estimate, compared with the NO₂-derived CO₂** | Too sparse for per-cell ML (G1a), but it directly tests the NOx:CO₂ conversion, the base paper's largest error term (~25% of its uncertainty) |

**Request for the guide:** please review **D8**. It changes Experiment B from "OCO-3 as a model
feature" to "OCO-3 as an independent check on cluster totals". The result becomes a case study with n = 8
rather than a statistical comparison.

## 4. Revised near-term plan

| Weeks | Work |
|---|---|
| 3 | Corridor finalised (G4/D9) and ERA5 matched to 1,031 overpasses: **done** |
| 3–5 | Phase 1: wind rotation, line densities and Differential Evolution inversion for C1–C3; NOx → CO₂ via EDGAR sector ratios |
| 5–6 | OCO-3 SAM mass-balance on 7 dates + OCO-2 transect on 2024-01-23; comparison with Phase 1 (D8) |
| 4–7 | Phase 2 data layers (VIIRS, OSM, Sentinel-2, TROPOMI CO, EDGAR, ODIAC) on the 1 km grid |

## 5. Risks

- **Chakan industrial area** lies outside the corridor to the NE and may add NO₂ on NE-wind days.
- **Cluster separability** (G3 caveat): if the line densities can't separate C1–C3, the inversion falls back to a single Pune+PCMC source and the corridor map becomes a downscaled product.
- **Direct-CO₂ sample size** (n = 8): the D8 comparison shows whether the two methods agree or disagree; it can't validate either one statistically.
- **No OCO-3 data from December 2023 onward**: the 2023–24 season has only the single OCO-2 transect (2024-01-23) as a direct CO₂ check.
