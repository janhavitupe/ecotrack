# Chapter 9 — Glossary (A–Z)

**850 hPa**: a pressure level ≈ 1.5 km above sea level (~1 km above Pune). We use the wind there to move the plumes.

**Ablation (study)**: removing one ingredient at a time to see how much each contributes (Phase 6).

**Air mass (relative)**: the amount of air above a point compared with sea level, ≈ exp(−z/H). Used to remove terrain from CO.

**Background (V_bg, B)**: the "clean air" level to subtract. For G3 and flux divergence: the 10th percentile of the NO₂ map. For EMG: the fitted constant B.

**Bias**: a consistent error in one direction (e.g. EMG +12%). Doesn't average away.

**Bootstrap**: estimating uncertainty by re-running on 200 random resamples (with replacement) of the days.

**Boundary layer (BLH)**: the lowest, sun-mixed layer of air, where pollution spreads (median 1.66 km at midday).

**Buffer**: the area within a distance of a line or point (corridor = highway ± 3.5 km).

**Burden (a)**: the total NO₂ in the city's plume (mol), from the EMG fit (51,748 mol).

**Calm composite**: the average NO₂ on days with wind < 2 m/s; its peak marks the source.

**CARTO / Esri tiles**: background map images used in our check map.

**CMR**: NASA's Common Metadata Repository, the searchable catalogue behind `earthaccess`.

**Cluster (C1/C2/C3)**: our three corridor zones: Shivajinagar–Kasarwadi; PCMC; Dehu Road–Talegaon.

**CO**: carbon monoxide, from incomplete burning; lives for weeks; our sector fingerprint.

**CO:NOx ratio**: moles of CO emitted per mole of NOx. Pune: 21.2; EDGAR: 16.0.

**CO₂:NOx ratio**: tonnes of CO₂ per tonne of NOx; converts NOx to CO₂. EDGAR 172; CO-constrained 181.

**COG (cloud-optimised GeoTIFF)**: a map image you can read part of over the internet (ODIAC).

**Column (density)**: the amount of a gas above 1 m² of ground (mol/m²).

**Composite**: an average of many images.

**Confidence interval (95% CI)**: a range containing the true value 95% of the time.

**Corridor**: our study strip: highway centreline ± 3.5 km + Talegaon MIDC, 269 km².

**CR (crossover rate)**: the DE setting: the chance each parameter comes from the mutant (0.7).

**Cube**: our stack of daily TROPOMI images on one fixed grid (1004 × 90 × 95).

**DE, Differential Evolution**: a population-based optimiser used to fit the EMG (NP 300, F 0.5–1.0, CR 0.7).

**DEM**: Digital Elevation Model, a map of ground height (SRTM).

**Detection threshold**: the smallest emission a dataset could reliably detect (OCO: ~8–15 Mt/yr for Pune).

**Dithering**: re-drawing DE's F randomly each generation (from 0.5–1.0).

**Divergence (∇·)**: net outflow per area of a flux field; positive = a source.

**Downwind / upwind**: the direction the wind blows toward / comes from.

**e-folding distance (x₀)**: the distance over which NO₂ falls to 37% (≈ 25 km); x₀ = w·τ.

**EDGAR**: the European Commission's global emission inventory (v8.0 GHG, v8.1 AP).

**EMG, Exponentially Modified Gaussian**: the curve for a smoothed, exponentially decaying plume, fitted to the line density.

**Emission factor**: kg of gas released per unit of activity (per litre of fuel, etc.).

**Emission rate (E)**: gas released per second (kg/s or mol/s).

**Enhancement (ratio)**: the amount above background; the ratio = cluster ÷ background (G3).

**EPSG:4326 / EPSG:32643**: codes for lat/lon and the UTM 43N (metric) coordinate systems.

**ERA5**: ECMWF's hourly global weather reanalysis, 0.25°.

**erfc / erfcx**: the complementary error function / its scaled version; used inside the EMG formula.

**F (mutation factor)**: DE's step size for mutants.

**Far-out fence**: the Tukey outlier rule with k = 3.

**Feasibility gates (G1–G4)**: our four go/no-go checks before Phase 1.

**Flux**: how much gas flows past per second per metre = column × wind.

**Flux divergence (method)**: E = divergence of the flux + sink; gives an emission map (Beirle 2019).

**Footprint**: the patch of ground one satellite measurement covers (TROPOMI 3.5 × 5.5 km).

**Forward model**: a calculation predicting what an instrument *should* see, given assumed emissions (the OCO plume).

**GEE, Google Earth Engine**: a cloud platform holding satellite/weather data and doing computations on it.

**GES DISC**: the NASA data centre serving the OCO files.

**Geofabrik**: a German company/server that republishes the OpenStreetMap database daily as regional files (.osm.pbf). Used for feature table v2 when the Overpass API was overloaded.

**GeoJSON**: a JSON format for map shapes.

**Glint mode**: OCO looking at the sun's reflection, used over water; our OCO-2 day was glint.

**Granule**: one data file/unit in a satellite archive (OCO: one global day).

**Haversine**: the formula for distance between two lat/lon points.

**HDF5 / NetCDF4**: scientific file formats for big arrays (EDGAR, OCO).

**Hotspot**: a peak in the emission map (central Pune; Pimpri–Chinchwad).

**hPa**: hectopascal, a pressure unit; ~1013 hPa at sea level.

**Inventory (bottom-up)**: emissions estimated from activity × emission factors, mapped with proxies.

**Inverse-variance weighting**: averaging with weights 1/σ².

**Inversion**: working backwards from observations (NO₂ columns) to their causes (emissions).

**IQR**: interquartile range, Q3 − Q1.

**IST / UTC**: Indian Standard Time = UTC + 5:30.

**L1 / L2 / L3**: satellite processing levels: raw → per-pixel gas amounts → gridded maps.

**Leaflet**: the JavaScript map library behind `g4_map.html`.

**Lifetime (τ)**: the time for NO₂ to fall to 37% by chemistry (1.67 h in Pune).

**Line density (L(x))**: the rotated plume summed across the wind at each downwind distance (mol/m).

**Lite file**: NASA's simplified OCO product, one file per day.

**MD5 checksum**: a short fingerprint of a file published next to a download; recomputing it (`md5sum`) proves the file arrived complete and unaltered.

**MIDC**: Maharashtra Industrial Development Corporation industrial estates (Bhosari, Chinchwad, Talegaon).

**Midday rate**: our satellite-derived rate (11:30–13:30 IST, October–May), expressed per year; not an annual total.

**Mole (mol)**: 6.022 × 10²³ molecules.

**Molar mass**: grams per mole (NO₂ 46, CO 28, CO₂ 44, C 12).

**Nadir**: looking straight down.

**NIES**: Japan's National Institute for Environmental Studies (makes ODIAC).

**Nominatim**: OSM's place-name search service.

**Non-detection**: the signal isn't distinguishable from noise (OCO for Pune).

**NOx**: NO + NO₂, reported as NO₂ mass; NOx = 1.32 × NO₂.

**NP (population size)**: the number of candidate solutions in DE (300).

**.npz**: NumPy's compressed array file.

**OCO-2 / OCO-3**: NASA's CO₂ satellites (OCO-3 on the ISS, with snapshot mode).

**ODIAC**: the fossil-CO₂ inventory spread by night-lights; units tonnes C/cell/month.

**OFFL**: TROPOMI's "offline" (best-quality) processing stream.

**OSM, OpenStreetMap**: the free crowd-sourced world map.

**OSRM**: a routing engine on OSM data (tried for the centreline, rejected).

**Outlier**: a value far from the rest; removed by IQR fences.

**Overpass**: one pass of the satellite over the area.

**Overpass API**: OSM's database-query service.

**Oversampling**: gridding coarse pixels onto a finer grid, so neighbouring cells repeat values (GEE L3).

**PBF (.osm.pbf)**: OpenStreetMap's compact binary file format; read in Python with pyosmium (`import osmium`).

**PCMC**: Pimpri-Chinchwad Municipal Corporation, the twin city northwest of Pune.

**Percentile**: the value below which that percentage of data falls.

**Plume**: the downwind trail of polluted air.

**Plume-model scaling (β)**: fit how many times the predicted plume the data contain (the OCO check).

**ppm**: parts per million (by molecule count).

**Prior**: an assumption used as a starting point (the EDGAR ratio; the emission map in the OCO check).

**Proxy**: a map used to spread emissions (night-lights, roads, population).

**qa_value**: TROPOMI's per-pixel quality score (0–1); not present in GEE L3.

**Quality flag (OCO)**: `xco2_quality_flag`, 0 = good.

**R²**: goodness of fit; 1 = perfect.

**Reanalysis**: a weather model corrected by observations into a complete record (ERA5).

**Reduced χ²**: scatter relative to the stated error bars; ≈ 1 means consistent.

**Resumable**: a download that continues where it stopped.

**Retrieval**: turning measured light into a gas amount.

**Root-sum-square (RSS)**: combining independent errors: √(Σ errors²).

**Rotation (wind rotation)**: turning each day's image so its wind points the same way.

**Sampling rectangle (`sampleRectangle`)**: the GEE function that returns pixel values in a box.

**SAM, Snapshot Area Map**: OCO-3 scanning an ~80 × 80 km area around a target (Pune is one).

**Scale height (H)**: the height over which air pressure drops by a factor of e (~8.4 km).

**Scenario test**: re-splitting sectors to see which mixes can explain the observed CO:NOx.

**Sector**: a category of emission source (industry, transport, residential, …).

**Sensitivity test**: re-running with a changed setting to see how much the answer moves.

**Sentinel-5P (S5P)**: the European satellite carrying TROPOMI.

**SHA-256**: a cryptographic fingerprint of a file; any change, even one digit, gives a different hash. Stored in `feature_table_v2.meta.json` to prove the frozen table is unchanged.

**Shares (flux-divergence shares)**: each zone's fraction of the total; robust (±2.4%).

**Sink term**: (V − V_bg)/τ, the NO₂ destroyed per second per area.

**SNR**: signal-to-noise ratio.

**Solar zenith angle**: the sun's angle from overhead; > 70° is excluded.

**Sounding**: one OCO measurement.

**Spatial variance share**: the fraction of a feature's variance that is between cells (where) rather than between months (when). 1 = purely spatial (roads), 0 = purely temporal (ERA5 weather).

**Spearman correlation**: correlation computed on ranks instead of raw values; robust to skewed data and outliers. Used in the v2 correlation QA.

**SRTM**: the Shuttle Radar Topography Mission height map.

**Steady state**: emissions in = losses out, so amounts don't change over time.

**Step (CO step)**: the downwind-minus-upwind CO line density = E(CO) × ⟨1/w⟩.

**Sun-synchronous orbit**: an orbit passing each place at the same local time every day.

**Swath**: the strip of ground a satellite sees in one pass.

**Synthetic test**: running a method on fake data with a known answer to measure its accuracy.

**Terrain normalisation**: dividing a column by the relative air mass to remove height effects.

**Titiler**: the raster API that cropped ODIAC for us.

**Tracer**: an easy-to-measure gas that travels with the one you care about.

**TROPOMI**: the instrument on Sentinel-5P measuring NO₂, CO, etc.

**Troposphere**: the lowest ~10–15 km of the atmosphere.

**Tukey fences**: Q1 − k·IQR and Q3 + k·IQR.

**u, v**: the east–west and north–south wind components.

**Uncertainty budget**: the list of all error sources and their combined total (23.6%).

**Upper limit (95%)**: the value the true emission is 95% likely to be below (OCO: 7–14 Mt/yr).

**UTM**: Universal Transverse Mercator, a flat metric map grid (zone 43N for Pune).

**Validation**: checking results against something independent.

**Vectorised**: evaluating many inputs in one array operation (the fast DE test).

**Waypoint**: one of the 10 named places along the corridor.

**Annual-mean equivalent**: the satellite midday October–May rate divided by F (D17), for comparison with annual inventories.

**Background slope (c)**: the extra EMG parameter in D19: a background that changes linearly with distance (B + c·x).

**Bilinear interpolation**: estimating a value at a point from the four surrounding grid values (used to put NO₂/CO on cell centres).

**Cell (grid cell)**: one 1 km × 1 km square of the Phase 2 grid; 268 of them.

**Converged (optimiser)**: the DE population has settled on one answer before the iteration limit.

**F (temporal factor)**: how much higher emissions are in our overpass hours and months than on average (1.20–1.23).

**Fallback (flat)**: the D19 quality rule. An unconstrained sloped fit is refitted with a flat background.

**Feature table**: the Phase 2 table, one row per cell per month, with all the input variables (v1: 10,720 rows).

**Fit window**: how far downwind the EMG is fitted (45 km after D19).

**GRIP4**: Global Roads Inventory Project, a published global road map; used for roads in feature table v1.

**HCHO**: formaldehyde, a satellite indicator of reactive VOCs; our chemistry proxy (D14).

**IPCC code**: standard emission-category codes (e.g. 1A3b = road transport), used to match EDGAR profiles.

**Lognormal**: a distribution of a quantity whose logarithm is normal; always positive, skewed. Used in the Monte Carlo.

**Model-free check**: a test that doesn't rely on fitting a model (e.g. city-minus-rural NO₂ for COVID).

**Monte Carlo**: estimating uncertainty by simulating the calculation many times with randomly drawn inputs (200,000 draws).

**NDBI**: Normalized Difference Built-up Index, (SWIR − NIR)/(SWIR + NIR), from Sentinel-2 bands B11 and B8.

**NDVI**: Normalized Difference Vegetation Index, (NIR − red)/(NIR + red), from Sentinel-2 bands B8 and B4.

**Overpass API / mirror**: OSM's query servers; mirrors are copies run by other organisations.

**Quality rule**: the D19 check that flags a sloped fit as unconstrained (τ < 0.6 h or a bootstrap range > ×2).

**SCL**: Sentinel-2's Scene Classification Layer (cloud, shadow, vegetation, water…), used to mask clouds.

**Second source**: emissions downwind of the main city (PCMC/Talegaon) that broke the single-source EMG assumption (D19).

**Temporal profile**: how emissions are spread over hours, weekdays and months (EDGAR; Crippa et al. 2020).

**Unconstrained fit**: a fit whose parameters the data can't pin down (e.g. slope vs decay trade-off).

**VIIRS DNB**: the night-time light sensor on Suomi-NPP; monthly radiance in nW/cm²/sr.

**VOC**: volatile organic compounds, reactive gases (from fuels, solvents, plants) that drive urban photochemistry.

**x₀**: see e-folding distance.

**XCO₂**: column-averaged CO₂ mole fraction (ppm), what OCO measures.

**YAML**: the human-readable config format (`study.yaml`).
