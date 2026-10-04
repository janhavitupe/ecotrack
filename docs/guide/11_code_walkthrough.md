# Chapter 11 — How to Read the Code (where to start, what calls what)

The repo has ~2,500 lines of Python across 26 files. Don't read them alphabetically. This chapter
gives you **the order to read them in, how each file connects to the next, and how to poke at the
data yourself** so the code stops being abstract.

---

## 11.1 The one rule for reading any script here

Every runnable script ends with:
```python
if __name__ == "__main__":
    run()
```
**Start reading from the bottom.** Find `run()` and read it top to bottom: it's the story of the
script. Each line in `run()` calls a helper function defined higher up. Only jump up to a helper
when you need to know *how* it does its job. The docstring at the very top of each file (the text
in `"""..."""`) says *what* the script does and *why*; read that first.

---

## 11.2 The pipeline: what produces what

Every arrow is a file on disk. A script reads the files on its left and writes the files on its
right. That's how the scripts "talk" to each other: **through files, not by calling each other.**

```
configs/study.yaml ──► (read by EVERY script via config.load_config())

FOUNDATION
  geometry.py ─────────────────────────────► data/interim/corridor.geojson
                                             (corridor_polygon(), cluster_zones() used everywhere)

FEASIBILITY (chapter 5)
  feasibility/g4_verify_waypoints.py ──────► outputs/feasibility/g4_waypoints.json
  feasibility/g4_map.py ───────────────────► outputs/feasibility/g4_map.html
  feasibility/g2_tropomi_coverage.py ──────► outputs/feasibility/g2_tropomi_overpasses.csv ─┐
  feasibility/g3_no2_signal.py ────────────► outputs/feasibility/g3_no2_signal.json         │
  feasibility/g1_oco_soundings.py ─────────► data/interim/oco/oco3_soundings.csv ──────┐    │
                                             outputs/feasibility/g1_oco3_summary.json  │    │
DATA                                                                                   │    │
  acquire/era5_overpass.py  ◄── reads g2_tropomi_overpasses.csv ◄──────────────────────┼────┘
          └────────────────► data/interim/era5/overpass_met.csv ──────────┐            │
  acquire/tropomi_cube.py ─► data/interim/tropomi/cube/*.npz      ──┐     │            │
  acquire/tropomi_cube.py --product co ─► .../cube_co/*.npz ──────┐ │     │            │
  acquire/dem.py ──────────► data/interim/dem_cube_grid.npz ────┐ │ │     │            │
  acquire/edgar.py ────────► data/interim/edgar/*.npz ────────┐ │ │ │     │            │
  acquire/odiac.py ────────► data/interim/odiac/*.npz ──────┐ │ │ │ │     │            │
                                                            │ │ │ │ │     │            │
PHASE 1 (chapter 6) — run in this order                     │ │ │ │ │     │            │
  1 inversion/run_city.py  ◄── cube (+ IQR via qc.py) + ERA5 ◄──────┴─────┘            │
       └─► outputs/phase1/city_fit.json  (source, E(NOx), τ) ─────────────┐            │
  2 inversion/run_divergence.py ◄── cube + ERA5 + city_fit.json           │            │
       └─► outputs/phase1/divergence_totals.json, divergence_map.npz ─────┤            │
  3 inversion/run_co2.py ◄── city_fit + divergence_totals + EDGAR + ODIAC │            │
       └─► outputs/phase1/co2_summary.json ───────────────────────────────┤            │
  4 inversion/run_oco_check.py ◄── divergence_map + co2_summary + OCO soundings ◄──────┘
       └─► outputs/phase1/oco_check.json                                  │
  5 inversion/run_co_ratio.py ◄── CO cube + DEM + EDGAR + city_fit + co2_summary
       └─► outputs/phase1/co_ratio.json   (CO:NOx, CO₂:NOx, revised budget)
  6 inversion/run_seasonal.py ◄── cube + ERA5 + city_fit   └─► seasonal.json
  7 inversion/run_co_divergence.py ◄── CO cube + DEM + ERA5 + co_ratio + divergence_map   └─► co_divergence.json
  8 inversion/temporal_adjust.py ◄── co2_summary + co_ratio + EDGAR temporal profiles   └─► temporal_adjust.json
  9 inversion/mc_budget.py ◄── city_fit + co2_summary + co_ratio + temporal_adjust
       └─► outputs/phase1/mc_budget.json   (the headline: 2.79 Mt/yr annual [1.79–4.36])
 10 inversion/de_sensitivity.py ◄── cube + ERA5 + city_fit   └─► de_sensitivity.json

PHASE 2 (chapter 12)
  grid.py ──────────────────► data/interim/grid/cells.csv, cells.geojson
  acquire/grid_layers_gee.py ◄── cells.geojson ──► layers_monthly.csv (VIIRS, HCHO, ERA5), layers_seasonal.csv (NDVI, NDBI)
  acquire/osm_pbf.py ◄── cells + data/raw/osm/*.osm.pbf ──► layers_roads.csv, layers_landuse.csv (OSM, v2)
  (acquire/roads_osm.py: the earlier Overpass route, superseded)
  acquire/roads_grip.py ◄── cells.geojson ──► layers_roads_grip.csv (GRIP4 fallback)
  features.py ◄── cells + both cubes + DEM + ERA5 + all layers + EDGAR + ODIAC
       └─► data/processed/feature_table_v2.csv (+ .meta.json with SHA-256) ; outputs/phase2/qa_*_v2
  progress_report.py ◄── all results ──► docs/EcoTrack_Progress_Report.pdf
```

**Library files** (not run by themselves; they hold reusable functions):

| File | Provides | Used by |
|---|---|---|
| `config.py` | `load_config()`, the folder paths | everything |
| `geometry.py` | waypoints, `corridor_polygon()`, `cluster_zones()` | feasibility, ee_utils, run_* |
| `qc.py` | `iqr_filter()` | `load_cube()` |
| `acquire/ee_utils.py` | Earth Engine login, `tropomi_qc()`, corridor as an EE geometry | every GEE script |
| `inversion/emg.py` | rotation, binning, line density, EMG, DE fit, emission formula | run_city, run_divergence, run_co_ratio, de_sensitivity, tests |
| `inversion/divergence.py` | mean flux, divergence, emission map, area sums | run_divergence, tests |
| `inversion/run_city.py` | `match_wind()`, `fit_subset()` (incl. the D19 window/slope and quality rule), `fit_window()`, plot colours | the later run_* scripts reuse these |
| `grid.py` | `load_cells()` | Phase 2 scripts |

---

## 11.3 Reading order (10 sessions)

Each session: read the file, then do the "try it" exercise in §11.4. Have chapter 6 open alongside.

| # | Read | Lines | Why this order |
|---|---|---|---|
| 1 | `configs/study.yaml` | 109 | Every setting the code uses. You'll recognise these names everywhere. |
| 2 | `config.py` → `geometry.py` | 18 + 100 | How the config becomes the corridor shape. Short and self-contained. |
| 3 | `acquire/ee_utils.py` → `feasibility/g2_tropomi_coverage.py` | 60 + 110 | Your first Earth Engine script: QC, valid fractions, counting days. |
| 4 | `acquire/tropomi_cube.py` → `qc.py` | 145 + 57 | How the data cube is built and cleaned. **`load_cube()` is the function every analysis starts with.** |
| 5 | **`inversion/emg.py`** | 160 | **The most important file.** Read it function by function with chapter 6 §6.5 next to it: `offsets_km` → `rotate` → `RotatedGrid` → `bin_days` → `line_density` → `emg_unit` → `fit_emg` → `emissions`. |
| 6 | `inversion/run_city.py` (`run()` at line 183, then the helpers) + `tests/test_emg.py` | 247 + 70 | How emg.py is used on real data, and how the synthetic test proves it works. |
| 7 | `inversion/divergence.py` → `run_divergence.py` → `run_co2.py` | 64 + 177 + 209 | The map, the zones, and the NOx → CO₂ conversion. |
| 8 | `run_co_ratio.py` (+ `tests/test_co_step.py`), then `run_oco_check.py` | 245 + 212 | The CO breakthrough and the OCO check. |

| 9 | `run_seasonal.py`, `temporal_adjust.py`, `mc_budget.py` | ~100 each | Seasons, midday → annual, Monte Carlo: short scripts built on the earlier ones. |
| 10 | `grid.py` → `acquire/grid_layers_gee.py` → `features.py` (chapter 12) | 100 + 130 + 190 | Phase 2: how the feature table is assembled and QA'd. |

Skip until later: `g1_oco_soundings.py` (mostly download logistics), `g4_map.py` (mostly HTML),
`tropomi_gee.py` (a week-1 test), `de_sensitivity.py` (a loop around `fit_emg`), `roads_osm.py` / `roads_grip.py`
(download logistics), `run_co_divergence.py` (an exploratory map).

---

## 11.4 Poke at the data yourself (do this alongside reading)

Open a terminal in `D:\EcoTrack`, activate the venv, type `python`, and paste these. Reading code is
ten times easier once you've *seen* the arrays it works on.

**Session 2: the corridor**
```python
from ecotrack.geometry import corridor_polygon, waypoints
c = corridor_polygon()
print(c.geom_type, c.bounds)          # one Polygon; its lon/lat extent
print(waypoints()[0])                 # what one waypoint looks like
```

**Session 4: the cube**
```python
from ecotrack.acquire.tropomi_cube import load_cube
import numpy as np
no2, times, lat, lon, frac = load_cube()
print(no2.shape)                      # (1004, 90, 95): days × rows × columns
print(times[:3])                      # first three overpass times (UTC)
print(np.nanmedian(no2))              # typical NO₂ column, mol/m² (~3e-5)
day0 = no2[0]                         # one day's image (90 × 95), with NaN where clouds were
print(np.isnan(day0).mean())          # fraction of cloudy/missing pixels that day
```
Plot one day and the average:
```python
import matplotlib.pyplot as plt
plt.imshow(np.nanmean(no2, axis=0)); plt.colorbar(); plt.title("mean NO2"); plt.show()
```

**Session 5: rotation in miniature**
```python
from ecotrack.inversion.emg import rotate
print(rotate(5, 0, 1, 0))   # wind toward the east, point 5 km east  → (5, 0): downwind
print(rotate(0, 5, 1, 0))   # point 5 km north                       → (0, 5): to the side
print(rotate(5, 0, -1, 0))  # wind toward the west, point 5 km east  → (-5, ...): upwind
```

**Session 6: the real fit's numbers**
```python
import json
r = json.load(open("outputs/phase1/city_fit.json"))["results"][0]
print(r["fit"])        # a, x0, mu, sigma, b, r2
print(r["emission"])   # tau_h, e_nox_kg_s, ...
```
Then redo the Level 2 hand calculations from chapter 8.

**Session 6: run the tests and break one on purpose**
```powershell
python -m pytest -q                        # 11 passed
```
Change `TRUE_E_NO2` in `tests/test_emg.py` to 1.0 and rerun. It still passes, because the method
recovers whatever emission you plant. Now change the assertion tolerance from `rel=0.20` to `rel=0.05`:
it **fails**, because the EMG bias is ~12%. That's the bias from chapter 6, seen with your own eyes.
Undo both changes afterwards (`git checkout tests/test_emg.py`).

**Session 7: the emission map**
```python
import numpy as np, matplotlib.pyplot as plt
d = np.load("outputs/phase1/divergence_map.npz")
plt.imshow(d["e_nox_mol_m2_s"], cmap="RdBu_r", vmin=-2e-8, vmax=2e-8); plt.colorbar(); plt.show()
```
You should see the two red hotspots (central Pune bottom-right, PCMC above-left of it).

---

## 11.5 How to trace a single number back to its source

Take the headline **2.98 Mt CO₂/yr** and walk it backwards:
1. `outputs/phase1/co_ratio.json` → `co2_mt_yr_co_constrained`, computed in `run_co_ratio.py` as
   `satellite_nox_kt_yr_midday × r_central / 1000`.
2. `satellite_nox_kt_yr_midday` (16.5) comes from `co2_summary.json`, made by `run_co2.py` from
   `city_fit.json` → `e_nox_kg_s` × seconds per year.
3. `e_nox_kg_s` (0.522) comes from `run_city.py` → `fit_subset()` → `emg.fit_emg()` and `emg.emissions()`.
4. `fit_emg()` fitted the line density from `emg.line_density()`, built from `emg.bin_days()` on
   the cube from `load_cube()` (IQR-filtered by `qc.py`) and the wind from `match_wind()`.
5. `r_central` (181) is the mean of the feasible sector scenarios in `run_co_ratio.py`, which uses the
   CO step (`step_from()` on `anomalies()` of the CO cube) and the EDGAR sector files.

Doing this exercise for 2–3 numbers is the fastest way to understand how the pieces fit together.

---

## 11.6 Patterns you'll see repeatedly (so they stop looking strange)

| Pattern | Example | Meaning |
|---|---|---|
| `cfg = load_config()` then `cfg["inversion"]["wind_level"]` | everywhere | read a setting from study.yaml |
| `no2[sel]` with `sel` a True/False array | `run_city.py` | keep only the days where `sel` is True (e.g. windy days) |
| `np.nanmean`, `np.nanmedian` | everywhere | averages that ignore NaN (missing pixels) |
| `axis=0` | `np.nanmean(no2, axis=0)` | average over days → one map |
| `ee.ImageCollection(...).filterDate(...).map(...)` | GEE scripts | a description of work sent to Google; nothing runs until `.getInfo()` |
| `.getInfo()` | GEE scripts | "now actually compute it and send me the result" |
| `json.loads((OUT / "x.json").read_text())` | run_* scripts | read a previous step's results |
| `(OUT / "x.json").write_text(json.dumps(...))` | run_* scripts | save this step's results for the next step |
| `@dataclass` | `RotatedGrid`, `Emission` | a simple container for named values |
| `def f(...): """..."""` | everywhere | the docstring explains the function; read it first |
| `pytest.approx(x, rel=0.2)` | tests | "equal within 20%" |
