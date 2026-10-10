# EcoTrack — Analysis Plan for the ML Experiments (Phases 4–6)

**Status:** **FROZEN.** The git commit containing this line, made before any model was trained, is the proof. Any later change is a dated amendment (§9).
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

**Experiments on L-co:** N0, N1, A, C and D, with `co_norm` removed from C and D (B is undefined).

**Residual target (the "beyond geography" test).** For every split, fit the label against distance to the source on the **training cells only**:
- a monotone smooth: isotonic regression, decreasing with distance;
- then train each experiment on the residuals and score on held-out residuals.

The fit uses training data only, so no information leaks from the test cells. The residual target is run for N0, A, B, C and D on the block folds and the PCMC hold-out.

### 3.1 Primary hypotheses (the only ones that carry a significance claim)
With ~4 experiments × 2 labels × 4 splits, some differences would pass a 95% rule by chance. So **five tests are primary** (four hypotheses; H2 is scored for space and for time); everything else is secondary and reported descriptively.

| # | Tested group G | Base model | Label | Split | Score |
|---|---|---|---|---|---|
| H1 | **activity layers** (night lights, NDVI, NDBI, roads, industrial land) | geography + NO₂ + CO + weather/HCHO | L-fd | 15 km blocks | spatial skill |
| H2a | **CO** | geography + NO₂ | L-fd | 15 km blocks | spatial skill |
| H2b | **CO** | geography + NO₂ | L-fd | leave-one-season-out | temporal skill |
| H3 | **all of D's features** | none (the target already has the distance trend removed) | L-fd residual target | 15 km blocks | R² |
| H4 | **NO₂** | geography | L-co | 15 km blocks, corridor cells | spatial skill |

Each hypothesis asks: **does feature group G add predictive skill to the base model?** "Geography" = distance to source, x, y, so each test asks whether G helps *beyond location*. The test is a group permutation test (§7).

H4 is the NO₂-independent test: does satellite NO₂ locate emissions in a label that never used NO₂, beyond geography?

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
4. **Leave-one-season-out (L-fd only):** the temporal test. Only **temporal skill** is scored here: the held-out season shares its cells with the training seasons, so spatial skill would be leaked.

**Two test sets are too small for interval estimates:**
- **Corridor transfer:** 7 blocks, but uneven (117, 55, 44, 31, 14, 4, 3 cells), so effectively 3–4 areas. Its block-bootstrap intervals are reported but expected to be wide.
- **PCMC hold-out:** 2 blocks (58 + 5 cells), so effectively **one area**. It is a **descriptive case study**: point estimates only, no significance claim. P4's "PCMC" part is judged descriptively.

**Extrapolation in fold 3 (checked before freezing, from label ranges only, no model):**
- Tree models can't predict above the largest training label.
- Block fold 3 holds the central-Pune peak: 139 of its 2,890 test rows exceed every training label in that fold.
- Every other fold, the corridor split and the PCMC split have no test row above their training maximum.
- So results are also reported **per fold**, fold 3 is flagged, and the pooled comparison is repeated **without fold 3**. Ridge (which extrapolates) is shown for fold 3.

## 5. Models (fixed settings: no per-experiment tuning)

| Model | Settings |
|---|---|
| Ridge regression (floor) | standardised features (fit on training folds only); α by inner 5-fold CV on training blocks |
| Random Forest | 500 trees, min_samples_leaf 5, max_features 0.5, seed 42 |
| XGBoost | 400 trees, depth 4, learning rate 0.05, subsample 0.8, colsample 0.8, seed 42 |

- **Primary model: Random Forest.** All decisions (§3.1, §7) use it.
- **Ridge and XGBoost are robustness checks:** see §7 (robust = same sign in every variant).
- **Hyperparameter tuning** (proposal Phase 6) is done once, on the best configuration only, by nested CV, and reported separately. "Best" = the experiment with the largest ΔR² over N0 on L-fd, 15 km blocks. Tuning never decides between experiments.
- **Standardisation** is fitted on training data only. Trees don't need it but receive the same inputs.

## 6. Metrics

- **R², RMSE, MAE** on held-out data.
- **Skill over the null:** ΔR² = R²(experiment) − R²(N0), on the same split.
- **Decomposition** of the pooled out-of-fold predictions:
  - **spatial skill:** R² between the predicted and observed **cell means** (averaged over the 5 seasons) across held-out cells;
  - **temporal skill:** R² between predicted and observed **seasonal anomalies** (value minus that cell's 5-season mean), pooled over cells (L-fd only).
- **N1 (shuffled control):** training feature rows are permuted (labels stay), the model is trained, and it predicts the unpermuted test features.
- **Ceiling-normalised R²:** R² ÷ noise ceiling.

## 7. Decision rule: group permutation tests

For each primary hypothesis:
1. Fit the base model + G with the **real** G values: out-of-fold score s_obs.
2. Refit **99 times** with G replaced by a **structured null version** that keeps its realistic structure but breaks its alignment with the label (same columns, model, splits and seed): scores s_1 … s_99.
   - **Spatial tests (H1, H2a, H3, H4): rotations.** G's maps are rotated about the emission source (alternating plain rotations and mirror-then-rotate, angles spread over 20–340°), with the same transform in every season, for training and test rows. A rotated map keeps its smoothness and its rings around the city; only its directions stop lining up with the label.
   - **Temporal test (H2b): season permutations** (below).
   - **Why not shuffle rows:** a shuffled map loses its smoothness. On smooth random null labels, row shuffling gave 8 false alarms in 12 tests: unrelated smooth maps line up by chance, and shuffled ones never do (§10).
3. **Effect** = s_obs − mean(s_r). **One-sided p** = (1 + number of s_r ≥ s_obs) ÷ 100. Rotations by different angles are not fully independent (with ~13 independent areas, only a handful of truly different rotations exist), so p-values near 0.05 are interpreted cautiously and effect sizes are always shown.
**Exception, H2b (temporal):** shuffling rows would destroy CO's seasonal structure (an unfair null for a timing test). H2b instead uses **season permutations**: each row receives CO from the same cell in another season, using all 119 non-identity orders of the 5 seasons, so p = (1 + #null ≥ observed) ÷ 120.

4. **G adds skill only if p ≤ 0.05**, i.e. the real model beats at least 95 of the 99 shuffled versions. Otherwise the result is "no detectable effect", and that is reported as such.

**Why this rule (and not a bootstrap of the difference between two experiments):**
- On pure-noise labels the bootstrap rule flagged **7 of 9** contrasts as significant.
- Models with different inputs differ in how much their predictions wobble, and resampling the test set measures that systematic difference very precisely.
- Correcting each experiment by one shuffled twin still gave **2 of 9**.
- In a permutation test both arms have identical inputs, and refitting captures the training randomness.
- **Calibration before freezing (real settings, 19 nulls per test, 5 seeds):**

  | Null labels | Tests | False alarms |
  |---|---|---|
  | Smooth random maps (σ = 6 km, as smooth as L-fd) | H1, H2a, H3, H4 (rotation nulls) | **1 of 20 (5%)** |
  | Independent noise | H2b (season permutations) | **0 of 5** |

  For comparison, row shuffling gave 8 of 12 (smooth maps) and 2 of 5 (H2b). Files: `outputs/phase5/permutation_test_calibration_*.json`.

**Robustness:** each primary effect is recomputed (9 shuffles) with ridge and XGBoost, with 10 and 20 km blocks, and without fold 3. It is called robust if its sign is the same in every variant.

**Secondary results** (experiments A–D vs N0, every split, the ablation) are reported as point estimates only, with no significance claim.

## 8. Predictions (written before any model is run)

| # | Prediction | Reason |
|---|---|---|
| P1 | On L-fd, A scores high in raw R² | Construction link (NO₂ ↔ L-fd, Spearman 0.91) |
| P2 | **H2a: CO adds no detectable spatial skill** on L-fd | CO barely varies between 1 km cells (Phase 2 spatial share 0.02) |
| P3 | H2b: CO may add a little temporal skill on L-fd (leave-one-season-out) | CO's information is seasonal; small effect expected |
| P4 | H1 and H3 significant: activity layers add spatial skill beyond geography, with the gain most visible in the PCMC hold-out (descriptive) | Activity layers should place the PCMC hotspot that geography can't |
| P5 | N1 (shuffled) shows ~0 skill over N0; H4 significant (NO₂ locates emissions in the CO label beyond geography) | Sanity control; NO₂ ↔ L-co Spearman 0.79 |
| P6 | NDBI contributes little or negatively in the ablation | Dry-soil confusion (Phase 2) |
| P7 | On L-co, scores are lower in absolute terms but similar as a fraction of the ceiling | L-co is noisier (ceiling 0.75 in the corridor) |

## 9. Reporting rules

- Every experiment, control and split is reported, including the ones that don't support a prediction.
- Any change to this plan after freezing is recorded as a dated amendment with its reason, and results are shown both ways.
- Secondary comparisons are reported with their intervals, but labelled "secondary"; their significance is not claimed.
- Feature importance (permutation importance on held-out blocks) is *descriptive*. Correlated features share importance (Phase 2 correlation QA).

## 10. History of this plan (before freezing)

| Date | Change | Reason |
|---|---|---|
| 2026-10-10 | Draft written | — |
| 2026-10-10 | Block rule: added "first crossing of 95% of the variance" to the fitted range | The corridor's label variogram has a hole effect (narrow domain); decided before the regional data existed |
| 2026-10-10 | **Block rule changed from the label variogram to the label-error variogram** | On the regional grid the first rule returned 100 km (the fit hit its bound; 2 blocks), because the label has no finite range. No model had been trained. The argument for errors is in §4.1 |
| 2026-10-10 | Folds balanced by cell count | Random block assignment gave folds of 207–1,057 cells |
| 2026-10-10 | Robustness at 10 and 20 km blocks; L-co interpreted mainly on the corridor | Added with the block result |
| 2026-10-10 | **Decision rule replaced by group permutation tests (§7); hypotheses restated as "does group G add skill to a base model including geography"** | Smoke test on noise labels: the bootstrap rule gave 4 of 5, then 7 of 9 false alarms (real settings); a one-twin correction 2 of 9. Pre-freeze; no model had seen a real label |
| 2026-10-10 | **Calibration passed:** rotation tests 1 of 20 false alarms on smooth nulls; H2b season permutations 0 of 5 on noise. Plan ready to freeze | Final check of the decision rule before any real result |
| 2026-10-10 | **Spatial tests switched from row shuffling to rotations ("spin" nulls)** | On smooth random null labels (σ 6 km), row shuffling gave 8 false alarms in 12 tests (H1 stuck at p = 1.00): a shuffled map loses its smoothness, so the real smooth map wins by chance alignment. Pre-freeze; no model had seen a real label |
| 2026-10-10 | H2b switched to season permutations; calibration extended to smooth random null maps | On noise labels the row-shuffled H2b gave p 0.10, 0.05, 0.10 (biased: shuffling destroys CO's seasonal structure). Smooth nulls test the spatial tests under realistic label smoothness |
| 2026-10-10 | Before freezing, from an implementer's read-through: primary model (RF); four primary hypotheses H1–H4; precise spatial/temporal skill and N1 definitions; leave-one-season-out scores temporal skill only; PCMC hold-out descriptive (one area); fold-3 extrapolation handling; L-co experiment list; residual-target scope | Each gap would otherwise have become a choice made after seeing results |
