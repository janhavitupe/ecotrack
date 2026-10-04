# Chapter 3 — The Data, A to Z

For each dataset: **what it is · who makes it · how it's measured · what the numbers mean ·
how we got it · what we did with it · the traps we hit.**

A quick map first:

| Dataset | Measures | Type | Used for |
|---|---|---|---|
| TROPOMI NO₂ | NO₂ column | Satellite | The core: emissions, the map |
| TROPOMI CO | CO column | Satellite | Sector fingerprint (CO:NOx) |
| OCO-3 / OCO-2 | XCO₂ | Satellite | Direct CO₂ check |
| ERA5 | Wind, boundary layer, pressure | Weather model ("reanalysis") | Moving the plumes |
| SRTM | Ground height | Radar map | Terrain correction for CO |
| EDGAR | Emissions by sector | Inventory | NOx→CO₂ ratio, comparison |
| ODIAC | Fossil CO₂ emissions | Inventory | Comparison |
| OpenStreetMap | Roads, places, industrial land | Crowd-sourced map | Corridor geometry; roads + industrial land (v2, Geofabrik extract) |
| TROPOMI HCHO | Formaldehyde column | Satellite | Chemistry/VOC proxy (Phase 2, D14) |
| VIIRS DNB | Night-time lights | Satellite | Human activity (Phase 2) |
| Sentinel-2 | Surface reflectance → NDVI, NDBI | Satellite | Vegetation / built-up (Phase 2) |
| GRIP4 | Road network | Published dataset | Roads in feature table v1 (D20) |
| EDGAR temporal profiles | Hourly/weekly/monthly emission patterns | Inventory tables | Midday → annual (D17) |

---

## 3.1 TROPOMI (Sentinel-5 Precursor): NO₂ and CO

**What:** TROPOMI (TROPOspheric Monitoring Instrument) is a spectrometer on the European Space
Agency's **Sentinel-5 Precursor (S5P)** satellite, launched in October 2017 under the EU's
Copernicus programme.

**How it measures:** it looks down and splits reflected sunlight into its colours (a
**spectrum**). Every gas absorbs light at its own tell-tale wavelengths, like a barcode. How deep
those absorption lines are tells you how much gas the light passed through. NO₂ is read from
visible/blue light; CO from short-wave infrared.

**Orbit and timing:** the satellite is in a **sun-synchronous orbit**. It crosses the equator at
about **13:30 local time**, every day, and covers the whole Earth daily. Over Pune the overpass
falls between **06:00 and 08:00 UTC = 11:30–13:30 IST**.
- UTC = world standard time; IST = UTC + 5:30.

**Pixel size:** each measurement ("ground pixel") covers about **3.5 × 5.5 km** (since August 2019;
before that 3.5 × 7 km, which is one reason our study starts in October 2019). The CO pixels are
larger (~5.5 × 7 km).

**Processing levels:**
- **L1**: raw light measurements.
- **L2**: gas amounts per original ground pixel, in the satellite's swath geometry, with a
  **qa_value** (0–1 quality score) and cloud information.
- **L3**: L2 re-gridded onto a regular map grid. **We used L3 from Google Earth Engine.**
  - Collection IDs: `COPERNICUS/S5P/OFFL/L3_NO2` and `COPERNICUS/S5P/OFFL/L3_CO`.
  - **OFFL** = "offline", the carefully processed version (vs NRTI, near-real-time).
  - Grid: **0.01° ≈ 1.1 km** (scale 1113.2 m).
  - **Important:** a 3.5 × 5.5 km TROPOMI pixel spans several 1.1 km grid cells, and GEE gives
    them all the same value. So neighbouring cells aren't independent (this bit us, see chapter 7).

**The variables (bands) we used:**
- NO₂: `tropospheric_NO2_column_number_density` (**mol/m²**), `cloud_fraction` (0–1),
  `solar_zenith_angle` (degrees).
- CO: `CO_column_number_density` (**mol/m²**, the total column), `solar_zenith_angle`.
- **Solar zenith angle**: how far the sun is from straight overhead. Above 70° the sun is low,
  light paths are long and slanted, and retrievals get unreliable.

**Quality control we applied:**
1. `cloud_fraction ≤ 0.3` (NO₂ only; the CO product has no such band). Clouds hide the air below.
2. `solar_zenith_angle ≤ 70°`.
3. Earth Engine's own built-in quality pre-filter. **The GEE product has no `qa_value` band**, so
   the proposal's "qa ≥ 0.7" can't be applied by us. We say this honestly in the Methods chapter.
4. An **overpass counts as usable** if ≥ 50% of the corridor's 230 pixels survive QC.
5. **IQR outlier removal** (NO₂): each pixel is compared with its own history; values outside
   Tukey's far-out fences (k = 3) are removed. That's 0.09% of pixels (chapter 6, §6.2).

**What we downloaded:** a **"cube"**: for every usable overpass, the full image over a ~100 km box
around Pune (73.35–74.30°E, 18.15–19.05°N), **90 × 95 pixels**, on one fixed grid, so day 1's
pixel (i, j) is exactly the same place as day 900's.
- **NO₂: 1,004 overpasses; CO: 907 overpasses** (October–May, 2019–2024).
- Stored as one file per month: `data/interim/tropomi/cube/YYYY-MM.npz` (CO in `cube_co/`).
- A `.npz` is a compressed bundle of NumPy arrays. Ours holds `no2` (days × rows × columns),
  `time_ms`, `lat`, `lon` and `valid_fraction`. The CO files reuse the array name `no2`; it's
  just the column array.

**Typical numbers:** NO₂ background ~3 × 10⁻⁵ mol/m², Pune up to ~9 × 10⁻⁵. CO ~0.037 mol/m²:
large and fairly uniform, with Pune adding only ~2%.

---

## 3.2 OCO-3 and OCO-2: direct CO₂

**What:** NASA's **Orbiting Carbon Observatories**. They measure **XCO₂** (column-average CO₂, in ppm)
from reflected sunlight in three near-infrared bands.
- **OCO-2**: its own satellite (launched 2014), crossing at ~13:30. It sees a **narrow track**, 8
  footprints across (~10 km wide), each ~1.3 × 2.3 km. It rarely crosses a small area.
- **OCO-3**: the spare instrument, mounted on the **International Space Station** (since 2019).
  - The ISS orbit drifts, so it passes at **different times of day** (our dates: 08:52–16:04 IST).
  - It has a pointing mirror, which allows **Snapshot Area Maps (SAMs)**: it scans an ~80 × 80 km
    patch around a chosen target in ~2 minutes. **Pune is a SAM target**, a lucky finding.
  - The record has gaps: no data 20 Oct – 26 Nov 2019, and nothing from December 2023 to May 2024.

**Data product:** the **"Lite" files** (`OCO3_L2_Lite_FP` and `OCO2_L2_Lite_FP`, version 11).
- **One NetCDF file per day, covering the whole globe.**
- Each measurement is a **"sounding"** with: `latitude`, `longitude`, `time`, `xco2` (ppm),
  `xco2_uncertainty` (ppm), `xco2_quality_flag` (**0 = good**, 1 = bad), `sounding_id`, and
  `Sounding/operation_mode` (0 nadir = straight down; 1 glint = at the sun's reflection over water;
  2 target; 3 transition; **4 SAM**).
- **NetCDF4** is a scientific file format built on **HDF5** (a container for big arrays). We read it
  with `h5py`.

**How we got it:**
- **NASA Earthdata** login; the files are served by **GES DISC** (Goddard Earth Sciences Data and
  Information Services Center).
- In your Earthdata profile you **must approve the "NASA GESDISC DATA ARCHIVE" application**. We
  first approved the similarly named "Test" one by mistake, which gave "403 Forbidden".
- The `earthaccess` Python library searches NASA's catalogue (**CMR**) and streams files.

**Traps we hit:**
- **Searching by bounding box returns almost every day**, because every file is global. You have
  to open each file and count the soundings that actually fall near Pune (script G1).
- **Versions:** OCO-2's newest version (11.3r) covers only 2024; 2019–2023 are in 11.2r. Choose
  the newest version *per day*, or you silently lose four seasons.

**What we found:** 8 usable dates (7 OCO-3, mostly SAMs, plus 1 OCO-2). 100–900 good soundings each.
Single-sounding noise ~0.5–1.1 ppm. Pune's expected signal is ~0.02–0.15 ppm, **too small** (chapter 6, §6.8).

---

## 3.3 ERA5: the weather

**What:** a **reanalysis** from ECMWF (the European Centre for Medium-Range Weather Forecasts).
- A reanalysis runs a weather model that is continuously corrected by millions of real observations
  (stations, balloons, aircraft, satellites). The result is a complete, consistent weather record
  for every hour since 1940.
- **ERA5** = the 5th generation. Resolution **0.25° ≈ 28 km**, **hourly**.

**How we got it:** Google Earth Engine collection `ECMWF/ERA5/HOURLY`.

**Variables used:**

| Band | Meaning | Units |
|---|---|---|
| `u_component_of_wind_10m`, `v_component_of_wind_10m` | Wind at 10 m | m/s |
| `u_component_of_wind_100m`, `v_component_of_wind_100m` | Wind at 100 m | m/s |
| `u_component_of_wind_850hPa`, `v_component_of_wind_850hPa` | Wind at 850 hPa (~1 km above Pune) | m/s |
| `boundary_layer_height` | Depth of the mixed layer | m |
| `surface_pressure` | Air pressure at the ground (for the OCO ppm conversion) | Pa |

**What we did:** for every usable TROPOMI overpass, took the **nearest hour** of ERA5 at each
cluster centre (`src/ecotrack/acquire/era5_overpass.py` → `data/interim/era5/overpass_met.csv`),
and computed speed and direction.
- **Finding:** clusters C2 and C3 fall in the **same** 0.25° cell, so effectively there is one
  wind per overpass for the whole corridor.

**Key numbers:** median wind speed 2.5 m/s (10 m), 3.2 (100 m), **3.5 (850 hPa)**. Median
boundary layer 1.66 km. **October–March winds from the east-southeast; April–May from the
west-northwest.**

---

## 3.4 SRTM: ground height

**What:** the **Shuttle Radar Topography Mission** (NASA, 2000). The Space Shuttle used radar to
map the height of the land almost worldwide, at ~30 m resolution. A map of heights is called a
**DEM** (Digital Elevation Model).

**How we got it:** GEE image `USGS/SRTMGL1_003`, averaged to our 0.01° grid
(`src/ecotrack/acquire/dem.py`). In our box: 14–1180 m, median 642 m.

**Why:** the CO terrain correction (chapter 2, §2.2; chapter 6, §6.9).

---

## 3.5 EDGAR: the European inventory

**What:** the **Emissions Database for Global Atmospheric Research**, by the European Commission's
Joint Research Centre (JRC). Emissions for every country, sector and gas, on a **0.1° (~11 km)
global grid**, as **tonnes per grid cell per year**.

**Versions we used (same activity data, FT2022, so their ratios are consistent):**
- **v8.1 AP** (air pollutants): **NOx** and **CO**. NOx is reported as NO₂ mass.
- **v8.0 GHG** (greenhouse gases): **fossil CO₂**.
- Years 2019–2022 (totals), plus every sector for 2021.

**Sector codes** (what's in each file):

| Code | Sector | Code | Sector |
|---|---|---|---|
| IND | Industrial combustion | TRO | Road transport |
| RCO | Residential & commercial (homes, shops) | ENE | Power generation |
| REF_TRF | Refineries, fuel transformation | CHE | Chemical processes |
| AGS | Agricultural soils | AWB | Agricultural waste burning |
| TNR_Other | Off-road / rail | TNR_Aviation_LTO | Aircraft landing/take-off |
| NEU, PRU_SOL, NMM, NFE, … | Minor industrial/process sectors | TOTALS | Sum of all |

**How we got it:** direct download from the JRC server
(`jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/EDGAR/datasets/...`). Each file is a global zip
(~16 MB); we cut out the Pune box and deleted the global copy (`src/ecotrack/acquire/edgar.py`).

**Role, per the proposal's design rule: a prior and a comparison, never "ground truth".**
Using it as the truth would be circular.

**Key numbers (within 25 km of central Pune):** NOx 21.1 kt/yr, fossil CO₂ 3.63 Mt/yr.
CO₂:NOx = **172** (166–176 across years). Sector ratios range from 115 to 393.

---

## 3.6 ODIAC: the Japanese CO₂ inventory

**What:** the **Open-source Data Inventory for Anthropogenic CO₂**, by NIES (Japan). Fossil CO₂
only, on a **1 km monthly grid**. National totals are spread onto the map mainly using **satellite
night-time lights** (bright = more emissions), plus known power-plant locations.

**Units: tonnes of CARBON per 1 km cell per month.** Multiply by 44/12 for CO₂. We didn't guess this:
we looked it up in NASA's US GHG Center documentation, after spotting a 2.6× mismatch with EDGAR.

**How we got it:** NASA's **US GHG Center** hosts it as cloud-optimised GeoTIFFs. Its raster API
(**titiler**) crops the Pune box on the server and sends back a small NumPy array
(`src/ecotrack/acquire/odiac.py`). 35 months, October 2019 – December 2023 (v2024 ends there).

**Key number:** **11.8 Mt CO₂/yr** within 25 km, **3.2× EDGAR**. The two inventories disagree hugely.

---

## 3.7 OpenStreetMap (OSM): the geography

**What:** a free, crowd-edited world map. We used it three ways:
1. **Nominatim** (OSM's place-name search): "where is Khadki?" → coordinates (G4).
2. **Overpass API** (OSM's database query service): "give me every road tagged as the Old
   Pune–Mumbai Highway" and "every polygon tagged `landuse=industrial`" (259 areas, including
   MIDC Bhosari).
3. **Map tiles**: the background of our check map (via CARTO, because OSM's own tile server blocks
   pages opened from a file).

**OSRM**, a routing engine built on OSM data, was tried for a driving-route centreline and
rejected (chapter 7).

---

## 3.7b Datasets added in later work

**TROPOMI HCHO (formaldehyde)**: same instrument and Earth Engine L3 pipeline as NO₂
(`COPERNICUS/S5P/OFFL/L3_HCHO`, band `tropospheric_HCHO_column_number_density`, mol/m²; QC cloud ≤ 0.3, solar
zenith ≤ 70°). HCHO is made when VOCs (volatile organic compounds, from vehicles, solvents, vegetation) are
oxidised, so it's the standard satellite indicator of reactive VOCs. Used as the **chemistry proxy** (D14),
because TROPOMI's O₃ product is a *total* column dominated by the stratosphere. Typical Pune value ~2.4 × 10⁻⁴ mol/m².

**VIIRS Day/Night Band (night lights)**: the VIIRS instrument on the Suomi-NPP satellite photographs the Earth at
night; brightness tracks human activity. We use NOAA's **monthly stray-light-corrected composite**
(`NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG`): `avg_rad` in nW/cm²/sr, plus `cf_cvg` (how many cloud-free nights went
into the month; zero → masked). Pune corridor: 2–63, median rising 15.6 (2019) → 23.6 (2024).

**Sentinel-2 (Copernicus, ESA)**: two satellites taking 10–60 m multispectral images every ~5 days. We use the
surface-reflectance product `COPERNICUS/S2_SR_HARMONIZED`:
- bands B4 (red), B8 (near-infrared), B11 (short-wave infrared);
- the **SCL** scene-classification band, to drop cloud and shadow pixels.

From these: **NDVI** = (B8 − B4)/(B8 + B4) (vegetation) and **NDBI** = (B11 − B8)/(B11 + B8) (built-up). These are
seasonal medians of 40–47 scenes per season.

**GRIP4 (Global Roads Inventory Project v4)**: Meijer et al. (2018), Environmental Research Letters 13, 064006. A
harmonised global road map built from national datasets and OSM, hosted in Earth Engine's community catalogue
(`projects/sat-io/open-datasets/GRIP4/South-East-Asia`). The road type `GP_RTP` runs from 1 highway, 2 primary,
3 secondary and 4 tertiary to 5 local. Used for feature table v1 when the OSM servers were overloaded (D20). Sources ~2014;
local roads sparse.

**EDGAR CO (v8.1 AP)**: same download and format as EDGAR NOx; used for the sector CO:NOx ratios (D4/D12).

**EDGAR temporal profiles** (Crippa et al., 2020, Scientific Data 7, 121): how each sector's emissions vary by
**hour** (per month and day type), **weekday** and **month**, per country/region.
- `EDGAR_temporal_profiles_r1.xlsx`: monthly profiles. India has its own only for residential (1A4) and fires;
  other sectors use world region 7.
- `auxiliary_tables.rar`: `hourly_profiles.csv`, `weekly_profiles.csv`, `weekdays.csv`, `weekenddays.csv`. Extracted
  with Windows' built-in `tar.exe`.

Used to convert our midday October–May rate to an annual mean (D17).

## 3.8 Formats, grids and where each file lives

| Format | What it is | Where we met it |
|---|---|---|
| **NetCDF / HDF5** (.nc) | Scientific container for multi-dimensional arrays with metadata | EDGAR, OCO |
| **GeoTIFF / COG** | Image file with map coordinates; COG = "cloud-optimised", so you can read part of it over the internet | ODIAC |
| **.npz** | NumPy's compressed array bundle | Our cubes, maps |
| **CSV** | Plain table | OCO soundings, ERA5 matches |
| **JSON** | Structured text (dictionaries/lists) | All our results in `outputs/` |
| **YAML** | Human-friendly config text | `configs/study.yaml` |
| **GeoJSON** | JSON for map shapes | `data/interim/corridor.geojson` |

**Folder conventions:**
- `data/raw/`: original downloads (only EDGAR's temporary zips).
- `data/interim/`: processed data we built (cubes, soundings, clipped inventories, the DEM, ERA5
  matches, the corridor).
- `outputs/`: results and figures.
- `data/raw/` and `data/interim/` are **not in git** (too big; regenerated by the acquire scripts).
- `data/processed/` (the frozen feature table, ~4.5 MB) **is** committed: it's a deliverable, and it depends on external
  services that can change over time (Earth Engine reprocessing, OSM edits).

---

## 3.9 How much data, in the end

| Dataset | Amount |
|---|---|
| TROPOMI NO₂ | 1,004 overpasses × 8,550 pixels |
| TROPOMI CO | 907 overpasses |
| OCO-3 | 893 days scanned → 7 strong dates |
| OCO-2 | 1,177 days scanned → 1 strong date |
| ERA5 | 1,031 overpass-hours × 3 points |
| EDGAR | 3 gases × (4 years totals + 19 sectors for 2021) |
| ODIAC | 35 months |
| SRTM | 1 map |
| TROPOMI HCHO, VIIRS | 40 months × 268 cells (monthly means) |
| Sentinel-2 | 5 seasons × 40–47 scenes |
| GRIP4 roads | 268 cells (lengths per class) |
| OSM Geofabrik extract | 1 file, 221 MB (India western zone) → 36,082 road ways + 223 industrial areas in the box |
| OSM | 10 places, the highway (134 road segments), 259 industrial areas |

Total on disk: tens of MB, because we only kept the Pune box.
