# Chapter 6 — Phase 1, Every Method Explained

> **Read this first:** §6.5–6.10 walk through each method with the numbers from the *original* configuration, which is
> still the right way to learn the arithmetic. §6.11 explains the later correction (D19), and the summary table at the
> end (§6.13) has the **current** values.

This is the heart of the project. Each section explains **the idea (in words) → the maths → what
the code does → our actual numbers**. Keep chapter 2 and the glossary nearby.

---

## 6.1 Building the data cube

**Idea:** to average many days, every day's image must sit on *exactly* the same grid.

**What the code does** (`acquire/tropomi_cube.py`):
1. For each month, ask GEE for TROPOMI images touching the corridor, apply QC, and keep only
   overpasses where ≥ 50% of corridor pixels are valid.
2. **Reproject** each image onto one fixed 0.01° grid (90 rows × 95 columns, 73.35–74.30°E,
   18.15–19.05°N), and pull the numbers out with `sampleRectangle`.
3. Save one `.npz` per month. `load_cube()` stitches them into one array, **(1004, 90, 95)**:
   day × row × column.

**Bug met:** the box edges fell exactly on pixel boundaries, so GEE returned 91 × 96. The fix
was to pull the box in by a quarter pixel on each side.

---

## 6.2 Outlier removal (IQR)

**Idea:** remove the rare garbage values (retrieval glitches) **without** removing the plume.

**The trap:** the plume makes a pixel high *only on days the wind points at it*. An outlier filter
that looks at the wrong thing deletes the very signal we're measuring.

**Three variants** (`qc.py`), tested on a fake plume with fake glitches (`tests/test_qc.py`):

| Variant | What it compares | Synthetic result | Real-data removal |
|---|---|---|---|
| domain | each pixel vs the whole image that day | **clips the plume core** (−7%) | 4.2% |
| local | each pixel vs its neighbours that day | fine on fake data | **29%** ✗ |
| **temporal, k = 3** | each pixel vs **its own history** | catches 92% of glitches, plume changes 0.9% | **0.09%** ✓ |

- Why "local" failed on real data: GEE copies each ~3.5 × 5.5 km TROPOMI pixel into several 1 km
  cells. Neighbours are identical, so the only "deviations" are the edges between footprints, and
  the filter flagged those.
- **The lesson:** test QC on real data too.

**Tukey fences** (k = 3): for each pixel's time series, compute Q1 and Q3 (the 25th and 75th
percentiles) and IQR = Q3 − Q1. Remove values < Q1 − 3·IQR or > Q3 + 3·IQR.

---

## 6.3 Matching wind to each overpass

`run_city.match_wind()` joins each cube day to the ERA5 row nearest in time (within 30 min), taking
u, v and speed at 850 hPa at the C2 point.
- **Bug met:** pandas refused to join two date columns stored with different precision
  (milliseconds vs microseconds). The fix converts both to nanoseconds.

---

## 6.4 Where is the source? The calm-wind composite

**Idea:** on calm days (wind < 2 m/s), NO₂ piles up over its source instead of blowing away. So
the peak of the calm-day average marks the main source.

**Steps:**
1. Average the 187 calm overpasses → a map.
2. Smooth it with a 3 × 3 pixel average.
3. Find the maximum within 15 km of the Pune/PCMC centre.

**Result:** **18.485°N, 73.855°E**, Swargate/Camp in central Pune, ~2 km south of the corridor tip.
PCMC shows as a secondary ridge (figure `calm_composite.png`).

---

## 6.5 How much NOx? Wind rotation + line density + EMG fit (the base paper's method)

This is the most important method. Take it slowly.

### Step 1: rotate every day
Each day the wind blows in a different direction, so averaging raw images would smear the plume
into a round blob. Instead, **rotate each day's image around the source so its wind always points
the same way (+x, "downwind")**. Then all the plumes line up and averaging makes them clearer.

Maths, for a pixel at offset (dx east, dy north) km from the source, and wind (u, v):
```
θ = atan2(v, u)                       # the direction the wind blows TO
along  =  dx·cos θ + dy·sin θ         # distance downwind (+) / upwind (−)
across = −dx·sin θ + dy·cos θ         # distance sideways
```
Every pixel of every day is dropped into a **rotated grid** of 2 km bins, from 40 km upwind to
60 km downwind (`along`) and ±20 km sideways (`across`). Summing and dividing gives the **mean
rotated field** (figure `rotated_main.png`).

We only use **windy days** (2–8 m/s): on calm days there's no plume direction, and in very strong
wind the plume is too diluted.

### Step 2: line density
Add up the rotated field *across* the wind (all 40 km of it) at each downwind distance x:

  **L(x) = Σ_across (mean NO₂) × width** → units **mol/m**

That's "how much NO₂ is in a 1 m thick slice across the plume at distance x". It rises through the
city and then decays downwind as NO₂ is destroyed (figure `line_density_main.png`).

### Step 3: the EMG model
An **Exponentially Modified Gaussian (EMG)** describes that shape. Think of it this way: NO₂ is
emitted at a point and then decays exponentially as it's carried downwind (the "exponential" part).
But the source isn't really a point, it's a whole city, so the curve gets smoothed (the
"Gaussian" part). Plus a flat background.

  **L(x) = a · f(x; x₀, μ, σ) + B**

| Parameter | Meaning | Our fit |
|---|---|---|
| **a** | total NO₂ in the plume attributable to the city (the **burden**), in mol | 51,748 mol |
| **x₀** | e-folding distance: how far NO₂ travels before dropping to 37% | 24.95 km |
| **μ** | where the source sits along x | −3.3 km |
| **σ** | how spread-out the source is (city size) | 9.3 km |
| **B** | background line density | 1.27 mol/m |

f is a unit-area EMG (it integrates to 1). The code uses `erfc`/`erfcx` (the complementary
error function), with a numerically safe form to avoid overflow.

### Step 4: fit it with Differential Evolution (DE)
"Fitting" means finding the 5 parameters that make the model curve match the data points best,
i.e. that minimise the sum of squared differences.

**Differential Evolution** (Storn & Price, 1997) is an optimiser inspired by evolution. It is good
at finding the *global* best, rather than getting stuck in a nearby dip:
1. Create a **population** of NP random guesses (**NP = 300** = popsize 60 × 5 parameters).
2. For each guess, build a "mutant": take one guess and add F × (the difference between two
   others). **F (mutation) ∈ [0.5, 1.0]**, re-drawn each generation ("dithering").
3. Mix the mutant with the original, parameter by parameter, with probability **CR (crossover) = 0.7**.
4. If the new guess fits better, it replaces the old one ("survival of the fittest").
5. Repeat for up to 2,000 generations until the population converges; then polish with a local method.

**Sensitivity test (proposal step 4):** we re-ran the fit with 36 combinations (NP 150/300 ×
F dithered/0.5/0.9 × CR 0.3/0.7/0.9 × 2 random seeds). **All gave the same answer to 6 digits.**
The result doesn't depend on the optimiser's settings.

### Step 5: from the fit to the emission (worked example; original configuration)

> These worked numbers use the *original* fit (flat background, fit to 60 km). That's still the right way to learn
> the arithmetic. The corrected main fit (D19, §6.11) gives E = 0.663 kg/s and τ = 1.09 h by exactly the same formulas.
```
w (mean wind of the 781 windy days)      = 4.1446 m/s
lifetime τ = x₀ / w = 24,951 m / 4.1446 m/s = 6,020 s = 1.672 h
E(NO₂) = a / τ     = 51,748 mol / 6,020 s  = 8.596 mol/s
E(NOx) = 1.32 × E(NO₂)                     = 11.347 mol/s
in kg:  11.347 mol/s × 0.0460 kg/mol       = 0.522 kg/s
per year (midday rate): 0.522 × 31,557,600 = 16.5 kt NOx/yr
```
The logic of E = a/τ: in steady state, what goes in (emission) equals what's destroyed. What's
destroyed per second is the amount present (a) divided by how long each molecule survives (τ).

### Step 6: uncertainty by bootstrap
Resample the 781 days *with replacement* 200 times, refit each time (a fast local fit starting from
the best answer), and take the 2.5th and 97.5th percentiles:
**E(NOx) = 0.522 [0.486–0.555] kg/s; τ = 1.67 [1.55–1.81] h.**

### Step 7: sensitivity runs

| Change | E(NOx) kg/s |
|---|---|
| Only east-southeast winds / only west-northwest | 0.561 / 0.442 |
| Only 2–4 m/s / only 4–8 m/s | 0.478 / 0.506 |
| Wind at 100 m / 10 m instead of 850 hPa | 0.456 / 0.347 |

**The wind level matters most.** Surface wind is too slow for a plume ~1 km deep. With a smaller w,
you get a longer τ and a smaller E. That's why 850 hPa is the physically justified choice.

---

## 6.6 Does the method work? Synthetic tests (`tests/test_emg.py`)

**Idea:** build a *fake* city on the real grid, with a **known** emission (0.5 mol/s) and lifetime
(3 h). Simulate 200 days with random winds and noise, run the exact same pipeline, and see if you
get the known answer back.

**Result:** emission **+11–12%**, lifetime **−16–17%**, the same in both random seeds, so it's a
**systematic bias**, not noise. We found where it comes from by switching each factor off:
- ~2%: the ±20 km window cuts off the plume's edges far downwind;
- ~6%: averaging days with different wind speeds (the plume length changes with wind);
- ~4%: 2 km bins near the source.

We **keep** this bias in the uncertainty budget (12%) rather than silently correcting it. This is
a strong point for examiners: most studies *assume* their method error; we *measured* it.

---

## 6.7 Where exactly? The flux-divergence map (Beirle et al., 2019)

**Why:** the EMG treats the city as one source. But the line density rose again 50–60 km
downwind: in east-southeast winds that's PCMC and Talegaon up the corridor. We needed a map.

**Idea:** think of a pixel as a room. Air carries NO₂ in through one door and out through another.
- If more NO₂ leaves than enters, something inside is **emitting** it.
- NO₂ is also destroyed inside the room (the **sink**).

  **E = L_NOx × [ ∇·(V·w) + (V − V_bg)/τ ]**

| Symbol | Meaning |
|---|---|
| V | mean NO₂ column in the pixel |
| V·w | the **flux**: how much NO₂ flows past per second per metre (column × wind) |
| ∇·(V·w) | the **divergence**: outflow minus inflow per area. Computed with `np.gradient` on the mean flux maps |
| (V − V_bg)/τ | the **sink**: NO₂ destroyed per second (only the excess above background, V_bg = 2.96 × 10⁻⁵ mol/m²) |
| τ | 1.67 h from the EMG fit |
| L_NOx | 1.32 |

Summing E over an area gives that area's emission.

**Synthetic test** (`tests/test_divergence.py`): recovers a known source at **−4%**, stable at any
radius, with no fake sources away from the plume.

**Results:**
- **Two hotspots, 16.7 km apart:** central Pune (18.485, 73.855), the same pixel the EMG found,
  and **Pimpri–Chinchwad (18.625, 73.795)**, inside the corridor, at ~75% of Pune's strength.
- **Agreement:** summed within 25 km, **0.570 kg/s**, versus EMG's 0.522: within 9%.
- **The catch:** on real data the total keeps rising with radius (0.47 at 20 km → 0.70 at 35 km). We
  split it into its two terms: the flux term levels off (~0.16 kg/s), but the **sink term** keeps
  growing (~70% of the total). Even 30 km out, NO₂ is ~24% above our chosen background, and the
  method counts all of that as local emission.
  - So **absolute totals depend on τ and the background choice** (−16% to +30%),
  - but **shares barely move** (the corridor is 20.8–21.8% in every test).
- **Decision D10:** the city total comes from EMG; *where* it comes from comes from the
  flux-divergence **shares**.

| Zone | Share | NOx kg/s |
|---|---|---|
| Pune core (outside the corridor) | 29.5% | 0.168 |
| C1 Shivajinagar–Kasarwadi | 10.1% | 0.058 |
| C2 PCMC | 6.5% | 0.037 |
| C3 Dehu–Talegaon | 4.5% | 0.025 |
| **Corridor** | **21.1%** | **0.120** |

---

## 6.8 From NOx to CO₂, and the inventories (`run_co2.py`)

1. **Comparison area:** within 25 km of the source, where the two methods agree.
2. **EDGAR ratio:** EDGAR's fossil CO₂ ÷ EDGAR's NOx over the same area. Grid cells partly inside
   the circle count partly: each 0.1° cell is split into 10 × 10 sub-points to find its fraction
   inside.
   - Ratio **172** (2019 176, 2020 166, 2021 171, 2022 176).
3. **CO₂** = 16.5 kt NOx/yr × 172 = **2.83 Mt CO₂/yr**.
4. **Compare:** EDGAR 3.63 Mt; ODIAC 11.8 Mt (converted from carbon ×44/12).
5. **Findings:** the satellite NOx is **22% below EDGAR's** (16.5 vs 21.1 kt; unresolved). The
   inventories differ **3.2×**. By sector, the ratio spans 115 (industry) to 393 (homes).

**The first uncertainty budget** (each term is a relative 1σ; they combine by root-sum-square):
- ratio representativeness 25% (the base paper's value);
- EMG bias 12%;
- wind regime 11.4% (half the difference between the two regimes);
- NOx/NO₂ 7.6% (0.1/1.32);
- wind level 6.4%;
- bootstrap 3.3%;
- EDGAR year-to-year 3.1%;
- **→ total 31.9%.**

---

## 6.9 Can CO₂ satellites confirm it? The OCO check (`run_oco_check.py`)

**Idea: plume-model scaling.** Predict what Pune's CO₂ plume *should* look like on each OCO day,
then ask the data "how many times this plume do you see?" (β).

1. **Emission map** = the flux-divergence map (positive part, within 25 km, or 10 km as an
   alternative), scaled so it sums to 2.83 Mt CO₂/yr = 90 kg CO₂/s.
2. **Gaussian plume:** each 1 km cell's CO₂ spreads downwind in a widening Gaussian (width
   σ = √(2² + (0.15·d)²) km at distance d), carried by that day's ERA5 wind at the OCO overpass hour.
   CO₂ doesn't decay.
3. **Convert to ppm:** a column mass ÷ 0.044 kg/mol ÷ (air in the column = surface pressure ÷
   (g × 0.029)). At Pune, that's ~3.3 × 10⁵ mol of air per m².
   - Worked example: 90 kg/s spread by 4 m/s wind across ~50 km → 90/(4 × 50,000) = 4.5 × 10⁻⁴ kg/m²
     → 0.0102 mol/m² → 0.0102 / 331,000 = 3.1 × 10⁻⁸ = **0.03 ppm**. Tiny.
4. **Regression** per day: XCO₂ = b₀ + bₓ·x + b_y·y + **β**·predicted (weights 1/uncertainty²).
   The x and y terms absorb a regional slope.
5. **Combine the 8 days** by inverse-variance weighting, inflating the error by √χ² because the
   days disagree more than their error bars.

**Result:**
- Predicted plume **0.02–0.15 ppm**.
- Sounding noise 0.5–1.1 ppm, plus **stripes** between scan swaths (retrieval artefacts, 0.5–1 ppm).
- **β = 1.02 ± 0.94** (10 km prior) or 2.00 ± 1.81 (25 km). That's consistent with 1, but also with 0:
  **not a detection.**
- Upper limit: **< 7–14 Mt/yr** (95%). Detection threshold: **~8–15 Mt/yr**.
- **Conclusion (D11):** OCO gives a bound, not a measurement, for a city of Pune's size.

---

## 6.10 The breakthrough: TROPOMI CO pins down the ratio (`run_co_ratio.py`)

**Idea:** different sources emit different amounts of CO per NOx (homes: 78; industry: 10;
traffic: 2 mol/mol). If we measure Pune's CO:NOx, we learn its **sector mix**, and so the right
CO₂:NOx.

**Why CO behaves differently:** CO lives for weeks, so it doesn't decay in the plume. Downwind of
the city its line density **steps up and stays up**. The height of the step = E(CO) × ⟨1/w⟩.

**The terrain problem** (§2.2): the Western Ghats imprint a ~6% pattern on the CO column, more than
Pune's ~2% signal. **The four-step fix:**
1. Divide each column by exp(−z/8.4 km), using SRTM height smoothed to the ~5 km CO pixel. That
   turns it into an air-mass-normalised amount.
2. Subtract each day's median over the box (the whole region's CO goes up and down day to day).
3. **Subtract each pixel's long-term average.** Anything that stays in the same place (terrain
   leftovers, instrument patterns, even the city's average CO dome) disappears. Only what moves
   with the wind survives.
4. Rotate by the wind (as in 6.5) and take **line density at 20–40 km downwind minus at 20–40 km
   upwind** = the full step. (The removed dome was symmetric, so the difference recovers the
   whole step.)

**Synthetic test** (`tests/test_co_step.py`): a known 100 mol/s source **plus fake terrain bigger than
the plume** → recovered **98.6** (−1.4%). Terrain alone → **−0.8** (≈ 0). The method works.

**Worked example (real data):**
```
step = 64.98 mol/m ;  ⟨1/w⟩ over 608 windy days = 64.98 / 240.3 = 0.270 s/m
E(CO) = step / ⟨1/w⟩ = 240.3 mol/s = 6.73 kg/s
CO:NOx = 240.3 / 11.35 = 21.2 mol/mol   [95% CI 18.7–23.8]
EDGAR, same area: 16.0 → observed is 33% higher
```
It's robust: 19.5–22.0 across terrain choices and seasons.

**What does "33% more CO" mean?** Try re-splitting pairs of sectors (all others kept at EDGAR's shares):
- *Industry vs transport:* even 100% industry can't reach 21.2 → **impossible**.
- *Residential vs industry:* works if homes are 24% of the pair (EDGAR: 13%) → CO₂:NOx **181**.
- *Residential vs transport:* 57% (EDGAR 33%) → **174**.
- *High-CO group vs the rest:* 18.5% (EDGAR 11%) → **188**.
- **So Pune has more household/biomass-type burning than EDGAR assumes.**
- CO-constrained CO₂:NOx = **181 (95% range 167–197)**, instead of "anywhere from 115 to 393".

**New headline:** 16.5 kt NOx/yr × 181 = **2.98 Mt CO₂/yr**.
**New uncertainty:** the 25% ratio term becomes 8.1% (scenario spread) + 10% (assumed, for EDGAR's
per-sector ratios). The total goes from 31.9% to **23.6%**:
```
√(3.3² + 6.4² + 11.4² + 12.0² + 7.6² + 3.1² + 8.1² + 10.0²) = √558.8 = 23.6 %
```
**This is the project's main answer so far: adding a second satellite tracer (CO) measurably
improves the estimate.**

---

## 6.10b Monte Carlo uncertainty (added later; D18)

Instead of adding percentages by root-sum-square, a **Monte Carlo** simulates the whole calculation 200,000
times. Each time it draws a random value for every uncertain input (emission from the bootstrap, wind
level, NOx/NO₂ ratio, CO₂:NOx ratio, and so on) and multiplies them through. The spread of the 200,000
answers *is* the uncertainty. Lognormal draws keep everything positive, so the ranges come out lopsided
(−19% / +24%). Result: annual **2.45 Mt/yr [95%: 1.54–3.90]**, which rules out ODIAC's 11.8.

## 6.11 The D19 correction: when the fit window is too long

Testing a **sloped background** (B + c·x instead of a flat B) changed the answer by 42%. Chasing why exposed a
real flaw. In east-southeast winds, **PCMC and Talegaon sit 30–60 km downwind of central Pune**. Fitting
the line density all the way to 60 km means the "plume" includes a *second* city. A single-source curve can only
explain that raised tail as slow decay, so the lifetime came out too long (1.67 h) and the emission too low.

| Fit window | flat background | sloped background |
|---|---|---|
| 60 km | 0.522 | 0.740 |
| **45 km** | 0.591 | **0.663** |
| 30 km | 0.609 | 0.651 |

Inside 30–45 km the two background models agree, and on synthetic data the sloped model is as accurate as the
flat one. So the corrected method fits to **45 km with a sloped background → E = 0.663 kg/s, τ = 1.09 h**.
The ripple effects: CO:NOx = 240.3 / (0.663/0.046) = **16.7** (close to EDGAR's 16.0), so the CO₂:NOx ratio
becomes **163**, and annual fossil CO₂ is **2.79 Mt/yr [1.79–4.36]**. The earlier "more household burning"
conclusion turned out to be an artefact of the low NOx, and was withdrawn.

**Lesson:** a model's assumptions (here, "one source") must hold *across the whole window you fit*.

## 6.12 Midday rate vs annual mean (added later; D17)

The satellite sees Pune at ~12:30 IST in October–May only. That's a *busy* window: road traffic at midday
is ~1.6× its daily average. To compare with inventories (which are annual), divide by a factor **F**:
```
F = Σ over sectors of (NOx share) × (overpass-hour factor) × (weekday factor) × (Oct–May month factor)
  ≈ 0.643×1.08 (industry) + 0.198×1.60 (transport) + 0.099×1.39 (residential) + … = 1.23
annual NOx = 16.5 / 1.23 = 13.4 kt/yr ;  annual CO₂ = 13.4 × 181 / 1000 ≈ 2.42 Mt/yr
```
The factors come from EDGAR's published temporal profiles (Crippa et al., 2020). Caveat: EDGAR's India
residential month profile assumes winter heating, which Pune hardly does. A flat profile gives F = 1.20.

## 6.14 Seasons and the COVID-19 check (added later)

**Seasonal fits** (`run_seasonal.py`): the same EMG fit, done separately for each October–May season. Current
values (after D19): 0.434 / 0.602 / 0.733 / 0.666 / 0.663 kg/s for 2019–20 … 2023–24. The spread *between*
seasons is 2.8× the uncertainty *within* a season, so seasons are genuinely different: the time variation is real,
not noise. That's why Phase 3 can use **seasonal** labels.

**COVID check, deliberately model-free:** the mean NO₂ within 10 km of the source minus the mean in a rural ring
35–45 km away, for 25 March – 31 May of each year:
```
2020 (lockdown) 7.8 · 2021 (restrictions) 21.5 · 2022 27.3 · 2023 29.3 · 2024 34.3   µmol/m²
→ 2020 is −74% and 2021 −29% vs the 2022–24 mean
```
The satellite sees both lockdown periods in the right order of severity. (We first tried the EMG on the 2020 window
alone: it gave −84% but with R² 0.62 and a 8.8 h lifetime. A degenerate fit, because the plume was too weak, so it
wasn't used. The model-free check is the trustworthy one.)

## 6.15 A CO-based emission map (added later; D16 feasibility)

The flux-divergence idea of §6.7, applied to **CO** instead of NO₂ (`run_co_divergence.py`). CO doesn't decay, so there's
no sink term: E = divergence of the flux only. **The trap:** Pune's winds blow mostly from one direction, and the
fixed terrain pattern × that mean wind fakes a divergence. On synthetic data with *Pune's real winds*, the raw version
gave a −70 mol/s fake source from terrain alone. Removing each pixel's long-term mean (as in §6.10) fixes it (≈ 0),
with a −12% bias.

Real result: 248 mol/s within 25 km vs 240 from the CO step (agreement within 3%); pattern correlation with the NO₂
map r = 0.75; **the corridor holds 14.5% of the city's CO but 21.0% of its NOx**. That's an exploratory sign of an
industrial corridor (low CO per NOx) next to a residential core (high CO per NOx).

## 6.13 Summary of every number, in one place (current, after D19)

| Quantity | Value |
|---|---|
| Usable NO₂ / CO overpasses | 1,004 / 907 |
| Source location | 18.485°N, 73.855°E |
| E(NOx), city | **0.663 kg/s [0.620–0.715]** = 20.9 kt/yr midday (pre-D19: 0.522) |
| NO₂ lifetime | **1.09 h [0.96–1.23]** (pre-D19: 1.67) |
| Flux divergence, 25 km | 0.787 kg/s (+19% vs EMG; τ 1.09 h) |
| Corridor share / NOx | 21.0% / 0.165 kg/s (FD) |
| EDGAR NOx / CO₂ (25 km) | 21.1 kt / 3.63 Mt |
| ODIAC CO₂ (25 km) | 11.8 Mt |
| CO:NOx observed / EDGAR | **16.7** / 16.0 mol/mol (pre-D19: 21.2) |
| CO₂:NOx EDGAR / CO-constrained | 172 / **163 (148–180)** |
| **City fossil CO₂** | **2.79 Mt/yr annual mean [95%: 1.79–4.36]**; midday rate 3.39 [2.26–5.08] (Monte Carlo, after D19) |
| Corridor fossil CO₂ | ~0.63 Mt/yr |
| OCO β / upper limit | 0.81 ± 0.74 (10 km) · 1.57 ± 1.44 (25 km) / < 7–14 Mt/yr |
