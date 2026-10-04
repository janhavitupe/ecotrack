# Chapter 10 — Viva Questions (with model answers)

Cover the answer, say yours out loud, then compare. If you can answer all of these in your own
words, you're ready.

---

### The big picture

**Q1. What problem does your project address?**
Cities emit most fossil CO₂, but inventories are slow, coarse and disagree (for Pune, by 3.2×). We
estimate a city's CO₂ from satellites, and test whether combining satellites beats relying on NO₂ alone.

**Q2. Why not measure CO₂ directly from space?**
Pune adds only ~0.03–0.15 ppm to a ~420 ppm background, while CO₂ satellites have ~0.5–1 ppm noise
per sounding and only occasionally overpass. We tested it: OCO-3/OCO-2 can't detect Pune's plume.

**Q3. Why NO₂?**
It's co-emitted with CO₂ by combustion, has a low background (so city signals stand out), a
lifetime of only hours (so it's local and fresh), and TROPOMI measures it daily at ~3.5 × 5.5 km.

**Q4. What's the weakness of the NO₂ approach?**
Converting NOx to CO₂ needs a ratio that depends on the sector mix (115–393 across sectors). The
base paper calls it its largest error term.

**Q5. What's your headline result?**
Pune + PCMC emit ~0.66 kg/s NOx (midday) and **~2.8 Mt fossil CO₂/yr as an annual mean (95%: 1.8–4.4)**.
The corridor contributes ~21%. ODIAC's 11.8 Mt/yr is outside our range; EDGAR's 3.6 is inside it.

### Data

**Q6. Why did your study start in October 2019?**
TROPOMI's pixel size shrank to 3.5 × 5.5 km in August 2019, so starting after that keeps the data
consistent. October–May avoids the monsoon clouds.

**Q7. What QC did you apply to TROPOMI?**
Cloud fraction ≤ 0.3, solar zenith ≤ 70°, GEE's built-in quality pre-filter (the GEE product has no
qa_value band), an overpass counts only if ≥ 50% of corridor pixels are valid, and IQR outlier
removal (per-pixel time series, Tukey k = 3, removing 0.09%).

**Q8. Why that particular IQR filter?**
We tested three on synthetic data and checked their removal rates on real data. A whole-scene filter
clips the plume core. A local filter removed 29% of real pixels, because GEE's 1 km grid copies each
TROPOMI footprint into several cells. The temporal filter caught 92% of injected spikes and changed
the plume by 0.9%.

**Q9. What is ERA5 and why 850 hPa?**
ECMWF's hourly weather reanalysis. 850 hPa is ~1 km above Pune, inside the midday boundary layer
(median 1.66 km), so it represents the wind the pollution travels in. Surface wind is slowed by
friction, and gave a 33% lower emission.

**Q10. What are EDGAR and ODIAC, and how did you use them?**
Bottom-up inventories. EDGAR (EU JRC) is by sector and gas: we used it for the CO₂:NOx ratio and as
a comparison. ODIAC (NIES) is fossil CO₂ spread by night-lights: a comparison only. Neither is
treated as ground truth, since that would be circular.

**Q11. What's special about OCO-3?**
It's on the ISS, so it passes at varying times, and it can do Snapshot Area Maps (~80 × 80 km).
Pune is a SAM target. We found 7 usable OCO-3 dates, plus 1 OCO-2 date.

### Methods

**Q12. Explain the wind-rotation method.**
Rotate each day's NO₂ image around the source so its wind points the same way, average the days to
get a clean plume, sum across the wind to get the line density, then fit an EMG curve. That gives
the burden (a) and e-folding distance (x₀). Then τ = x₀/w and E = 1.32·a/τ.

**Q13. What is an EMG and why that shape?**
An Exponentially Modified Gaussian: exponential decay downwind of the source (NO₂ is destroyed with
lifetime τ), smoothed by a Gaussian because a city is spread out, not a point. Plus a background.

**Q14. Why Differential Evolution?**
It's a global optimiser: a population of guesses evolving by mutation and crossover, less likely to
get stuck in local minima. Our proposal specified NP 300, F 0.5–1.0, CR 0.7. We tested 36
combinations, and all gave the identical result.

**Q15. How do you know the method works?**
Synthetic tests: a fake city with a known emission, simulated on the real grid with random winds
and noise. EMG recovers +12% (a systematic bias we traced to three causes and kept in the budget);
flux divergence −4%; the CO step −1.4%.

**Q16. Why did you need a second method (flux divergence)?**
EMG assumes one source. The data showed a second source downwind (PCMC). Flux divergence
(E = ∇·flux + sink) maps emissions pixel by pixel. It found two hotspots 16.7 km apart, and agreed
with EMG within 9% at 25 km.

**Q17. Why don't you use flux-divergence totals directly?**
They depend on the lifetime and background choice (−16% to +30%), because the sink term keeps
growing with area. But zone *shares* vary by only ±2.4%, so the city total comes from EMG and the
split comes from flux-divergence shares (D10).

**Q18. How did you convert NOx to CO₂?**
Initially with EDGAR's ratio over the same 25 km area (172) → 2.83 Mt/yr ± 32%. Then with a ratio
constrained by TROPOMI CO (163, range 148–180) → 2.79 Mt/yr annual mean [1.79–4.36] (Monte Carlo, after D19).

**Q19. Explain the CO method.**
CO is inert over hours, so downwind of the city its line density steps up by E(CO)/w. We normalised
for terrain (air mass), removed daily and static patterns, rotated by the wind, and took downwind
minus upwind. E(CO) = 6.73 kg/s → CO:NOx = 16.7, within 4% of EDGAR's 16.0.

**Q20. How does CO:NOx tell you the CO₂:NOx?**
Each sector has characteristic CO:NOx and CO₂:NOx ratios. Re-splitting sectors to match 16.7 gives a
CO₂:NOx of 154–173 across the four feasible scenarios (95% range 148–180), close to EDGAR's 172. (Before the D19 fix,
NOx was underestimated, CO:NOx came out at 21.2, and it *looked* like more household burning. Be ready to explain
why that was withdrawn.)

**Q21. What did the OCO check show?**
A non-detection. The predicted plume (0.02–0.15 ppm) is well below the noise and swath artefacts.
β = 1.02 ± 0.94: consistent with our estimate but also with zero. Upper limit 7–14 Mt/yr; detection
threshold ~8–15 Mt/yr.

**Q22. What's in your uncertainty budget?**
Bootstrap 3.3%, wind level 6.4%, wind regime 11.4%, EMG bias 12%, NOx/NO₂ ratio 7.6%, EDGAR
year-to-year 3.1%, CO-scenario ratio spread 8.1%, EDGAR per-sector ratios 10% (assumed). Combined by
root-sum-square: 23.6%.

### Critical thinking

**Q23. What are your main limitations?**
- Midday October–May rates, not annual totals.
- The EMG +12% bias is kept uncorrected.
- The ratio constraint trusts EDGAR's per-sector ratios.
- One uniform wind per overpass.
- The corridor zones are 1–2 TROPOMI pixels wide.
- Central Pune (the biggest source) is outside the corridor.
- Satellite NOx is 22% below EDGAR, unexplained.
- OCO rests on 8 dates.

**Q24. Your NOx is 22% below EDGAR. Who's right?**
Unresolved. A midday rate should be *above* the daily mean, which points to EDGAR being high. But
the EMG's fitted background may also absorb diffuse emissions. We report it as an open question.

**Q25. EDGAR and ODIAC differ 3.2×. Why?**
Likely allocation. ODIAC spreads national totals by night-light brightness, concentrating emissions
in bright cities. We note this as a plausible, unverified explanation. The tentative OCO hint also
disfavours ODIAC's value, but isn't robust.

**Q26. What went wrong during the project?**
Several things; chapter 7 lists 25. For example: the waypoints were off by up to 4.4 km; a
bounding-box search was returning global files; the OCO-2 version mix-up; an IQR filter that
removed 29% of data; a wrong assumption that road transport is high-CO. Each was caught by
sanity-checking against physics or by testing on synthetic data.

**Q27. So does multi-source data improve CO₂ estimation?**
For Pune, yes, through TROPOMI CO: it narrows the dominant error term and cuts total uncertainty
from 32% to 24%. Direct CO₂ satellites give only an upper bound for a city of this size. Both halves
of that answer are useful.

**Q27b. What was the biggest mistake you found, and how?**
The plume fit originally reached 60 km downwind, which included a second source (PCMC/Talegaon) and biased NOx
~20% low. A sloped-background robustness test exposed it. We fixed the window, reran everything, and withdrew a
conclusion that had depended on the biased number (D19).

**Q29. How did you build the Phase 2 feature table?**
A 1 km UTM grid over the corridor (268 cells, kept if ≥ 50% inside), then every layer averaged onto the cells per month:
- NO₂ and terrain-normalised CO from our TROPOMI cubes;
- HCHO, VIIRS and ERA5 temperature/radiation from Earth Engine;
- Sentinel-2 NDVI/NDBI per season;
- roads.

The result is 10,720 rows, 16 features, 0 missing, with QA histograms and spot checks. Inventories are kept as reference columns, never features.

**Q30. Why HCHO and not ozone as the chemistry proxy?**
TROPOMI ozone is a total column dominated by the stratosphere, so it says almost nothing about city chemistry, and
reanalysis chemistry is ~50 km. HCHO tracks reactive VOCs on the same grid. Temperature and sunlight drive the chemistry (D14).

**Q31. Your roads come from GRIP4, not OpenStreetMap as proposed. Why?**
The OSM servers (and mirrors, and Geofabrik) were overloaded for hours; caching and mirrors only got 16 of 35 tiles.
GRIP4 is a published global road dataset available inside Earth Engine. v1 uses it and records the source; v2 will use
OSM with GRIP4 as a cross-check. Its weakness is sparse local roads (D20).

**Q32. How did you convert the midday satellite rate to an annual figure?**
EDGAR's published temporal profiles, weighted by Pune's sector mix and our actual overpass hours and months, give
F ≈ 1.23: midday October–May runs ~23% above the annual mean, mostly because daytime traffic is ×1.6.

**Q33. Why a Monte Carlo instead of root-sum-square?**
It multiplies the real input distributions through the whole chain, keeps values positive, and gives asymmetric ranges.
It also lets us show the known +12% method bias both uncorrected (headline) and corrected (sensitivity).

**Q34. How do you know the seasonal differences are real?**
The between-season spread (0.43–0.73 kg/s) is 2.8× the within-season bootstrap uncertainty, and an independent model-free
check sees the 2020 lockdown (−74%) and the 2021 restrictions (−29%).

**Q28. What comes next?**
Phase 2: gridded human-activity layers (night-lights, roads, Sentinel-2). Phase 3: labels from the
satellite flux-divergence shares, which avoids the circularity of labelling with the same proxies
used as features (D2/D10). Then ML experiments, with Experiment B reframed around TROPOMI CO.
