# Chapter 12 — Phase 2: Building the Feature Table, Step by Step

Phase 2 puts **every data layer onto one 1 km grid**, producing a table with one row per grid cell per
month: the input for the machine-learning experiments in Phases 4–6. This chapter covers what was
built, why, in what order, and every problem met on the way.

---

## 12.1 Why a grid and a table at all?

The ML models (Phases 5–6) need examples of the form "for this place and time, here are the inputs (NO₂,
night-lights, roads, wind…) and here is the answer (CO₂)". So:
- **place** = a 1 km × 1 km square ("cell") of the corridor;
- **time** = a month (October–May, 2019–2024, so 40 months);
- **row** = one cell in one month → 268 cells × 40 months = **10,720 rows**.

The answer (the label) is built in Phase 3; Phase 2 builds the inputs (the "features").

## 12.2 Step 1 — The grid (`src/ecotrack/grid.py`, decision D15)

1. Take the corridor polygon (D9) and convert it to **UTM 43N metres**, so 1 km really is 1 km.
2. Lay a chessboard of 1 km squares over it, aligned to whole kilometres.
3. Keep a square if **at least 50%** of its area is inside the corridor.
4. For each cell, record:
   - an id `c<row>_<col>`;
   - centre lat/lon;
   - fraction inside the corridor;
   - **cluster** (C1/C2/C3, from the nearest waypoint);
   - distance to the Phase 1 source.

**Result: 268 cells** (C1 91, C2 63, C3 114) covering 268 km², against a corridor of 269 km², so the 50% rule loses almost nothing.
Files: `data/interim/grid/cells.csv` (table) and `cells.geojson` (shapes for Earth Engine).

## 12.3 Step 2 — Checking what's available (before writing code)

We asked Earth Engine which collections exist over Pune:

| Collection | Status | Use |
|---|---|---|
| `NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG` (night lights) | ✅ to 2026 | human activity |
| `NOAA/VIIRS/DNB/ANNUAL_V22` | ✗ empty for 2021 | not used |
| `COPERNICUS/S2_SR_HARMONIZED` (Sentinel-2) | ✅ 6 images over Pune in Jan 2021 | NDVI, NDBI |
| `COPERNICUS/S5P/OFFL/L3_HCHO` (formaldehyde) | ✅ | chemistry proxy |
| `COPERNICUS/S5P/OFFL/L3_O3` (ozone) | ✅ but a *total* column | rejected (see D14) |

(Asking for "the newest image" of the *whole global* Sentinel-2 archive hung the first check: it's enormous.
Always filter to your area first.)

## 12.4 Decision D14 — the chemistry proxy

The proposal asked for an "atmospheric chemistry proxy (O₃, VOC fields from MERRA-2/CAMS)". Why we changed it:
- **Reanalysis chemistry** (MERRA-2/CAMS) is ~50 km, far coarser than our 1 km cells.
- **TROPOMI O₃** is the *total* ozone column, dominated by the stratospheric ozone layer 20–30 km up, so it
  says almost nothing about city-level chemistry.
- **TROPOMI HCHO (formaldehyde)** is the standard satellite indicator of **reactive VOCs** (volatile organic
  compounds, the other ingredient of urban photochemistry). It comes on the same grid, with the same QC.
- **ERA5 2 m temperature and solar radiation** are the *drivers* of photochemistry (heat and sunlight).

So D14: chemistry proxy = **HCHO + temperature + solar radiation**.

## 12.5 Step 3 — Earth Engine layers onto the cells (`acquire/grid_layers_gee.py`)

For each of the 40 months:
- **VIIRS** night-light radiance, masked if the month had no cloud-free coverage (`cf_cvg`);
- **HCHO**: monthly mean of QC'd overpasses (cloud ≤ 0.3, solar zenith ≤ 70°);
- **ERA5**: 2 m temperature and solar radiation at **07 UTC** (≈ the overpass hour).

And for each of the 5 seasons:
- **Sentinel-2** median composite of all scenes with < 60% cloud, after removing cloud and shadow pixels
  with the **SCL** (scene classification) band, keeping classes 4 vegetation, 5 bare, 6 water, 7 unclassified.
  - **NDVI** = (B8 − B4)/(B8 + B4): vegetation (near-infrared vs red).
  - **NDBI** = (B11 − B8)/(B11 + B8): built-up (short-wave infrared vs near-infrared). Concrete and roofs
    reflect more SWIR than NIR.

Averaging onto cells uses Earth Engine's `reduceRegions(mean)` over the 268 cell polygons.

**Two bugs, both caught by looking at the first output lines:**
1. **VIIRS and HCHO came back blank (NaN) for every cell**, while ERA5 worked. Earth Engine names the output of
   a *single-band* image `mean` instead of the band name, so our code looked for a column that didn't exist.
   Fix: `ee.Reducer.mean().setOutputs([name])`.
2. **ERA5 was missing in 7,560 of 10,720 rows.** We reduced a 27.8 km raster at its *native* scale over 1 km
   polygons: most cells contain no ERA5 pixel *centre*, so they got nothing. Fix: sample at 1 km, so each
   cell takes the value of the ERA5 cell it sits in. After the fix: 0 missing, and VIIRS/HCHO were checked to be
   bit-identical to the first run (max difference 0.0).

## 12.6 Step 4 — Roads: the saga (D20)

The proposal says OpenStreetMap roads. What happened:
1. `roads_osm.py` asks the **Overpass API** for drivable roads in 0.1° tiles and sums the length per cell per class
   (major = motorway/trunk/primary; mid = secondary/tertiary; minor = residential/unclassified/living street).
2. **The server refused (504 Gateway Timeout, 429 Too Many Requests)** again and again. The OSM servers
   were overloaded that day, and **Geofabrik** (the alternative OSM download site) was down too, while our own
   internet was fine (Google answered in 2 s).
3. Mitigations, one after another:
   - smaller tiles (0.05°);
   - **cache every tile to disk**, so reruns resume;
   - **rotate across three mirror servers**;
   - **light queries**: one query per road class with `out skel geom` (geometry only, no tags).
4. Still only **16 of 35 tiles** after many hours (the background job kept hitting its time limit and being restarted).
5. **Fallback: GRIP4** (Global Roads Inventory Project; Meijer et al., 2018), a published global roads dataset
   available inside Earth Engine (`projects/sat-io/open-datasets/GRIP4/South-East-Asia`). Its road type
   `GP_RTP` (1 highway … 5 local) maps onto our three classes. `roads_grip.py` computes the lengths per cell
   **on Google's servers in minutes**.
6. **Caveat:** GRIP4's sources are older (~2014) and its local roads are sparse: minor roads median 0.07 km per cell.

**Decision D20:** feature table **v1 uses GRIP4**, with the source recorded. When the OSM download completes, **v2**
will use OSM and keep GRIP4 as `grip_*` cross-check columns.

**How it ended (2026-10-04).** Three days later Overpass was *still* returning 504, but Geofabrik was back. Geofabrik
publishes the whole OpenStreetMap database cut into regions, as one file per region per day, in the compact
**`.osm.pbf`** format. Instead of asking a busy server for small pieces, we downloaded the **India western zone**
(221 MB) once:
1. `curl -L -o data/raw/osm/western-zone-<date>.osm.pbf https://download.geofabrik.de/asia/india/western-zone-latest.osm.pbf`.
2. Check the file against the **MD5 checksum** Geofabrik publishes next to it, which proves it arrived complete.
3. `python -m ecotrack.acquire.osm_pbf` reads it with **pyosmium** (`pip install osmium`). It scans every object,
   keeps road ways of our classes inside the box, and assembles `landuse=industrial` **areas** (polygons, including
   multipolygon relations). Then it clips both to the cells exactly as before. It takes 2.5 minutes with no server.

Lesson: **when an API is the bottleneck, look for a bulk download of the same data.** The dated file also makes the
snapshot reproducible, which a live API is not.

**The comparison (why it was worth it):** OSM and GRIP4 agree on where the big roads are (Spearman 0.84), but GRIP4
has almost no local streets: median minor road 0.07 km per cell vs **4.2 km in OSM**. So v1's minor-road column was
nearly empty, and v2 fixes it.

## 12.7 Step 5 — Atmosphere, weather and inventories from our own files (`features.py`)

- **NO₂ and CO per cell-month**: from the Phase 1 cubes (NO₂ IQR-filtered; CO terrain-normalised), as the monthly
  mean map **interpolated bilinearly at each cell centre**. The cube pixels are 0.01° (~1.1 km), so a 1 km cell may
  contain no pixel centre; interpolation avoids empty cells. QA columns `no2_n`/`co_n` count the overpasses behind each value.
- **Weather per month**: from the overpass-matched ERA5 file: mean 850 hPa wind speed, the *vector-mean* direction
  (from the mean u and v; averaging angles directly is wrong, because 350° and 10° average to 180°), boundary layer, and
  `frac_ese` (share of days with east-southeast wind). These are **the same for all cells in a month** (one ERA5 cell).
- **Inventories** as `ref_*` columns: EDGAR NOx/CO/CO₂ density of the 0.1° cell, and ODIAC CO₂ density of the
  nearest 1 km pixel. **Reference only, never features** (the proposal's rule; D2).
- **OCO-3** is deliberately **not** a column (8 dates in total; D11).

## 12.8 Step 6 — QA (proposal Phase 2 step 5)

`features.py` writes `outputs/phase2/qa_feature_table_v1.json` and `qa_histograms.png`:
- **missing-data audit**: 0 missing in v1;
- **per-feature statistics** (min, 1%, median, 99%, max) and **histograms**;
- **spot check** of 8 random cells in January 2022.

What the histograms told us (all sensible):
- NO₂ is highest in C1 and lowest in C3, as in Phase 1.
- CO has two peaks (seasonal).
- Night lights range from 1.9 (rural) to 63 (dense core) and rise from a median of 15.6 (2019) to 23.6 (2024).
- Weather columns are "steppy" (one value per month).
- **EDGAR is blocky** (~16 distinct values over 268 cells: its 0.1° cells are bigger than ours).

## 12.9 The result

`data/processed/feature_table_v1.csv`: **10,720 rows, 16 features, 0 missing**, with its road source in
`feature_table_v1.meta.json`. Every column is described in `docs/data_dictionary.md`. The table is **committed to git**
(unlike raw/interim data), because it's a frozen deliverable and some of its sources can change over time.

## 12.9b Version 2: the final Phase 2 table (2026-10-04)

`data/processed/feature_table_v2.csv`: **10,720 rows, 17 features, 0 missing.** What changed:
- **Roads from OpenStreetMap** (12.6), with GRIP4 kept as `grip_road_*_km` so anyone can compare.
- **New feature `industrial_frac`**: the share of each cell covered by OSM `landuse=industrial`. The proposal
  lists "industrial-land fraction" for the Phase 3 weights. Overlapping polygons are merged first, so no area is
  counted twice. **Check it makes sense:** the top cells are MIDC Bhosari (97% industrial), the Chinchwad/Akurdi belt
  and Talegaon MIDC, exactly the estates anyone in Pune would name.
- **Freezing properly:** the meta file stores the **SHA-256** hash of the CSV, a fingerprint that changes if even one
  digit changes. Rebuilding gave the identical hash, so the build is deterministic.

**Two new QA checks, and what they teach:**
1. **Correlation matrix** (`qa_correlation_v2.png`, Spearman = correlation of ranks, robust to skewed data). The
   strongly related pairs are the expected ones:
   - minor ↔ total roads (0.93);
   - boundary layer ↔ sunlight (0.90), temperature ↔ sunlight (0.80);
   - wind direction ↔ east-wind fraction (−0.84).
   We keep them all, but when the ML ablation says which inputs matter, correlated inputs **share** the credit,
   which is important to remember when interpreting it.
2. **Spatial variance share**: for each feature, how much of its variation is *between cells* (where) rather than
   *between months* (when).
   - Roads, industry, NDVI/NDBI, VIIRS: ~0.9–1.0 (mostly where).
   - NO₂: 0.34.
   - CO and HCHO: **0.02**. Their 1 km variations are tiny next to their seasonal swings.
   - Weather: 0, since one ERA5 cell covers the corridor.

   **So:** at 1 km the model can only learn *where* emissions are from the activity layers (and partly NO₂). CO,
   HCHO and weather help with *when*. We wrote this down **before** training any model. That is honest, and it
   shapes Phase 4: spatial-block cross-validation, so the model can't just memorise each cell.

## 12.10 Other snags met along the way
- **Windows console encoding:** printing "→" crashed when the output was piped (the cp1252 console has no such
  character). Prints were switched to ASCII.
- **C: drive full (76 MB)**: Windows refused to start Python ("insufficient system resources"). It was fixed by clearing
  the pip cache (5 GB) and temp files. Keep several GB free on C:, because Windows needs it for memory paging.

## 12.11 What's left in Phase 2
- Nothing: **Phase 2 is complete** with feature table v2.
- Next, Phase 3 builds the labels (design in `docs/phase3_design.md`, decision D16, awaiting the guide).
