# Chapter 13 — Phase 3: Building the CO₂ Labels, Step by Step

Phase 3 makes the **answers** the machine-learning models will learn to predict: how much fossil CO₂ each
1 km cell emits in each season. This chapter explains why that's hard, how we did it, how we checked it,
and the one decision the data forced on us (D21).

---

## 13.1 What a "label" is, and why we have to build one

In machine learning, a **label** is the correct answer for an example. For a spam filter it's "spam / not
spam"; for us it's "this cell emitted X tonnes of CO₂ per km² per year in this season".

The problem: **nobody measures CO₂ emissions per square kilometre in Pune.**
- There are no sensors on every factory and road.
- OCO-3 can't see Pune's plume (D11).
- The inventories disagree with each other by 3.2× and aren't allowed as truth (D2).

So the label must be **constructed** from what we *can* measure. Phase 1 gave us two satellite emission maps:
- the **NO₂ flux-divergence map** (where NOx is emitted);
- the **CO flux-divergence map** (where CO is emitted).

Phase 1 also gave us the city's total CO₂ (NOx × 163). A label spreads the total over the cells using a map.

## 13.2 The trap: circularity

Imagine labelling each cell's CO₂ by its night-light brightness, then asking a model "can night lights predict
CO₂?". Of course it can: we *made* the answer from night lights. The model would score brilliantly and prove
nothing. That's **circularity** (decision D2).

The proposal's original label had exactly this problem for Experiment D: it spread CO₂ using night lights, NDBI and
roads, the very features Experiment D uses. So we use the satellite emission maps instead (D10/D16). But:
- **L-fd** is built from NO₂, and NO₂ is Experiment A's feature. That's circular for A.
- **L-co** is built from CO. It never touches NO₂, so it tests A fairly, but it's circular with the CO feature,
  so we drop CO when using it.

Two labels from two different gases let each experiment be tested fairly by at least one of them.

## 13.3 The recipe (`src/ecotrack/labels.py`)

**L-fd** for cell c in season s:

  label = share_NO₂(c) × E_NOx(s) × 162.7

1. Take the multi-year NO₂ emission map (the Phase 1 map, rebuilt and checked to be identical).
2. **Smooth it to ~5 km** (a 5 × 5-pixel box average). TROPOMI pixels are ~3.5 × 5.5 km, so the map has no real
   detail finer than that. Pretending otherwise would add noise, not information.
3. Read the smoothed value at each cell's centre (bilinear interpolation). Divide by the map's total within 25 km of
   the source. That's the cell's **share** per km².
4. Multiply by the city NOx for that season (from the Phase 1 seasonal EMG fits: 0.43–0.73 kg/s) and by the
   CO₂:NOx ratio 162.7 (constrained by TROPOMI CO, D12).
5. Convert kg m⁻² s⁻¹ to **t CO₂ km⁻² yr⁻¹**: × 10⁶ m²/km² × 31,557,600 s/yr ÷ 1,000 kg/t.

**L-co** for cell c:

  label = share_CO(c) × (multi-year city CO₂)

This is the same steps 1–3 using the CO emission map. The city total enters only as **one constant number**, so NO₂
sets the overall size but not the pattern.

**Worked example (cell c000_021, near Shivajinagar, 2019–20):**
- Its NO₂ share is 0.00137 per km², i.e. 0.137% of the city's 25 km total sits in this 1 km² cell.
- The city emits 0.434 kg NOx/s that season, × 162.7 = 70.6 kg CO₂/s.
- 0.00137 × 70.6 = 0.0965 kg CO₂/s from this cell.
- × 31,557,600 s/yr ÷ 1,000 = **3,043 t CO₂/yr**. That's the value in `labels_v1.csv`.

## 13.4 Uncertainty for every label

A label without an error bar can't be judged. We used the **bootstrap** again (chapter 6):
1. Resample the satellite days with replacement 200 times (100 for CO).
2. Rebuild the map each time and recompute every cell's share.
3. The spread of those shares is the label's random uncertainty.

For L-fd we add the season total's own uncertainty.

What the bootstrap does *not* include is the **common scale**: the CO₂:NOx ratio (±5%), NOx/NO₂ (±7.6%) and the
EMG method bias (12%). Those multiply every cell by the same factor, so they can't change which cells are high or
low. They're recorded in `labels_v1.meta.json`.

**Noise ceiling.** If labels are noisy, even a perfect model can't match them exactly. The best possible R² is
**1 − (average noise variance ÷ total label variance)**:
- L-fd: 0.97. Very clean, though optimistic, since it only counts sampling noise.
- L-co: 0.75.

Remember this when the models report scores: an R² of 0.7 on L-co is near-perfect.

## 13.5 The checks (why we trust it)

| Check | What we found |
|---|---|
| Is the rebuilt NO₂ map identical to Phase 1's? | Yes, exactly |
| Do the cells add up to Phase 1's corridor shares? | 20.7% vs 21.0% (NO₂); 14.3% vs 14.5% (CO). The tiny gap is smoothing spreading a little past the corridor edge |
| Does the smoothing size matter? | 3 or 7 px instead of 5: r ≥ 0.98 with the main labels |
| Is one fixed map OK for every season? | NO₂: each season's own map correlates r ≥ 0.98 with the 5-year map, so yes. CO: r 0.24–0.86, so per-season CO maps are too noisy |
| Unit conversion and total conservation | `tests/test_labels.py` |

## 13.6 Decision D21: the data said "no" to seasonal CO

**The plan:** L-co would also change by season, using each season's CO total.

**The test:** the same rule we used for NO₂ in Phase 1. A season-to-season change is real only if the
spread *between* seasons is bigger than the uncertainty *within* a season.
- NO₂ scored **2.8**, a clear pass.
- CO's seasonal totals (226–266 mol/s, each ±28–48) scored **0.49**, a fail. Their "seasonal changes" are smaller
  than their noise.

**Decision D21:** L-co uses the same 5-year total in every season. It is a **spatial-only** label: it tests whether a
model gets *where* right; L-fd tests *where* and *when*. The seasonal CO numbers are still computed and saved, and
the switch is one line in the config (`co_seasonal_scale`).

**Why this isn't "changing the method after seeing the results":** the rule was fixed in advance and applied the
same way to both gases. Writing down the rule and the numbers is what makes it honest.

## 13.7 What we learned about the labels

1. **The two labels agree on where** (cell-level r = 0.93) but put different amounts in the corridor (20.7% vs 14.3%).
   CO is weaker far from the city: L-co is near zero, even slightly negative, in rural Talegaon, where its
   uncertainty is bigger than the value itself.
   - **Negative labels** (11.6% of L-co) are kept. Clipping them to zero would push the average up, which is a bias.
2. **85% of L-fd's variation is between cells, 15% between seasons.** L-co is 100% spatial.
3. **The labels are really a 5 km field.** Neighbouring 1 km cells aren't independent; the corridor contains only about
   11 independent 5 km × 5 km areas. So in Phase 5, cross-validation must hold out blocks of at least ~5 km, or
   the model could "cheat" by copying its neighbour.
4. **Circularity, measured:**
   - L-fd correlates **0.91** with the NO₂ feature, its recipe.
   - But L-co, which never used NO₂, still correlates **0.79** with NO₂. So NO₂ really does carry information about
     emissions; it's not just the recipe talking.
   - Surprise: L-co correlates only 0.27 with the CO *feature*. The CO column barely changes between cells (Phase 2),
     while the label comes from the emission map, a transform of how the column changes with the wind.
5. **Inventories:** ODIAC's *pattern* matches our labels well (Spearman 0.89), because it's drawn with night lights,
   and our emissions follow the city's lights. Its *total* is still 3.2× too big. EDGAR's coarse blocks match less (0.66 / 0.48).

## 13.8 Files

- `src/ecotrack/labels.py`: builds both labels, the QA and the figures.
- `data/processed/labels_v1.csv`: 1,340 rows with columns:
  - `cell_id`, `season`, `cluster`;
  - `label_fd`, `label_fd_sd`, `label_fd_annual`;
  - `label_co`, `label_co_sd`, `label_co_annual`;
  - `share_fd_per_km2`, `share_co_per_km2`.
- `data/processed/labels_v1.meta.json`: constants, common-scale uncertainty, SHA-256.
- `outputs/phase3/qa_labels.json`: every check above.
- `outputs/phase3/figures/`: label maps, seasons, per-cell agreement.
- Full write-up: [../phase3_report.md](../phase3_report.md).

## 13.9 What's next (Phase 4)

1. Average the monthly features into seasons and join them to the labels.
2. Standardise them (subtract the mean, divide by the spread), so no feature dominates by its units.
3. Define the cross-validation folds: spatial blocks ≥ 5 km, leave-one-cluster-out, leave-one-season-out.
4. Apply the rules from §13.7:
   - with L-co, drop CO;
   - with L-fd, report Experiment A as the "construction baseline".
