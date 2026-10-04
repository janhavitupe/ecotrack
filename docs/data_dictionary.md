# EcoTrack — Data Dictionary: Feature Table v2 (current) and v1

**File:** `data/processed/feature_table_v2.csv`, built by `python -m ecotrack.features`
(meta file `feature_table_v2.meta.json`: road source, OSM extract, feature list, SHA-256 of the CSV).
**v1** (`feature_table_v1.csv`, GRIP4 roads, 16 features) is kept unchanged as the earlier frozen version.
**v2 changes:** roads from OpenStreetMap (Geofabrik extract), the new `industrial_frac` column, and `grip_road_*_km` cross-check columns.
**Shape:** 10,720 rows = **268 grid cells × 40 months** (October–May, Oct 2019 – May 2024).
**One row** = one 1 km × 1 km grid cell in one month.
**Grid:** UTM 43N (EPSG:32643) squares, ≥ 50% inside the corridor (D15); `data/interim/grid/cells.csv` / `cells.geojson`.

**Role column:**
- **ID**: identifies the row.
- **Context**: describes the cell; can be used for grouping and splits, but not as a model feature.
- **Feature**: a model input.
- **QA**: a data-quality count.
- **Reference**: inventories, for comparison only. **Never use these as features** (proposal §5 design rule, D2), and **never as labels**.

## Identifiers and context

| Column | Role | Meaning | Units / values |
|---|---|---|---|
| `cell_id` | ID | Grid cell: `c<row>_<col>` in the UTM grid | e.g. `c015_019` |
| `month` | ID | Calendar month | `YYYY-MM` |
| `season` | Context | October–May season the month belongs to | e.g. `2021-22` |
| `lat`, `lon` | Context | Cell centre | degrees (WGS84) |
| `cluster` | Context | Corridor cluster of the nearest waypoint | `C1_shivajinagar_kasarwadi`, `C2_pcmc`, `C3_dehu_talegaon` |
| `frac_in_corridor` | Context | Share of the cell's area inside the corridor | 0.5–1 |
| `dist_to_source_km` | Context | Distance to the Phase 1 emission source (18.485 N, 73.855 E) | km |

## Atmospheric features (satellite)

| Column | Role | Meaning | Source & processing | Units | Time step |
|---|---|---|---|---|---|
| `no2` | Feature | Tropospheric NO₂ column | TROPOMI OFFL L3 (GEE). QC: cloud ≤ 0.3, solar zenith ≤ 70°, GEE qa pre-filter, usable overpasses only, IQR outlier removal (temporal, k = 3; D13). Monthly mean, bilinear at the cell centre | mol/m² | monthly |
| `co_norm` | Feature | Terrain-normalised CO column (column ÷ exp(−z/8.4 km), z = SRTM elevation smoothed to ~5 km) | TROPOMI OFFL L3 CO (GEE); solar zenith ≤ 70° | mol/m² (sea-level equivalent) | monthly |
| `hcho` | Feature | Tropospheric formaldehyde column, the VOC/chemistry proxy (D14) | TROPOMI OFFL L3 HCHO (GEE); cloud ≤ 0.3, solar zenith ≤ 70°; monthly mean over the cell | mol/m² | monthly |

## Meteorological features (ERA5)
All four overpass-matched variables are the same for every cell in a month: the corridor lies within ~one 0.25° ERA5 cell. They describe *when* (transport and dilution conditions), not *where*.

| Column | Role | Meaning | Source & processing | Units | Time step |
|---|---|---|---|---|---|
| `ws850` | Feature | Mean wind speed at 850 hPa at TROPOMI overpass | ERA5 hourly, nearest hour to each usable overpass, averaged over the month | m/s | monthly |
| `wd850` | Feature | Vector-mean wind direction (FROM) at 850 hPa | from the monthly mean u, v | degrees from north | monthly |
| `blh_m` | Feature | Mean boundary-layer height at overpass | ERA5 | m | monthly |
| `frac_ese` | Feature | Share of overpass days with wind from 45–180° (the east-southeast regime: Pune upwind of the corridor) | ERA5 850 hPa | 0–1 | monthly |
| `t2m_k` | Feature | 2 m air temperature at 07 UTC (~overpass), a photochemistry driver (D14) | ERA5 hourly, sampled at 1 km (each cell takes its ERA5 cell's value) | K | monthly |
| `ssrd_j_m2` | Feature | Surface solar radiation in the 07–08 UTC hour, a photochemistry driver (D14) | ERA5 hourly accumulation | J/m² per hour (÷ 3600 ≈ W/m²) | monthly |

## Human-activity features

| Column | Role | Meaning | Source & processing | Units | Time step |
|---|---|---|---|---|---|
| `viirs_rad` | Feature | Night-time light radiance | VIIRS DNB monthly, stray-light corrected (`VCMSLCFG`); months with no cloud-free coverage masked | nW/cm²/sr | monthly |
| `ndvi` | Feature | Vegetation index (B8 − B4)/(B8 + B4) | Sentinel-2 SR harmonized, SCL cloud/shadow mask, seasonal median, mean over the cell | −1 … 1 | seasonal |
| `ndbi` | Feature | Built-up index (B11 − B8)/(B11 + B8) | same as NDVI | −1 … 1 | seasonal |
| `road_major_km` | Feature | Length of major roads in the cell | **v1: GRIP4** types 1–2 (highways, primary), the OSM fallback. **v2: OpenStreetMap** motorway/trunk/primary (+ links). The source is recorded in `feature_table_*.meta.json` | km per cell (= km/km²) | static |
| `road_mid_km` | Feature | Secondary + tertiary roads | v1: GRIP4 types 3–4; v2: OSM | km | static |
| `road_minor_km` | Feature | Local roads | v1: GRIP4 type 5 (**sparse coverage: median 0.07 km/cell**); v2: OSM residential/unclassified/living_street | km | static |
| `road_total_km` | Feature | Sum of the three | as above | km | static |
| `industrial_frac` | Feature (v2) | Share of the cell covered by industrial land | OSM `landuse=industrial` polygons (Geofabrik extract), merged so overlaps count once, intersected with the cell in UTM | 0 … 1 | static |

**Cross-check columns (v2 only):** `grip_road_*_km`, the GRIP4 values when OSM is the primary source.

## QA columns

| Column | Role | Meaning |
|---|---|---|
| `no2_n` | QA | Valid NO₂ overpasses at the cell (nearest pixel) that month |
| `co_n` | QA | Same for CO |

## Reference columns (inventories): comparison only

| Column | Meaning | Source | Units | Time step |
|---|---|---|---|---|
| `ref_edgar_nox_t_km2_yr` | EDGAR NOx (as NO₂) emission density of the 0.1° cell containing the cell centre | EDGAR v8.1 AP TOTALS (2023–24 use 2022) | t/km²/yr | annual |
| `ref_edgar_co_t_km2_yr` | EDGAR CO emission density | EDGAR v8.1 AP | t/km²/yr | annual |
| `ref_edgar_co2_t_km2_yr` | EDGAR fossil CO₂ emission density | EDGAR v8.0 GHG | t/km²/yr | annual |
| `ref_odiac_co2_t_km2_month` | ODIAC fossil CO₂ density of the nearest 1 km pixel (carbon × 44/12) | ODIAC v2024 (2024 months use the same month of 2023) | t CO₂/km²/month | monthly |

## Not in the table, and why
- **OCO-3 / OCO-2 XCO₂:** too sparse for per-cell features (8 dates in total; D11).
- **Labels (the CO₂ per cell):** built in Phase 3 from the flux-divergence shares (D10), kept in a separate file so they can't leak into the features.
