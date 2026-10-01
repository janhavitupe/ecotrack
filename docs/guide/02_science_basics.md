# Chapter 2 — The Science You Need

Read this slowly. Every later chapter builds on these ideas.

---

## 2.1 The gases in this project

| Gas | Formula | Where it comes from | How long it lives in air | Why we care |
|---|---|---|---|---|
| Carbon dioxide | CO₂ | Burning anything with carbon: fuel, coal, gas, wood | **Centuries** | The thing we want to measure; the main greenhouse gas |
| Nitrogen oxides | **NOx** = NO + NO₂ | High-temperature burning (engines, boilers, stoves). Air's own N₂ and O₂ react in the flame | **Hours** (≈ 1.7 h in Pune at midday) | Emitted *together with* CO₂, easy to see from space → a **tracer** |
| Nitrogen dioxide | NO₂ | Part of NOx | Hours | What TROPOMI actually measures |
| Carbon monoxide | CO | *Incomplete* burning: poor combustion, stoves, old engines, biomass | **Weeks to months** | Tells us *what kind* of burning (a "fingerprint") |

### Why NOx and not just NO₂?
A flame mainly makes **NO**, which turns into **NO₂** within minutes in sunlight. The two keep
swapping back and forth. The satellite sees only NO₂, so we scale up to total NOx with a ratio:
**NOx = 1.32 × NO₂**. That's a typical midday urban value from the literature (Beirle et al., 2011),
and it is an *assumption*, which is why it has its own line (±7.6%) in the uncertainty budget.

### What is a "tracer"?
A gas that travels with the thing you care about and is easier to measure. Think of dye added to
water to show where the water flows. NO₂ is our dye for CO₂: they leave the same chimneys and
exhaust pipes at the same time.

---

## 2.2 Measuring gas from space: "columns"

A satellite looking down can't tell *how high* the gas is. It measures **all the gas in the
column of air** below it, from the ground to space, per square metre of ground.

- **Column density**: the amount of gas above 1 m² of ground, in **mol/m²** (moles per square metre).
  - A **mole** is a counting unit: 6.022 × 10²³ molecules (like "a dozen" = 12, but huge).
  - Pune's NO₂: about **3 × 10⁻⁵ mol/m²** in clean-ish air, up to ~9 × 10⁻⁵ over the city.
  - Scientists often use "molecules/cm²": 1 mol/m² = 6.022 × 10¹⁹ molecules/cm².
- **Tropospheric column**: only the lowest ~10–15 km of the atmosphere (the **troposphere**, where
  weather and pollution live), excluding the stratosphere above. TROPOMI gives this separately.
- **XCO₂** (column-averaged CO₂): CO₂ satellites report CO₂ as a **mole fraction**, the average
  "parts per million" over the whole column. It's about 406–421 ppm in our data (rising yearly).
  - **ppm** = parts per million. 420 ppm = 420 CO₂ molecules per million air molecules.

### Why the ground height matters (the terrain problem)
A column counts *all* the air above you. Stand on a mountain and there is less air above you, so
less of every gas. Pune sits at ~560 m, the Konkan coast at ~0 m. So the Konkan column holds ~6%
more air, and ~6% more CO, **even with no pollution at all**. We had to remove this for CO
(chapter 6, §6.9).
- Air pressure falls with height roughly as **exp(−z/H)**, where z = height and **H ≈ 8.4 km** is
  the **scale height** (how far up pressure drops by a factor of e ≈ 2.72).

---

## 2.3 Wind, plumes and the boundary layer

- **Plume**: the trail of polluted air blown downwind from a source, like smoke from a chimney
  stretched out by the wind.
- **Wind components u and v**: weather data gives wind as two numbers. **u** is the east–west speed
  (positive = blowing *toward* the east) and **v** is the north–south speed (positive = toward the north).
  - Wind speed = √(u² + v²).
  - Wind direction is by convention **where the wind comes FROM**, in degrees clockwise from north.
    "Wind from 90°" means an easterly wind, blowing toward the west.
- **Boundary layer (BLH, boundary-layer height)**: the lowest layer of air, which the sun-heated
  ground stirs up during the day. Pollution from the ground mixes within it. In Pune at midday
  it is ~1.1–2.9 km deep (median 1.66 km).
- **Pressure levels (hPa)**: weather models give wind at fixed pressures instead of fixed heights.
  - **1000 hPa** ≈ sea level; **850 hPa** ≈ 1.5 km above sea level. Pune is at ~560 m, so
    850 hPa is ~1 km above the ground, **inside** the midday boundary layer. That's why we use it
    to push the plume: it represents the wind the pollution actually travels in.
  - **10 m and 100 m wind**: wind at 10 m and 100 m above the ground. It's slower, because the
    ground slows it (friction). Using it would make the plume seem to move too slowly (chapter 6).

---

## 2.4 Lifetime and e-folding: why NO₂ fades

NO₂ is destroyed by chemistry (mainly reacting with OH radicals made by sunlight). If none were
added, the amount would shrink **exponentially**:

  amount(t) = amount(0) × exp(−t/τ)

- **τ (tau), the lifetime**: the time for the amount to drop to 1/e ≈ 37%. In Pune, τ ≈ **1.7 hours**.
- **x₀, the e-folding distance**: how far the wind carries it in one lifetime: **x₀ = w × τ**.
  With wind w = 4.14 m/s and τ = 1.67 h = 6,020 s, x₀ = 4.14 × 6,020 ≈ 24,950 m ≈ **25 km**.
  That's exactly the value our fit found.

CO₂ and CO are effectively **inert** (they don't decay) over hours, so downwind of a city their
amount **stays up** rather than fading. We use that difference in chapter 6.

---

## 2.5 Emissions and their units

- **Emission rate (E)**: how much gas a source releases per second, in **kg/s** or **mol/s**.
- **Converting to per year**: 1 year = 31,557,600 s.
  - 0.522 kg/s × 31,557,600 s ≈ 16,470,000 kg ≈ **16.5 kt/yr** (kt = kilotonne = 1,000 tonnes).
  - CO₂ is usually in **Mt/yr** (megatonnes = million tonnes per year).
- **"Midday rate"**: our satellite sees Pune only at ~11:30–13:30 IST, and only October–May. We
  multiply that rate by a year's worth of seconds to get "kt/yr", but **it isn't an annual total**:
  nights emit less, and the monsoon months are missing. We always label it "midday rate".
- **Molar mass** (needed to convert mol ↔ kg):

  | Gas | g/mol |
  |---|---|
  | NO₂ (and NOx, which is conventionally reported "as NO₂") | 46.0 |
  | CO | 28.0 |
  | CO₂ | 44.0 |
  | C (carbon) | 12.0 |

  **ODIAC reports carbon, not CO₂.** To convert: × 44/12 ≈ × 3.67.

---

## 2.6 Inventories: the "bottom-up" way

An **emission inventory** estimates emissions by multiplying activity (litres of fuel sold,
factories, population) by **emission factors** (kg of gas per litre, per factory...), then spreading
the totals onto a map using **proxies** (road maps, night-time lights, population maps).
- **Bottom-up** = inventories, built from activity data.
- **Top-down** = inferred from atmospheric measurements, which is what we do.

Inventories split emissions into **sectors**: industry, road transport, residential (homes),
power plants, and so on. We use two of them:
- **EDGAR** (European Commission JRC): a full inventory by sector and gas.
- **ODIAC** (Japan's NIES): fossil CO₂ only, spread on a map using satellite night-lights.

Different sectors emit different **ratios** of gases. That fact is the key to chapter 6, §6.9:

| Sector | CO₂ per NOx (t/t) | CO per NOx (mol/mol) |
|---|---|---|
| Industry | 115 | 9.9 |
| Road transport | 174 | 1.95 |
| Residential (homes) | 393 | 77.9 |
| Power plants | 284 | 0.38 |

(EDGAR values around Pune, 2021.)

---

## 2.7 Statistics words you'll meet

- **Mean / median**: the average / the middle value.
- **Percentile**: the value below which a given percentage of the data falls. The 10th percentile
  of NO₂ means 10% of pixels are lower. We use it as the "clean background".
- **IQR (interquartile range)**: the 75th percentile minus the 25th percentile, a robust "spread".
- **Tukey fences**: a standard outlier rule. Anything below Q1 − k·IQR or above Q3 + k·IQR is an
  outlier. k = 1.5 is "outlier"; k = 3 is "far out" (the one we use).
- **R² (coefficient of determination)**: how well a fitted curve matches data. 1 = perfect.
  Our plume fits give 0.98–0.99.
- **Standard deviation (σ, sigma), and "1σ"**: typical spread. "± 24% (1σ)" means the true value
  lies within ±24% about 68% of the time.
- **95% confidence interval (CI)**: a range that contains the true value 95% of the time
  (roughly ± 2σ).
- **Bootstrap**: estimate uncertainty by re-running the analysis many times on random
  *resamples* of your data (drawn with replacement), then looking at how much the answer
  varies. We do 200 resamples of the overpass days.
- **Root-sum-square (RSS)**: how independent errors combine: total = √(a² + b² + c² + …). Two errors
  of 3% and 4% combine to 5%, not 7%.
- **Bias vs noise**: *noise* is random scatter that averages away; *bias* is a consistent offset
  in one direction that does not.
- **Signal-to-noise ratio (SNR)**: signal ÷ noise. Below ~3 means "not reliably detected".
- **Inverse-variance weighting**: when averaging estimates, give each a weight of 1/σ², so precise
  ones count more.
- **χ² (chi-square), reduced**: measures whether scatter is bigger than the stated error bars.
  ≈ 1 means consistent; 11–14 (as in our OCO check) means the scatter is far bigger than the
  error bars claim.

---

## 2.8 Coordinates and maps

- **Latitude / longitude**: position in degrees. Pune ≈ 18.5°N, 73.85°E.
- At Pune, **1° of latitude ≈ 110.6 km** and **1° of longitude ≈ 105.6 km** (111.3 km × cos(latitude)).
  - So 0.01° ≈ 1.1 km, our grid spacing.
- **EPSG codes**: ID numbers for coordinate systems. **EPSG:4326** = ordinary lat/lon.
  **EPSG:32643** = **UTM zone 43N**, a flat metric grid covering Pune. We use it when we need real
  kilometres, for example to buffer the highway by 3.5 km.
- **Buffer**: the area within a given distance of a line or point. Our corridor is the highway
  line buffered by ±3.5 km.
- **Bounding box (bbox)**: the simplest rectangle around an area, given as min/max lat and lon.
