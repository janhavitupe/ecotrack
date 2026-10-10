# EcoTrack — Analysis Plan for the ML Experiments (Phases 4–6)

**Status:** DRAFT, to be frozen (committed to git) **before any model is trained**. The commit timestamp is the proof.
**Author:** Janhavi Tupe · **Date:** 2026-10-10
**Why this document exists:**
- The labels are constructed and largely one smooth gradient away from Pune.
- The independent data are limited.
- Experiment B is expected to be weak at 1 km.

Fixing the metrics, splits, controls and decision rule in advance prevents "tuning until something wins", and makes a null result a valid result.

The block size (§4.1) was filled in from data on 2026-10-10, before any model was trained; its history is in §10.

---

## 1. Data (frozen inputs)

| Input | File | SHA-256 |
|---|---|---|
| Features (regional grid, D22) | `data/processed/feature_table_v2_region.csv` | `c19c057f2e60de2b025a9340db942cc276eb3d5a9612345dcc85673bc37152fa` |
| Labels (regional grid, D16/D21/D22) | `data/processed/labels_v1_region.csv` | `cc6172dbf6b4054577da20c49e1cf511f65c84832b0ec70a05d828e78f4fa6f9` |
| Model table: season means + labels + splits (Phase 4) | `data/processed/model_table_v1_region.csv` | `347dbb72cf94c73e19c57554533f291ce595fd0c677bd39ba3903f4f94d0aff0` |

- **Unit of analysis:** one cell × one season. Monthly features are averaged over the season's months.
- **Domain:**
  - **Training:** all regional cells (2,894 × 5 seasons).
  - **Reporting:** every score for (a) all held-out cells and (b) held-out **corridor** cells (268 cells).
- **Wind direction** is circular, so it enters as sin and cos.

## 2. Labels

| Label | Role | Notes |
|---|---|---|
| **L-fd** | primary | NO₂-built: Experiment A is the **construction baseline** |
| **L-co** | independent check | CO-built, spatial-only (D21). `co_norm` is dropped from all feature sets, so **Experiment B is undefined on L-co** (it would equal A) |

Each score is also reported as a fraction of the label's **noise ceiling**:

| | Regional grid | Corridor |
|---|---|---|
| L-fd | 0.99 | 0.97 |
| L-co | 0.78 | 0.75 |

L-co is weak away from the city:
- across the region its median uncertainty is 63% and 20% of its values are negative;
- its cell pattern agrees with L-fd at r = 0.75 (region) vs 0.93 (corridor).

**L-co results are therefore interpreted mainly on the corridor.**

## 3. Experiments and controls

| Set | Features |
|---|---|
| **A** | no2 |
| **B** | A + co_norm |
| **C** | B + ws850, sin/cos(wd850), blh_m, frac_ese, t2m_k, ssrd_j_m2, hcho |
| **D** | C + viirs_rad, ndvi, ndbi, road_major_km, road_mid_km, road_minor_km, road_total_km, industrial_frac |
| **N0: geography-only null** | dist_to_source_km, x_utm, y_utm |
| **N1: shuffled control** | D's features with rows permuted within each training fold (breaks the feature–label link) |
| **Feature-group ablation** | D minus one group at a time: {NO₂}, {CO}, {weather + HCHO}, {night lights}, {land cover: NDVI, NDBI}, {roads}, {industrial land} |

**Residual target (the "beyond geography" test).** For every split, fit the label against distance to the source on the **training cells only**:
- a monotone smooth: isotonic regression, decreasing with distance;
- then train each experiment on the residuals and score on held-out residuals.

The fit uses training data only, so no information leaks from the test cells.

## 4. Splits

### 4.1 Block size: **15 km** (23 blocks, ~13 independent areas)
- **Measured:** the correlation range of the label **errors**.
- **Method:** rebuild the NO₂ emission map from 30 bootstrap resamples of the satellite days, sample each at the cells exactly as the labels are made, and compute the variogram of (resample − main map).
- **Rule:** the block is the larger of (a) the fitted exponential practical range and (b) the first distance where the semivariance reaches 95% of the sill, rounded up to a whole km, minimum 5 km.
- **Result:** regional grid: practical range 14.7 km, first crossing 14.5 km → **15 km**.

**Why errors and not the label itself:**
- The label is smooth at every scale. Its variogram keeps rising to ~30 km even after removing the distance trend, so a "range" is undefined.
- Neighbouring cells can leak information in two ways:
  1. **Shared smooth signal:** a model can interpolate it from location. That is exactly what the geography-only null **N0** measures, and every experiment is scored as skill above N0.
  2. **Shared label errors:** the 5 km smoothing and the satellite footprint spread one error over several cells. Blocks must stop this.
- So blocks are sized to the error correlation.

**Checks:**
- Fixing each resample's 25 km denominator, or removing its domain mean, gives the same 14.5 km, so the range isn't an artefact of a common scale factor.
- **Folds** are balanced by cell count (blocks assigned largest first to the emptiest fold, seeded): 577–582 cells per fold.

### 4.2 Split schemes
1. **Spatial-block K-fold:** 15 km square blocks, assigned to K = 5 folds balanced by cell count (seed 42); all seasons of a cell stay in the same fold. *Robustness:* the comparison is repeated with 10 km and 20 km blocks; conclusions are reported as robust only if the sign of each significant difference holds at all three sizes.
2. **Corridor transfer:** train on all cells *outside* the corridor; test on the 268 corridor cells. This is the purest "does it generalise to an unseen area" test.
3. **PCMC hold-out:** train on cells more than 5 km from any C2 cell (2,600 cells); test on C2 (63 cells); the 231 cells in between are unused. C2 hosts the second hotspot, which a distance-only model cannot place.
4. **Leave-one-season-out (L-fd only):** the temporal test.

## 5. Models (fixed settings: no per-experiment tuning)

| Model | Settings |
|---|---|
| Ridge regression (floor) | standardised features (fit on training folds only); α by inner 5-fold CV on training blocks |
| Random Forest | 500 trees, min_samples_leaf 5, max_features 0.5, seed 42 |
| XGBoost | 400 trees, depth 4, learning rate 0.05, subsample 0.8, colsample 0.8, seed 42 |

Hyperparameter tuning (proposal Phase 6) is done **once, on the best configuration only**, by nested CV, and is reported separately. It never decides between experiments.

## 6. Metrics

- **R², RMSE, MAE** on held-out data.
- **Skill over the null:** ΔR² = R²(experiment) − R²(N0), on the same split.
- **Decomposition** of each held-out prediction:
  - **spatial skill:** R² of cell means across held-out cells;
  - **temporal skill:** R² of each cell's seasonal anomalies (L-fd only).
- **Ceiling-normalised R²:** R² ÷ noise ceiling.

## 7. Decision rule

- All experiments are scored on **identical splits**.
- Differences (e.g. D − C, D − N0) are **paired**. Their 95% intervals come from a **block bootstrap**: 1,000 resamples of whole spatial blocks of the test set.
- **A difference counts only if its 95% interval excludes zero.** Otherwise the result is "no detectable difference", and that is reported as such.

## 8. Predictions (written before any model is run)

| # | Prediction | Reason |
|---|---|---|
| P1 | On L-fd, A scores high in raw R² | Construction link (NO₂ ↔ L-fd, Spearman 0.91) |
| P2 | **B ≈ A in spatial skill** on L-fd | CO barely varies between 1 km cells (Phase 2 spatial share 0.02) |
| P3 | B may add a little temporal skill on L-fd (leave-one-season-out) | CO's information is seasonal; small effect expected |
| P4 | D > C in spatial skill, and D > N0 on the residual target, with the gain concentrated in the PCMC hold-out | Activity layers should place the PCMC hotspot that geography can't |
| P5 | N1 (shuffled) shows ~0 skill over N0 | Sanity control |
| P6 | NDBI contributes little or negatively in the ablation | Dry-soil confusion (Phase 2) |
| P7 | On L-co, scores are lower in absolute terms but similar as a fraction of the ceiling | L-co is noisier (ceiling 0.75 in the corridor) |

## 9. Reporting rules

- Every experiment, control and split is reported, including the ones that don't support a prediction.
- Any change to this plan after freezing is recorded as a dated amendment with its reason, and results are shown both ways.
- Feature importance (permutation importance on held-out blocks) is *descriptive*. Correlated features share importance (Phase 2 correlation QA).

## 10. History of this plan (before freezing)

| Date | Change | Reason |
|---|---|---|
| 2026-10-10 | Draft written | — |
| 2026-10-10 | Block rule: added "first crossing of 95% of the variance" to the fitted range | The corridor's label variogram has a hole effect (narrow domain); decided before the regional data existed |
| 2026-10-10 | **Block rule changed from the label variogram to the label-error variogram** | On the regional grid the first rule returned 100 km (the fit hit its bound; 2 blocks), because the label has no finite range. No model had been trained. The argument for errors is in §4.1 |
| 2026-10-10 | Folds balanced by cell count | Random block assignment gave folds of 207–1,057 cells |
| 2026-10-10 | Robustness at 10 and 20 km blocks; L-co interpreted mainly on the corridor | Added with the block result |
