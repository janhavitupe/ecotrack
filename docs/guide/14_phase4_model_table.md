# Chapter 14 — Phase 4: A Bigger Training Area, the Model Table, and Fair Testing

Phase 4 gets the data ready for machine learning, and makes sure the test will be **fair**. This chapter
explains why we enlarged the training area, what a variogram is, how the cross-validation splits were
chosen, and why we wrote the analysis plan *before* training anything.

---

## 14.1 The problem a good supervisor would raise

After Phase 3 we had 1,340 labels (268 cells × 5 seasons), which sounds like plenty. Three problems hid
behind that number:

1. **The labels are smooth.** They come from a ~5 km map, so neighbouring 1 km cells are almost copies of
   each other. Many cells, few *independent* pieces of information.
2. **The labels are mostly one slope:** high near central Pune, low far away. Any feature that's also high near
   Pune (NO₂, night lights, roads) will "predict" them, without telling us much.
3. **Experiment B** adds CO, which barely changes between 1 km cells (Phase 2). It will probably show no gain.

## 14.2 Fix 1: a bigger training area (decision D22)

The satellite emission maps cover a ~90 km box, not just the corridor. So we made a **regional grid**:
every 1 km cell within 30 km of the source (and safely inside the satellite box), plus all corridor cells.
That's **2,894 cells** instead of 268.

- **Same alignment:** the 268 corridor cells are exactly the same squares in both grids.
- **One switch:** set `ECOTRACK_GRID=region` and every script uses the regional grid. Outputs get a
  `_region` suffix, so nothing from the corridor is overwritten.
- **Proof the pipeline didn't change:** for the 268 shared cells, every feature and label came out
  identical on both grids (differences around 10⁻¹⁵, i.e. computer rounding).

The models now *train* on the whole region; the corridor stays the main place we *report* results.

## 14.3 Three engineering snags (and the lessons)

1. **"MemoryError" reading OpenStreetMap.**
   - To build road geometries, osmium remembers the coordinates of every point in the 221 MB file.
   - With 0.2 GB of RAM free and a nearly full C: drive (Windows needs C: space to extend memory), it crashed.
   - Fix: keep that memory in a temporary file on D: (`sparse_file_array`), deleted afterwards.
   - Lesson: watch free disk space on C:, because Windows uses it as overflow memory.
2. **Earth Engine took 6.5 minutes per month.**
   - The code built one list of all 2,894 cell shapes and sent the *whole list* with every request, even
     when a request used only 400 of them.
   - Building each request from its own 400 cells made it **3.6× faster**.
   - Lesson: think about what actually travels over the network.
3. **Bugs that only appear on new data.**
   - The label figure read cell shapes from the corridor folder (crash: unknown cell id).
   - A check summed "corridor share" over every regional cell (117%: impossible, so caught).
   - Both fixed; the corridor labels were rebuilt **byte-for-byte identical**, proving the fix changed nothing else.

## 14.4 The model table (`src/ecotrack/tensor.py`)

Models need one row per example. Our example is **one cell in one season**:
1. **Average the monthly features over the season's months.**
   - Exception: **wind direction** is an angle. The average of 350° and 10° is 0° (north), but a plain
     average says 180° (south)! So each direction becomes two numbers, sin and cos, which can be averaged safely.
   - A test checks exactly this case.
2. **Join the labels** (L-fd, L-co and their uncertainties).
3. **Add split columns** (below).

Result: `model_table_v1_region.csv`, 14,470 rows.

## 14.5 What a variogram is

A **variogram** answers: *on average, how different are two cells that are h km apart?*
- Take every pair of cells.
- Compute half the squared difference of their values.
- Average the pairs in distance bins (0–1 km, 1–2 km, …).

That average is the **semivariance**:
- **Close cells:** small semivariance (they're alike).
- **Far cells:** the semivariance levels off at the **sill**, where the cells are no longer related.
- **Practical range:** the distance where the curve reaches 95% of the sill.

**Why we need it.** In **spatial cross-validation** we hide some areas (test) and train on the rest. If a test
cell has a near-twin in training, the model can just copy it and look brilliant. So test areas must be
**blocks** at least as wide as the range.

## 14.6 The surprise: the labels never level off (decision D23)

- The labels' own variogram gave 7 km in the corridor.
- In the region it **kept rising to 30 km**: the labels are smooth at *every* scale, so there's no range. The rule
  returned 100 km blocks (2 blocks), which is useless.

**What can actually leak** between neighbours?
1. **The smooth pattern.** A model can learn "near Pune = high" from location alone. But that is precisely
   what our **geography-only null model** measures, and every experiment is scored as skill *above* it. Handled.
2. **Shared errors.** One bad satellite day, smoothed over 5 km, puts the *same error* into several neighbouring
   labels. A model trained on one of them would "predict" the error in its neighbour. **This is what blocks must prevent.**

**So we measured how far label errors spread:**
1. Rebuild the NO₂ map 30 times from **bootstrap** resamples of the days.
2. Subtract the main map: what's left is pure error.
3. Compute the variogram of that error.

It levels off nicely at **14.7 km**, so the blocks are **15 km** squares. Two cross-checks:
- **A common-factor check.** Each resampled map is divided by its own 25 km total, which scales all cells together and could fake long-range correlation. Holding that total fixed gives the same 14.5 km.
- **The corridor alone gives 9.5 km**, because its narrow shape has few long cell pairs across it.

**What this means:** the region has 23 blocks, roughly **13 independent areas**. The corridor alone has about 3. That number,
not "14,470 rows", is the honest size of our dataset.

**Folds.** The 23 blocks are dealt into 5 folds. Random dealing gave folds of 207 to 1,057 cells, because edge blocks are
only partly inside the circle. So blocks are dealt **largest first, each to the emptiest fold**: 577–582 cells per fold.
Tested for balance and for giving the same answer every run.

## 14.7 The four ways we'll test the models

| Test | Train on | Test on | Question |
|---|---|---|---|
| 15 km block folds (×5) | 4 folds | 1 fold | General skill (repeated with 10 and 20 km blocks for robustness) |
| Corridor transfer | everything outside the corridor | the corridor | Does it work in an area it never saw? |
| PCMC hold-out | cells > 5 km from PCMC | PCMC | Can it find a hotspot that distance alone can't predict? |
| Leave one season out | 4 seasons | 1 season | Does it get the *timing* right? (L-fd only) |

## 14.8 The analysis plan, and why it comes first

`docs/phase5_analysis_plan.md` writes down *everything* before any model is trained:
- the experiments;
- the controls:
  - **N0**, the geography-only null;
  - **N1**, shuffled features (should score ~0);
  - a target with the distance slope removed (does anything predict what geography can't?);
- the splits and the model settings, with no per-experiment tuning;
- **the decision rule:** a difference between experiments counts only if its 95% interval (from
  resampling whole blocks) excludes zero;
- **predictions** (for example "B ≈ A in spatial skill").

**Why first?** If you try many things after seeing results, something will always look like it "works" by
luck. Committing the plan to git first leaves a timestamp: the rules came before the results. This is called
**pre-registration**, and it's what makes a "no difference" result credible instead of embarrassing.

The plan has a **history table**. The block rule was changed before freezing (§14.6), and that's written down too,
with the reason. Changing a plan is fine; hiding the change is not.

## 14.9 Files

- `src/ecotrack/grid.py`: corridor and regional grids (`ECOTRACK_GRID`).
- `src/ecotrack/tensor.py`: season means, label join, error variogram, blocks, folds, splits.
- `data/processed/model_table_v1_region.csv` (+ meta): the table Phase 5 trains on.
- `outputs/phase4_region/variogram.png`: the figure in §14.6.
- `docs/phase4_report.md`: full write-up. `docs/phase5_analysis_plan.md`: the rules for Phases 5–6.
- `tests/test_tensor.py`: wind averaging and fold tests (17 tests in total).
