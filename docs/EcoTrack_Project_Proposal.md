# EcoTrack
## Meteorology-Informed Multi-Source Satellite-Based Estimation of Urban Fossil-Fuel CO₂ Emissions
### Project Proposal — Shivajinagar to Talegaon Dabhade Corridor, Pune

---

## 1. Executive Summary

Cities generate an estimated 70% of global anthropogenic CO₂ emissions, yet traditional
bottom-up emission inventories are slow to update, coarse in spatial resolution, and
inconsistent across regions. Satellite remote sensing offers a complementary top-down
approach, but existing satellite-based CO₂ estimation methods largely depend on a single
tracer — most commonly NO₂, used as a proxy for co-emitted fossil-fuel CO₂ via inventory
NOx:CO₂ ratios. This single-tracer dependence is a documented limitation: it inherits all
the uncertainty of the proxy relationship and cannot independently verify the CO₂ signal
it infers.

**EcoTrack** addresses this gap by fusing multiple satellite observations
(TROPOMI NO₂ and OCO-3 XCO₂), meteorological transport information (wind, boundary-layer
height, atmospheric chemistry proxies), and human-activity context (nighttime lights,
road density, built-up and vegetation indices) into a machine-learning framework that
estimates gridded urban fossil-fuel CO₂ emissions without relying on any single
observation source.

The study area is a ~33 km corridor along the **Old Mumbai-Pune Highway**, from
**Shivajinagar to Talegaon Dabhade**, Pune district, Maharashtra — a corridor chosen
specifically because it contains co-located, spatially adjacent traffic and industrial
emission sources (Khadki, Dapodi, Pimpri-Chinchwad MIDC, Akurdi-Nigdi, Dehu Road,
Talegaon MIDC), making it an unusually good testbed for asking whether additional data
sources can help a model distinguish between emission source types that a single NO₂
tracer cannot separate on its own.

The project is scoped as a 6-month (26-week), phased research effort producing: a
reproduced NO₂-based emission baseline (Phase 1), a fused multi-source 1 km gridded
dataset (Phase 2), a constrained CO₂ label-construction method (Phase 3), a four-stage
ablation study isolating the contribution of each data source (Phases 4–6), spatial and
uncertainty validation (Phase 7), and a final report with an explicit, honest account of
limitations (Phase 8).

---

## 2. Background and Motivation

### 2.1 The problem
Precise, timely, spatially resolved quantification of urban CO₂ emissions is essential
for climate mitigation planning, yet:
- Bottom-up inventories (e.g., national energy statistics) report emissions annually or
  biennially, at city or provincial resolution, with reporting lags of 1–2 years.
- CO₂-observing satellites (OCO-2, OCO-3, GOSAT) measure the atmospheric signal directly
  but at coarse spatial resolution and with sparse temporal/spatial coverage, since CO₂'s
  long atmospheric lifetime and high background concentration (~420 ppm) make isolating a
  local anthropogenic enhancement difficult.
- NO₂-observing satellites (TROPOMI) offer much higher spatial and temporal resolution
  and a shorter atmospheric lifetime, making local emission sources easier to isolate —
  but NO₂ is not CO₂. It requires an assumed, inventory-derived NOx:CO₂ emission ratio to
  convert one into the other, and that ratio varies by fuel type, combustion technology,
  and photochemical conditions.

### 2.2 The specific gap EcoTrack targets
The base methodology this project builds on (a TROPOMI NO₂ + wind-rotation + Differential
Evolution line-density inversion, validated at city scale in Shandong Province, China)
demonstrates that NO₂-derived CO₂ estimates can achieve strong internal fit (R² ≈ 0.95–0.97
on the NO₂ inversion itself) but the paper's own uncertainty analysis identifies the
NOx:CO₂ inventory-anchored conversion as the single largest error term (~25% of a total
35–45% uncertainty budget), and explicitly recommends incorporating direct CO₂
observations (e.g., OCO-3) to reduce this dependence.

**EcoTrack's research question:**
> Can combining multi-satellite observations, meteorological transport information, and
> human-activity indicators improve the spatial estimation of urban fossil-fuel CO₂
> emissions, compared with relying primarily on a single atmospheric tracer?

**Primary contribution:** evaluate the value of multi-source satellite observations for
urban fossil-fuel CO₂ estimation, while explicitly quantifying the additional
contribution of meteorological and human-activity information.

**Secondary contribution:** determine under which conditions (source type, atmospheric
conditions, data coverage) these additional information sources actually improve
estimation accuracy, rather than assuming they always do.

---

## 3. Related Work

| Study | Contribution relevant to EcoTrack |
|---|---|
| Xie et al. (Remote Sensing, 2026) — Shandong TROPOMI NO₂ + DE algorithm | Base methodology: wind-rotation, line-density model, Differential Evolution inversion, NOx:CO₂ conversion, ODIAC/EDGAR comparison, RSS uncertainty propagation |
| Hobbs et al. (Climate TRACE / WattTime, IGARSS 2023) | ML-based power-plant CO₂ estimation from multi-spectral imagery; precedent for plant-level generation-to-emissions modeling |
| Verma et al. (ICITIIT 2023) | LSTM forecasting of satellite-based CO time series; precedent for deep-learning treatment of atmospheric trace-gas time series |
| Sun et al. (CELCT 2026) — Yangtze River Delta | Constrained spatial label-allocation method (city totals → grid cells via nighttime lights/industrial-land/road weights); spatiotemporal attention U-Net architecture; feature-group ablation design — directly adapted for EcoTrack's label construction and experimental design |
| Arriaga et al. (INTERCON 2024) — Lima, Peru | OCO-3 + Sentinel-2 NDVI correlation methodology; documents real-world OCO-3 data sparsity (only ~10 usable dates over 3 years) — informs EcoTrack's OCO-3 feasibility-first approach |
| Menezes et al. (IGARSS 2025) — Wildfire biomass loss | Random Trees regression from NDVI/NBR/RVI/DEM for biomass-to-CO₂ conversion; relevant if disturbance/land-use confounds are found in the study corridor |
| To et al. (IEEE CAI 2024) | Tree/vegetation semantic segmentation at scale; relevant to NDVI-based biogenic-signal separation |
| Cao et al. (IEEE TGRS 2024) — DaQi-1 ACDL | Averaging-scheme and systematic/random error correction methodology for LiDAR-based CO₂ retrieval; precedent for EcoTrack's RSS-based uncertainty propagation |
| Giridharan & Sivakumar (InGARSS 2024); Anurogo et al. (ICST 2018) | NDVI/FPAR/APAR/NPP allometric carbon-stock estimation — reference methodology if a biogenic-correction term is added |

---

## 4. Study Area

### 4.1 Corridor definition
**Shivajinagar → Talegaon Dabhade**, following the Old Mumbai-Pune Highway
(MSH-4 / old NH4), Pune district, Maharashtra. Approximate corridor length: 33 km.

**Rationale:** this corridor is one of the few segments in the Pune metropolitan region
where dense industrial emission sources and heavy-vehicle traffic corridors are
directly co-located and spatially interleaved, rather than occurring in separate parts
of the city. This makes it a genuine test of whether EcoTrack's additional features
(road density, NDBI, nighttime lights) can help separate industrial-source CO₂ from
traffic-source CO₂ — a distinction that NO₂ and meteorology alone cannot make, since both
source types co-emit NOx.

### 4.2 Waypoints and sub-zone classification

| Location | Approx. coordinates | Category |
|---|---|---|
| Shivajinagar | 18.531°N, 73.848°E | Traffic / urban core |
| Khadki | 18.564°N, 73.851°E | Traffic / defense-industrial |
| Dapodi | 18.579°N, 73.831°E | Industrial |
| Kasarwadi | 18.598°N, 73.826°E | Industrial |
| Pimpri | 18.630°N, 73.813°E | Industrial + traffic |
| Chinchwad | 18.630°N, 73.800°E | Industrial + traffic |
| Akurdi | 18.648°N, 73.767°E | Industrial |
| Nigdi | 18.655°N, 73.764°E | Traffic |
| Dehu Road | 18.717°N, 73.750°E | Traffic / cantonment |
| Talegaon Dabhade | 18.721°N, 73.687°E | Industrial + traffic |

*Coordinates above are working values; verification against OpenStreetMap/ground
sources is a required Week 1 task before any quantitative analysis is run on them.*

### 4.3 Geometry
- **Corridor polygon:** waypoint line buffered ±3.5 km, to capture MIDC industrial land
  set back from the highway without including unrelated hill/agricultural terrain.
- **Working bounding box** (for simple data queries): lat 18.50–18.75°N,
  lon 73.65–73.87°E.
- **Modeling grid:** 1 km × 1 km cells within the corridor polygon.

### 4.4 Ground-truth / calibration reference
- **MPCB CAAQMS** — Karve Road station and historical Bhosari/Nal Stop monitoring
  (documented NOx exceedances in MPCB reports).
- **SAFAR network (IITM Pune)** — multi-microenvironment surface air-quality monitoring
  (industrial, traffic, residential, background categories), used as a qualitative,
  directional cross-check — **not** a direct validation of column CO₂/NO₂, since surface
  point measurements and satellite column measurements are physically different
  quantities.

---

## 5. Data Sources

| Layer | Variable | Source | Access method | Priority |
|---|---|---|---|---|
| TROPOMI | Tropospheric NO₂ column | Copernicus Sentinel-5P | Google Earth Engine / Copernicus Data Space | Core |
| OCO-3 | XCO₂ | NASA GES DISC | `earthaccess` (NASA Earthdata login) | Core / novelty |
| MERRA-2 or ERA5 | Wind U/V, boundary-layer height | NASA GES DISC / Google Earth Engine | `earthaccess` or GEE | Core |
| Atmospheric chemistry proxy | O₃, VOC-related fields | MERRA-2 / CAMS reanalysis | GES DISC / GEE | Core |
| VIIRS | Nighttime lights (radiance) | NASA Black Marble | Google Earth Engine | Core |
| OpenStreetMap | Road network | OSM | `osmnx` | Core |
| Sentinel-2 / Landsat-8 | NDBI, NDVI | Copernicus / USGS | Google Earth Engine | Core |
| EDGAR | Gridded NOx/CO₂ inventory | EC Joint Research Centre | Direct NetCDF download | Prior / conversion ratio only — not ground truth |
| ODIAC | Gridded fossil-CO₂ inventory | NIES Japan | Direct NetCDF download | Plausibility comparison only |
| MPCB / SAFAR | Surface NO₂, PM | MPCB / IITM | Public reports / data request | Optional qualitative check |

**Explicit design rule:** EDGAR and ODIAC are used only as *priors* (for spatial
allocation weighting and the NOx:CO₂ conversion ratio) and as *plausibility comparisons*
respectively — never as training ground truth for the ML model, since doing so would
make the model's accuracy circular (predicting a quantity derived from the same
inventory used to validate it).

---

## 6. Methodology Overview

```
Satellite observations
        ↓
TROPOMI NO₂  +  OCO-3 XCO₂
        ↓
Atmospheric transport / context (wind, BLH, chemistry)
        ↓
NO₂ emission inversion (wind-rotation + line-density + Differential Evolution)
        ↓
Constrained spatial CO₂ label (regional total → grid cells via activity-weighted allocation)
        ↓
Multi-source feature dataset (NO₂, XCO₂, meteorology, nighttime lights, roads, NDBI, NDVI)
        ↓
Experiments A/B/C/D — machine-learning ablation
        ↓
Spatial validation + uncertainty quantification
        ↓
Final corridor fossil-CO₂ estimation map
        ↓
Scientific interpretation + limitations
```

### 6.1 Experimental design (core ablation)
| Experiment | Features included | Tests |
|---|---|---|
| A | TROPOMI NO₂ only | Single-tracer baseline (reproduces base paper's approach on the corridor) |
| B | A + OCO-3 XCO₂ | Does direct CO₂ observation improve estimation over NO₂-proxy alone? |
| C | B + meteorology (wind, BLH, chemistry proxy) | Does atmospheric transport/dilution context add value? |
| D | C + human-activity (nighttime lights, road density, NDBI, NDVI) | Does ground-context help separate industrial vs. traffic source signatures? |

A secondary **feature-group ablation** (drop-one-group from the full model) isolates
which individual addition contributes most, following the design used in the Yangtze
River Delta multi-source CO₂ study.

---

## 7. Phased Plan (6 Months / 26 Weeks)

Work runs across four parallel tracks rather than strictly sequentially:
**Track A** (data pipeline), **Track B** (base-paper reproduction), **Track C**
(modeling), **Track D** (writing, continuous).

### Phase 1 — Reproduce the base NO₂ pipeline on the corridor (Weeks 1–4)
**Goal:** a standalone floor result, valid even if later phases underperform.
1. Acquire and QC TROPOMI NO₂ (cloud fraction ≤0.3, QA ≥0.7, solar zenith ≤70°, IQR
   outlier removal) — thresholds documented, changes logged, not silently altered.
2. Acquire and time-match MERRA-2/ERA5 wind (U/V → speed, direction).
3. Per sub-zone (Khadki, Pimpri-Chinchwad, Akurdi, Talegaon Dabhade, etc.): determine
   calm-wind reference point, rotate moderate-wind observations, compute line density.
4. Fit Differential Evolution inversion (NP=300, F∈[0.5,1.0], CR=0.7 as starting
   settings; sensitivity-tested, not treated as fixed constants) to estimate NO₂
   emission rate, atmospheric lifetime, background concentration.
5. Convert to a first-pass CO₂ estimate via an EDGAR-derived NOx:CO₂ ratio, explicitly
   labeled as an assumption, not a direct measurement.
6. Compare against ODIAC as a plausibility check (not independent ground truth).

**Deliverable:** QC'd TROPOMI dataset, wind-matched observations, plume/line-density
plots per sub-zone, DE inversion results, first-pass CO₂ estimates, ODIAC comparison,
Phase 1 report.

### Phase 2 — Multi-source data acquisition and gridding (Weeks 3–6, overlapping Phase 1)
**Goal:** every additional data layer collected, QC'd, and ready for a common grid.
1. Acquire OCO-3 XCO₂ for the corridor bbox; run the feasibility sounding-count check
   **immediately in Week 1**, not after building everything else.
2. Acquire VIIRS nighttime lights, OSM road network, Sentinel-2 NDBI/NDVI.
3. Acquire EDGAR and ODIAC gridded products, clipped to the corridor.
4. Build the 1 km × 1 km modeling grid over the corridor polygon; rasterize every layer
   onto it.
5. QA the assembled dataset — missing-data audit, per-feature sanity histograms,
   manual spot-checks of 5–10 cells.

**Deliverable:** complete, versioned, frozen multi-source feature table.

### Phase 3 — Label construction (Weeks 6–7)
1. Redistribute Phase 1's regional/sub-zone NO₂-derived CO₂ totals to 1 km cells using
   a composite weight of nighttime lights + NDBI (industrial-land fraction) + road
   density.
2. Calibrate with OCO-3-conditioned anomalies where coverage allows.
3. Document the circularity risk explicitly: labels are partly EDGAR/activity-anchored,
   not independent ground truth.

**Deliverable:** reproducible label-construction module + documented limitations.

### Phase 4 — Feature tensor construction (Week 7)
Assemble per-cell, per-month feature vectors: `[NO₂, XCO₂, wind speed, wind direction,
BLH, chemistry proxy, nighttime lights, road density, NDBI, NDVI]`. Standardize per
month; gap-fill missing OCO-3 cells via seasonally-constrained interpolation.

### Phase 5 — Modeling (Weeks 8–9)
Train Experiments A → B → C → D (XGBoost/Random Forest primary; small U-Net with
temporal gate as a stretch goal only if monthly composite count justifies it).
Spatial block train/val/test split (not random) to avoid cell-adjacency leakage.

### Phase 6 — Ablation and comparison (Weeks 10–12)
Full A/B/C/D comparison (R², RMSE, MAE) plus feature-group ablation. Hyperparameter
tuning on best-performing configuration.

**Deliverable:** ablation results table, predicted-vs-observed scatter plots.

### Phase 7 — Validation, uncertainty, spatial analysis (Weeks 13–16)
1. Spatial block cross-validation across all models.
2. RSS uncertainty propagation: TROPOMI inversion error + wind/transport error +
   NOx:NO₂ conversion error + DE/ML fitting error + inventory-conversion error.
3. Spatial hotspot maps across sub-zones; Hinjewadi-style negative-control reasoning
   applied to Nigdi/Dehu Road (traffic-heavy, lower industrial NOx).
4. Qualitative SAFAR/MPCB directional cross-check.
5. Buffer week for fixes; decision point on whether the U-Net stretch model is
   realistic given remaining time.

**Deliverable:** validation report, uncertainty budget, hotspot/residual maps.

### Phase 8 — Write-up, review, submission (Weeks 17–26)
1. Freeze all results (Week 19) — no further model changes after this point.
2. Draft Methods and Results (Weeks 19–20).
3. Draft Introduction, Discussion, Limitations, Future Work (Weeks 21–22).
4. Internal review by someone not involved in implementation details (Week 23).
5. Re-run buffer for review-triggered corrections only (Week 24).
6. Final formatting — abstract, references, figure captions, units, terminology,
   acronym definitions, overclaiming check (Week 25).
7. Presentation preparation and submission (Week 26).

---

## 8. Timeline Summary

| Weeks | Phase | Primary output |
|---|---|---|
| 1–4 | Phase 1 | NO₂/CO₂ baseline per corridor sub-zone |
| 3–6 | Phase 2 | Complete multi-source feature dataset |
| 6–7 | Phase 3 | CO₂ label-construction module |
| 7 | Phase 4 | Frozen feature tensor |
| 8–9 | Phase 5 | Trained A/B/C/D models |
| 10–12 | Phase 6 | Ablation results |
| 13–16 | Phase 7 | Validation + uncertainty + spatial maps |
| 17–26 | Phase 8 | Final report, review, submission |

---

## 9. Explicit Limitations (stated up front, not discovered late)

- OCO-3 spatial/temporal sparsity over the corridor — feasibility checked in Week 1,
  not assumed.
- Derived CO₂ labels are constrained estimates, not independent ground truth.
- EDGAR and ODIAC introduce inventory dependence and a documented circularity risk in
  both the NOx:CO₂ ratio and the label-allocation weights.
- TROPOMI retrievals degrade under cloud cover; monsoon-season gaps are expected and
  the study period (October–May) is chosen partly to avoid them, at the cost of not
  covering the full annual cycle.
- Surface station data (MPCB/SAFAR) measure a different physical quantity (point,
  surface-level) than satellite columns and can only be used as a directional,
  qualitative check.
- The NOx:CO₂ conversion factor is sector- and technology-dependent; a fixed ratio is a
  documented simplification, not a universal constant.
- Atmospheric reanalysis variables (MERRA-2/ERA5) are proxies for photochemical
  conditions, not a full chemical-transport model.
- Findings are scoped to this corridor and study period; generalization to other parts
  of Pune or other seasons is not claimed without further testing.

---

## 10. Final Reproducibility Package (target structure at submission)

```
EcoTrack/
├── README.md
├── data_dictionary.xlsx
├── environment.yml / requirements.txt
├── src/
├── notebooks/
├── configs/
├── outputs/
│   ├── figures/
│   ├── tables/
│   └── maps/
├── models/
├── reports/
│   └── final_report.pdf
└── CITATION.md
```

---

## 11. Success Criteria

The strongest version of this project is not the one with the most models or data
sources. It is the one where:
- every data source has a clearly stated purpose,
- every modeling and threshold choice is documented and justified,
- validation is difficult enough to be credible (spatial block splits, not random),
- uncertainty is reported honestly and propagated formally,
- and the final claims do not exceed what the corridor's data actually support.

A result showing that additional data sources provide little improvement over the NO₂
baseline is still a valid and useful research outcome, provided the experiment was
designed and validated properly.
