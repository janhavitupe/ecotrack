# Chapter 4 — Tools, Accounts and Setup

## 4.1 Accounts (all free)

| Account | Why | How |
|---|---|---|
| **Google Earth Engine (GEE)** | TROPOMI, ERA5, SRTM: Google stores the data and runs calculations on its computers | Register at code.earthengine.google.com/register → "Use without cost" → Academia & Research → create a **Cloud project**. Ours: `ecotrack-509517` |
| **NASA Earthdata** | OCO-2/OCO-3 | Sign up at urs.earthdata.nasa.gov, verify your email, then **Applications → Authorized Apps → Approve "NASA GESDISC DATA ARCHIVE"** (not the "Test" one) |
| **GitHub** | Back up and version the code | github.com; repository `janhavitupe/ecotrack` (keep it private until submission) |

**What Earth Engine is:** a Google service holding petabytes of satellite and weather data. You write
Python (via the `earthengine-api` library) describing *what* to compute: "average this collection
over this box". Google's servers do it and send back only the small result. That's why we never
downloaded whole TROPOMI files.

## 4.2 Python and the virtual environment

- **Python 3.11.**
- A **virtual environment** (`.venv`) is a private folder of Python libraries for this project,
  so it can't clash with other projects.
  ```powershell
  python -m venv .venv                 # create it (once)
  .venv\Scripts\Activate.ps1           # switch it on (each new terminal)
  pip install -r requirements.txt      # install the libraries
  pip install -e .                     # install our own code as the package "ecotrack"
  ```
  - If PowerShell refuses to run the Activate script:
    `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- **Log in once:**
  - `earthengine authenticate`
  - `python -c "import earthaccess; earthaccess.login(strategy='interactive', persist=True)"`.
    This saves your Earthdata login to `C:\Users\<you>\_netrc`.
- **Our C: drive was full.** pip needs temporary space, so we pointed its temp and cache folders at D:
  ```bash
  TMP='D:\EcoTrack\.piptmp' TEMP='D:\EcoTrack\.piptmp' PIP_CACHE_DIR='D:\EcoTrack\.piptmp\cache' pip install ...
  ```

## 4.3 The libraries and what each one does

| Library | Job in EcoTrack |
|---|---|
| **numpy** | Arrays and maths (the cube is a numpy array) |
| **pandas** | Tables (CSV), dates, joining the wind to overpasses |
| **scipy** | `differential_evolution` (the optimiser), `least_squares`, special functions (`erfc`, `erfcx`), image filters |
| **matplotlib** | All figures |
| **pyyaml** | Reads `configs/study.yaml` |
| **shapely** | Geometry: lines, buffers, polygons, "is this point inside?" |
| **pyproj** | Converts lat/lon ↔ UTM metres |
| **h5py** | Reads NetCDF4/HDF5 files (EDGAR, OCO) |
| **earthengine-api** (`ee`) | Talks to Google Earth Engine |
| **earthaccess** | Searches and streams NASA data (OCO) |
| **pytest** | Runs the automated tests in `tests/` |
| **openpyxl** | Reads the EDGAR temporal-profile Excel file (D17) |

## 4.4 The code, file by file

```
src/ecotrack/
├── config.py              loads configs/study.yaml; defines folder paths
├── geometry.py            waypoints, corridor polygon (highway ± 3.5 km + Talegaon MIDC), cluster zones
├── qc.py                  IQR outlier filter (3 variants; we use "temporal", k = 3)
├── grid.py                Phase 2: the 1 km UTM grid (268 cells), load_cells()
├── features.py            Phase 2: assembles feature table v1 (cell × month) + QA
├── acquire/               ── getting data ──
│   ├── ee_utils.py        Earth Engine login, geometries, the TROPOMI cloud/zenith mask
│   ├── tropomi_gee.py     first test export (week 1)
│   ├── tropomi_cube.py    downloads the NO₂ / CO cubes; load_cube() applies IQR for NO₂
│   ├── era5_overpass.py   wind + boundary layer for each overpass
│   ├── dem.py             SRTM elevation on the cube grid
│   ├── edgar.py           EDGAR NOx / CO / CO₂, clipped
│   ├── odiac.py           ODIAC, clipped via the GHG Center API
│   ├── grid_layers_gee.py Phase 2: VIIRS, HCHO, ERA5 t2m/radiation (monthly), Sentinel-2 NDVI/NDBI (seasonal) per cell
│   ├── roads_osm.py       Phase 2: OSM roads via the Overpass API (superseded: servers overloaded)
│   ├── osm_pbf.py         Phase 2: OSM roads + industrial land from a Geofabrik .osm.pbf file (used for v2)
│   └── roads_grip.py      Phase 2: GRIP4 road length per cell in Earth Engine (fallback, D20)
├── feasibility/           ── go/no-go checks (chapter 5) ──
│   ├── g1_oco_soundings.py      count OCO soundings over Pune
│   ├── g2_tropomi_coverage.py   usable TROPOMI days per month
│   ├── g3_no2_signal.py         is NO₂ above background?
│   ├── g4_verify_waypoints.py   waypoints vs OpenStreetMap
│   └── g4_map.py                interactive check map
└── inversion/             ── the science (chapter 6) ──
    ├── emg.py             rotation, line density, EMG model, DE fit, emission formula
    ├── run_city.py        city-scale EMG inversion + sensitivity runs + figures
    ├── divergence.py      flux-divergence maths
    ├── run_divergence.py  emission map, zone totals, bootstrap, sensitivity
    ├── run_co2.py         NOx → CO₂, EDGAR/ODIAC comparison, uncertainty budget
    ├── run_oco_check.py   OCO-3/OCO-2 plume-scaling check
    ├── run_co_ratio.py    TROPOMI CO step → CO:NOx → sector mix → CO₂:NOx
    ├── run_seasonal.py    EMG per season + flux-divergence corridor share (Phase 3 groundwork)
    ├── run_co_divergence.py CO flux-divergence map (an NO₂-independent emission map, D16)
    ├── temporal_adjust.py midday Oct–May rate → annual mean with EDGAR temporal profiles (D17)
    ├── mc_budget.py       Monte Carlo uncertainty (D18)
    └── de_sensitivity.py  36 DE settings test
tests/
├── test_emg.py            fake plume → does EMG recover the known emission?
├── test_divergence.py     same, for flux divergence
├── test_co_step.py        fake inert tracer + fake terrain → does the CO step work?
└── test_qc.py             fake spikes → does the IQR filter catch them without clipping the plume?
```

**Every script runs the same way:** `python -m ecotrack.<folder>.<script>`, for example
`python -m ecotrack.inversion.run_city`. The `-m` means "run this module from the installed package".

## 4.5 The config file (`configs/study.yaml`), the single source of truth

**Every** threshold lives here, never hidden in the code. That makes the project auditable: an
examiner can see every choice in one file. Section by section:

- `accounts.gee_project`: your Earth Engine project.
- `study.period` and `season_months`: October 2019 – May 2024; months 10, 11, 12, 1–5.
- `region.bbox`: the quick-query rectangle. `region.regional_bbox` is the wider box for the G3
  background. `corridor_buffer_km: 3.5`, `grid_res_km: 1`, `utm_epsg: 32643`.
- `waypoints`: the 10 places (OSM positions); used as labels and cluster centres.
- `centreline`: the highway line the corridor is built from (D9).
- `extra_areas`: the Talegaon MIDC circle (2.5 km).
- `clusters`: which waypoint belongs to C1/C2/C3. `cluster_radius_km: 5`.
- `tropomi`: collection, band, `cloud_fraction_max: 0.3`, `solar_zenith_max: 70`,
  `min_valid_fraction: 0.5`, and `iqr: {method: temporal, k: 3.0}`.
- `tropomi_co`: the same for CO.
- `oco`: products, `good_quality_flag: 0`, the padding around the box, `min_good_soundings_per_day: 20`.
- `inversion`:
  - `cube_box` (the ~100 km box) and `cube_res_deg: 0.01`;
  - `wind_level: "850"`;
  - `calm_max_ms: 2` (calm threshold), `windy_min/max_ms: 2–8`;
  - `source_search_radius_km: 15`;
  - `rot_res_km: 2`, `along_km: [-40, 60]`, `across_halfwidth_km: 20` (rotated-grid geometry);
  - `nox_no2_ratio: 1.32`;
  - `de: {popsize 60, mutation [0.5, 1.0], recombination 0.7, maxiter 2000, seed 42}`;
  - `bootstrap: 200`;
  - `fit_along_max_km: 45` and `background_slope: true` (D19).
- `tropomi_co`: the CO collection and QC (solar zenith ≤ 70°).
- `phase2`: `cell_km: 1`, `min_frac_in_corridor: 0.5` (D15), and the HCHO, VIIRS and Sentinel-2 collections and their QC (D14).

## 4.6 Git in five commands

```powershell
git status                          # what changed?
git add .                           # stage everything (except what .gitignore excludes)
git commit -m "what I did"          # save a snapshot
git push                            # upload to GitHub
git log --oneline                   # history
```
- `.gitignore` excludes `.venv/`, `data/`, big data files, the `_netrc` password file, and
  `images/`.
- **Never commit passwords.** Early on, the Earthdata password was pasted into a chat. Change it
  if you haven't already.

## 4.7 Where things run and how long they take

| Step | Where the work happens | Time |
|---|---|---|
| G2 coverage, G3 signal, cubes, ERA5, DEM | Google's servers (GEE) | 5–30 min each |
| G1 OCO scan | Your PC, streaming from NASA | hours (resumable) |
| EDGAR / ODIAC | Your PC | a few minutes |
| EMG inversion (`run_city`) | Your PC (CPU) | ~10–15 min |
| Flux divergence, CO₂, CO ratio | Your PC | a few minutes each |
| DE sensitivity (36 fits) | Your PC | ~15–20 min |
| Tests (`pytest`) | Your PC | ~15 s |
