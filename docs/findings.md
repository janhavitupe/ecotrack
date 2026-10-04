# EcoTrack — Findings to Date

**Project:** Meteorology-informed multi-source satellite estimation of urban fossil-fuel CO₂, Shivajinagar → Talegaon Dabhade corridor, Pune
**Author:** Janhavi Tupe · **Covers:** feasibility stage (G1–G4), Phase 1, and Phase 2 (in progress) — (NO₂ inversion, NOx → CO₂, inventory comparison, OCO check, TROPOMI CO sector constraint; all numbers after IQR outlier removal) · **Last updated:** 2026-09-24

This document collects every result so far in one place. Day-by-day detail is in
[research_log.md](research_log.md), and the reasoning behind each design change is in
[decisions.md](decisions.md). All numbers below come from files in `outputs/` and can be
regenerated with the commands in §9.

---

## 1. Key findings at a glance

*Current values after D19 (fit window ≤ 45 km, sloped background). Earlier numbers in §4.3–4.12 are the pre-D19 record; §4.0 has the revised tables.*

1. **The data supports the project.** TROPOMI gives a median of **26 usable days per month** over the corridor (G2). All three corridor clusters show NO₂ **1.7–2.4× above regional background** in every season (G3).
2. **Direct CO₂ observations are sparse.** **Pune is an OCO-3 Snapshot Area Map target**, with **8 strong direct-CO₂ dates** (7 OCO-3 + 1 OCO-2).
3. **The proposal's waypoints were up to 4.4 km off**, and Talegaon MIDC lay outside the original corridor. Both are fixed: the corridor is built on the real highway (D9, 269 km²).
4. **Pune + PCMC emit 0.663 kg/s NOx** [95% CI 0.620–0.715] at midday, with an NO₂ lifetime of **1.09 h** [0.96–1.23] (EMG, R² = 0.998; D19).
5. **Every estimator was tested on synthetic plumes**: EMG +11–12% (a measured bias, unchanged by D19); flux divergence −4%; CO step −1.4%. The converged DE fits give one optimum whatever the settings, and IQR filtering changes the results by < 2%.
6. **D19, a correction found by testing:** the original fit window (to 60 km downwind) included PCMC/Talegaon as a *second* source, biasing NOx **low by ~20%** (0.522 → 0.663 kg/s). Inside 30–45 km, flat and sloped backgrounds agree (0.59–0.66). This revised several downstream conclusions (items 9–13).
7. **The strongest NO₂ source is central Pune, just south of the corridor.** A second, distinct hotspot sits on **Pimpri–Chinchwad** (inside the corridor), 16.7 km away. **The corridor emits ~21% of the metro's NOx**, a share stable to ±2.4% across every sensitivity test and season.
8. **Two independent methods agree on location and broadly on size:** within 25 km, flux divergence gives 0.787 kg/s vs EMG 0.663 (+19%; flux-divergence totals depend on the lifetime, D10).
9. **Satellite vs inventories (annual-mean basis, D17):** satellite NOx **17.0–17.5 kt/yr vs EDGAR 21.1 (−17 to −19%)**. **EDGAR and ODIAC disagree 3.2×** (3.6 vs 11.8 Mt CO₂/yr).
10. **TROPOMI CO measures Pune's CO:NOx: 16.7 mol/mol [14.7–18.8], consistent with EDGAR's 16.0** (+4%). This constrains the NOx → CO₂ ratio to **163 (95%: 148–180)** instead of the sector span 115–393. *(Pre-D19 this read 21.2 and suggested "more household burning than EDGAR"; that was an artefact of the underestimated NOx and is withdrawn.)*
11. **Headline fossil CO₂ (Monte Carlo, D18): 2.79 Mt/yr annual mean [95%: 1.79–4.36]**; midday October–May rate 3.39 [2.26–5.08]. EDGAR's 3.63 lies inside the range; **ODIAC's 11.8 lies far outside** (≥ 2.7× the upper bound) in every variant.
12. **OCO-3/OCO-2 cannot see Pune's CO₂ plume** (0.02–0.15 ppm vs 0.5–1 ppm noise/artefacts). Consistent (β = 0.81 ± 0.74 / 1.57 ± 1.44; EDGAR implies β = 1.01) but only an **upper limit of ~7–14 Mt/yr** (D11).
13. **Multi-source data do improve the estimate, through TROPOMI CO, not OCO:** the dominant ratio term falls from 25% (the base paper's value) to ~10% (scenario spread 9.9% + an assumed 10% for EDGAR's sector ratios).
14. **The pipeline sees real-world changes.** Seasonal NOx is resolvable (between/within ratio 2.8; 0.43–0.73 kg/s). The city's NO₂ excess fell **74%** in the 2020 lockdown and **29%** in the 2021 restrictions.
15. **A CO-based emission map works independently of NO₂** (25 km total within 3% of the CO step; r = 0.75 with NO₂). The corridor holds **14.5% of the city's CO vs 21.0% of its NOx**: an exploratory sign of **industrial corridor vs residential core**.
16. **Winds reverse seasonally:** east-southeast in October–March (Pune's plume carried up the corridor), west-northwest in April–May.

---

## 2. Study setup (as finalised)

| Item | Value |
|---|---|
| Study period | 1 October 2019 – 31 May 2024, **October–May only** (5 dry seasons, 40 months) |
| Corridor | Old Pune–Mumbai Highway centreline ± 3.5 km, **plus Talegaon MIDC** (2.5 km circle): **269 km²**, one polygon (D9) |
| Clusters | C1 Shivajinagar–Kasarwadi · C2 PCMC (Pimpri, Chinchwad, Akurdi, Nigdi) · C3 Dehu Road–Talegaon |
| NO₂ | TROPOMI OFFL L3 via Google Earth Engine, cloud fraction ≤ 0.3, solar zenith ≤ 70°, IQR outlier removal (per-pixel time series, k = 3; D13) |
| CO₂ | OCO-3 Lite v11r; OCO-2 Lite v11.2r (2019–2023) / v11.3r (2024), quality flag = 0 |
| Meteorology | ERA5 hourly: wind at 10 m, 100 m and 850 hPa; boundary-layer height |
| All thresholds | [configs/study.yaml](../configs/study.yaml), the single source of truth |

---

## 3. Feasibility findings (G1–G4)

### G2 — TROPOMI coverage: **PASS**

| Month | Oct | Nov | Dec | Jan | Feb | Mar | Apr | May |
|---|---|---|---|---|---|---|---|---|
| Mean usable days (5-season average) | 17.4 | 21.8 | 23.4 | 26.4 | 27.6 | 28.8 | 26.2 | 24.6 |

- Median **26** usable days per month; minimum **13** (October 2019 and October 2020); no month below 5. **Monthly composites are viable.**
- October is consistently the weakest month, probably because of late-monsoon cloud.
- "Usable" means at least 50% of the corridor's 230 TROPOMI pixels pass QC on that overpass.
- **Methods note:** the GEE TROPOMI product **has no `qa_value` band**; GEE applies the quality filter during its own processing. Our QC is therefore "GEE's built-in qa filter + cloud fraction ≤ 0.3 + solar zenith ≤ 70°", not "qa ≥ 0.7 applied by us".

### G3 — NO₂ signal over the clusters: **PASS**

Enhancement = cluster mean ÷ 10th percentile of the regional box (73.30–74.30 E, 18.20–19.00 N), per season:

| Season | C1 Shivajinagar–Kasarwadi | C2 PCMC | C3 Dehu Road–Talegaon | Background (mol/m²) |
|---|---|---|---|---|
| 2019–20 | 2.22× | 2.10× | 1.74× | 2.49 × 10⁻⁵ |
| 2020–21 | 2.29× | 2.24× | 1.81× | 3.06 × 10⁻⁵ |
| 2021–22 | 2.31× | 2.15× | 1.71× | 2.87 × 10⁻⁵ |
| 2022–23 | 2.31× | 2.21× | 1.77× | 3.25 × 10⁻⁵ |
| 2023–24 | 2.37× | 2.25× | 1.78× | 3.09 × 10⁻⁵ |

- Every cluster is above the 1.5× threshold in every season, and the ranking never changes.
- **Caveat, confirmed in Phase 1:** C1's high value partly reflects central Pune next door, and C3's partly reflects NO₂ carried downwind from PCMC. G3 shows that a signal exists, not that the clusters are separable.

### G1 — Direct CO₂ observations (OCO-3 and OCO-2): **PARTIAL**

**OCO-3** (893 in-season days scanned, 0 failed downloads):
- Inside the 7 km-wide corridor: 236 good soundings on 10 days, **6 usable** (≥ 20 soundings).
- At city scale (bounding box): **7 strong days** (≥ 50 good soundings).

| Date | Good soundings (bbox) | Mode |
|---|---|---|
| 2019-10-14 | 56 | Snapshot Area Map |
| 2020-04-21 | 66 | Nadir |
| 2020-12-20 | 130 (> 1,100 in the wider area) | Snapshot Area Map |
| 2020-12-24 | 133 (> 1,100 in the wider area) | Snapshot Area Map |
| 2021-01-01 | 51 | Snapshot Area Map |
| 2022-01-27 | 112 | Snapshot Area Map |
| 2022-11-21 | 60 | Snapshot Area Map |

- **Pune is an OCO-3 Snapshot Area Map target:** snapshot mode over Pune on at least 9 dates in 2019–2023. Several were lost to cloud (e.g. May 2021: 427 soundings, 0 good quality).
- Most good soundings fall just outside the corridor, so OCO-3 works here at **city scale, not grid-cell scale**.
- **Data gaps:** no OCO-3 data from 20 Oct to 26 Nov 2019 (early mission) or from **December 2023 to May 2024**.

**OCO-2** (1,177 in-season days scanned): **1 strong day**, 2024-01-23. A glint-mode track crosses C1 and C2 with 60 good soundings in the corridor. It falls in the one season OCO-3 misses.

**Conclusion:** 8 direct-CO₂ dates. Too sparse for per-cell machine learning; used instead as an independent city-scale check on the NO₂-derived CO₂ (**D8, pending guide approval**).

### G4 — Waypoints and corridor geometry: **FIXED**

- **6 of the 10 proposal waypoints were more than 500 m from OpenStreetMap**: Dehu Road by **4.4 km** (it pointed at Dehu town), Talegaon by 2.1 km, and Pimpri, Chinchwad, Nigdi and Kasarwadi by 1.3–1.5 km.
- OSM place centres are neighbourhood centroids, so a corridor drawn through them zigzags. The corridor is therefore built from each waypoint **snapped to the actual highway**: 30.2 km, a median 200 m from the real road.
- **MIDC Bhosari:** 99% inside. **Talegaon MIDC:** ~5 km north of Talegaon town and outside the original buffer; added as a 2.5 km circle (77% of nearby industrial land now inside).
- **Chakan industrial area:** outside the corridor to the NE. It is a possible upwind source on NE-wind days.

### Meteorology at overpass time (ERA5, 1,031 overpasses)

| | 10 m | 100 m | 850 hPa |
|---|---|---|---|
| Median wind speed (m/s) | 2.5 | 3.2 | 3.5 |

- Boundary-layer height: median **1.66 km** (10th–90th percentile 1.06–2.94 km). Pune sits at ~560 m, so 850 hPa (~1 km above ground) lies inside the afternoon boundary layer, the level that best represents plume transport.
- Wind classes at 850 hPa: 192 calm (< 2 m/s) · 429 at 2–4 · 334 at 4–7 · 73 above 7 m/s.
- **Two wind regimes:** **October–March from the east-southeast** (central Pune upwind of PCMC and Talegaon; pollution carried *along* the corridor) and **April–May from the west-northwest** (reversed).
- TROPOMI overpasses fall at 06–08 UTC (11:30–13:30 IST).

---

## 4. Phase 1 — NO₂ inversion

### 4.0 Current results after D19 (these supersede the numbers in §4.3–4.12)

**What changed:** the EMG is fitted only to 45 km downwind (beyond that PCMC/Talegaon add a second source) with a sloped background (B + c·x). A quality rule sends unconstrained sloped fits (τ < 0.6 h or bootstrap range > ×2) back to a flat background (the westerly regime and the 2023–24 season). The background/window spread enters the budget (5.4%). Details: D19. Pre-D19 outputs: `outputs/phase1/v2_before_d19/`.

**City NOx (EMG):**

| Run | n | E(NOx) kg/s [95% CI] | τ (h) [95% CI] | R² |
|---|---|---|---|---|
| **Main (850 hPa, 2–8 m/s, ≤ 45 km, sloped)** | 781 | **0.663 [0.620–0.715]** | **1.09 [0.96–1.23]** | 0.998 |
| Easterly regime | 429 | 0.600 [0.565–0.651] | 1.53 | 0.998 |
| Westerly regime (flat fallback) | 276 | 0.484 [0.443–0.531] | 1.94 | 0.984 |
| Wind 2–4 / 4–8 m/s | 416 / 365 | 0.567 / 0.695 | 1.47 / 0.84 | 0.997 / 0.999 |
| Wind at 100 m / 10 m | 782 / 675 | 0.673 / 0.556 | 0.95 / 1.05 | 0.999 / 0.999 |
| Structure: flat 45 km / sloped 30 km / *original flat 60 km* | 781 | 0.591 / 0.651 / *0.522* | 1.46 / 0.85 / *1.67* | – |

- Midday rate 20.9 kt NOx/yr [19.6–22.5].
- The wind-level sensitivity nearly vanishes (100 m within 1.5%).
- **DE settings:** all 24 converged fits (CR 0.7/0.9) give the identical optimum (0.6627 kg/s). Only CR = 0.3 runs (12) hit the iteration limit before converging with 6 parameters; they lie within 3% of the optimal cost.

**Seasons (flux-divergence corridor share):** 2019–20 0.434 [0.370–0.511] (22.4%) · 2020–21 0.602 (20.1%) · 2021–22 0.733 (22.1%) · 2022–23 0.666 (20.0%) · 2023–24 0.663 (flat fallback; 21.1%). Between/within ratio **2.8**.

**Flux divergence** (τ = 1.09 h): 25 km **0.787 kg/s** (EMG +19%); corridor 0.165 kg/s; **shares unchanged**: corridor 21.0%, Pune core 27.6%, C1 9.8%, C2 6.3%, C3 4.9%.

**NOx → CO₂:**

| | Value |
|---|---|
| CO:NOx (TROPOMI CO step / EMG NOx) | **16.7 mol/mol [14.7–18.8]** vs EDGAR 16.0 (+4%) |
| Sector scenarios (all four feasible now) | high-CO group 173 [166–180] · industry vs transport 154 [148–169] · residential vs industry 162 [154–171] · residential vs transport 161 [156–167] |
| **CO-constrained CO₂:NOx** | **163 (95%: 148–180)** (EDGAR 172) |
| Fossil CO₂, midday rate | **3.40 Mt/yr** (CO ratio) · 3.60 (EDGAR ratio) |
| RSS budget (1σ) | 23.0% (CO ratio) · 30.9% (EDGAR ratio) |

RSS budget terms (CO ratio): bootstrap 3.6% · wind level 0.8% · wind regime 8.8% · EMG bias 12.0% · NOx/NO₂ 7.6% · EDGAR year 3.1% · **EMG structure (D19) 5.4%** · CO-ratio scenarios 9.9% · per-sector ratios (assumed) 10.0%.

**Annual mean (D17, F = 1.197–1.231):** NOx **17.0–17.5 kt/yr** (EDGAR 21.1 → −17 to −19%); CO₂ 2.76–2.84 Mt/yr (CO ratio).

**Monte Carlo (D18, 200k draws):**

| Fossil CO₂ (Mt/yr) | Median | 68% | 95% |
|---|---|---|---|
| Midday, symmetric | 3.39 | 2.76–4.16 | 2.26–5.08 |
| **Annual, symmetric (headline)** | **2.79** | 2.23–3.50 | **1.79–4.36** |
| Annual, bias-corrected | 2.51 | 2.05–3.05 | 1.69–3.69 |

EDGAR (3.63) is inside both 95% ranges; ODIAC (11.8) is outside both.

**OCO check:** β = 1.57 ± 1.44 (25 km prior), 0.81 ± 0.74 (10 km prior); EDGAR implies β = 1.01; upper limits unchanged (7.3 / 14.2 Mt/yr); ODIAC 1.2σ / 3.3σ away.

**Unchanged by D19:** source location and hotspots; corridor share; the COVID check (model-free); the CO flux-divergence map (248 mol/s; corridor 14.5%); OCO non-detection.

**Conclusion revised:** the pre-D19 claim that the excess CO implied "more household/biomass burning than EDGAR" is **withdrawn**. With unbiased NOx, Pune's CO:NOx matches EDGAR's, and the CO constraint narrows the CO₂:NOx ratio without contradicting EDGAR's sector mix.

### 4.1 Method validation on synthetic plumes

Before running on real data, both methods were tested on a simulated point source with known emission (0.5 mol/s NO₂) and lifetime (3 h), on the real TROPOMI grid, with random winds and retrieval-like noise ([tests/](../tests/)).

| Method | Emission recovered | Lifetime recovered | Notes |
|---|---|---|---|
| EMG (wind rotation + line density) | **+11 to +12%** | **−16 to −17%** | R² 0.99; the same bias in both random seeds → systematic |
| Flux divergence | **−4%** | (lifetime is an input) | Stable at 15, 25 and 35 km radii; no spurious source away from the plume |
| CO step (inert tracer, §4.8) | **−1.4%** | (no decay) | Static terrain pattern larger than the plume; terrain alone gives ≈ 0 |
| IQR outlier filter (temporal, k = 3; D13) | line density changed 0.9% | – | Catches 92% of injected spikes; the "domain" variant would clip the plume (−7%) |

**Where the EMG bias comes from** (measured by switching each factor off):
- ~2%: the ±20 km across-wind window cuts off the widening plume
- ~6%: averaging days with different wind speeds
- ~4%: 2 km binning near the source

This bias is **measured, not assumed**, and enters the uncertainty budget.

### 4.2 Source location

The calm-wind composite (187 overpasses, wind < 2 m/s) peaks at **18.485 N, 73.855 E**, around Swargate/Camp in central Pune, **~2 km south of the corridor's southern tip**. PCMC appears as a secondary NO₂ ridge along the corridor.

![Calm-wind NO₂ composite](../outputs/phase1/figures/calm_composite.png)

### 4.3 City-scale emission (EMG, the base paper's method)

Settings: IQR-filtered cube (D13), 850 hPa wind, overpasses with 2–8 m/s wind, Differential Evolution (population 300, F ∈ [0.5, 1.0], CR = 0.7), 200-member bootstrap over overpasses, NOx/NO₂ = 1.32.

| Run | n | E(NOx) kg/s [95% CI] | ≈ kt/yr* | τ (h) [95% CI] | x₀ (km) | w (m/s) | R² |
|---|---|---|---|---|---|---|---|
| **Main: all windy days** | **781** | **0.522 [0.486–0.555]** | **16.5** | **1.67 [1.55–1.81]** | 25.0 | 4.14 | 0.991 |
| Easterly regime (from 45–180°) | 429 | 0.561 [0.521–0.604] | 17.7 | 1.42 [1.31–1.54] | 21.5 | 4.22 | 0.990 |
| Westerly regime (from 225–360°) | 276 | 0.442 [0.388–0.494] | 14.0 | 2.18 [1.86–2.54] | 33.8 | 4.31 | 0.979 |
| Wind 2–4 m/s | 416 | 0.478 [0.437–0.511] | 15.1 | 1.97 [1.80–2.13] | 21.4 | 3.01 | 0.994 |
| Wind 4–8 m/s | 365 | 0.506 [0.464–0.546] | 16.0 | 1.62 [1.47–1.82] | 31.8 | 5.44 | 0.985 |
| Wind at 100 m | 782 | 0.456 | 14.4 | 1.82 | 25.7 | 3.92 | 0.981 |
| Wind at 10 m | 675 | 0.347 | 11.0 | 2.35 | 27.9 | 3.31 | 0.977 |

\* *Midday emission rate multiplied by one year; not an annual total (no night-time or monsoon data).*

- **The wind level is the largest single sensitivity.** Surface (10 m) wind is too slow to represent a plume ~1 km deep, which is why 850 hPa is the physically preferred choice.
- The two regimes differ by ~23%. The westerly regime has fewer overpasses and a longer lifetime.
- **Differential Evolution settings (proposal step 4):** the main fit was repeated for 36 combinations: population 150 / 300, F = [0.5, 1.0] dithered / 0.5 / 0.9, CR = 0.3 / 0.7 / 0.9, two seeds. **All converged to the same optimum**: E(NOx) 0.5220 kg/s and τ 1.672 h, spread < 0.001%. The result doesn't depend on the optimiser settings (`outputs/phase1/de_sensitivity.json`, `figures/de_sensitivity.png`).
- **Misfit:** the line density rises again 50–60 km downwind. In east-southeast winds that direction is up the corridor, so this is PCMC and Talegaon appearing as additional sources that a single-source fit cannot separate.

![EMG line density fit](../outputs/phase1/figures/line_density_main.png)
![Sensitivity of the EMG estimate](../outputs/phase1/figures/sensitivity.png)

### 4.4 Spatial attribution (flux divergence)

Settings: 968 overpasses (wind ≤ 8 m/s), IQR-filtered, 850 hPa wind, lifetime 1.67 h from EMG, background = 10th percentile of the mean column (2.96 × 10⁻⁵ mol/m²), 200-member bootstrap.

**Two distinct hotspots, 16.7 km apart:**

| Hotspot | Location | Within 4 km | Within 6 km | Within 8 km |
|---|---|---|---|---|
| Central Pune | 18.485 N, 73.855 E (outside the corridor) | 0.047 | 0.091 | 0.147 kg/s |
| **Pimpri–Chinchwad** | **18.625 N, 73.795 E (inside the corridor)** | 0.034 | 0.069 | 0.112 kg/s |

The Pune hotspot sits exactly where the EMG placed its source. The PCMC peak reaches 73% of Pune's intensity.

**Zone totals** (NOx, kg/s, 95% bootstrap CI):

| Zone | Pixels (~km²) | Emission | ≈ kt/yr* |
|---|---|---|---|
| Pune core (≤ 10 km from source, outside the corridor) | 222 | 0.168 [0.162–0.176] | 5.3 |
| C1 Shivajinagar–Kasarwadi | 77 | 0.058 [0.056–0.061] | 1.8 |
| C2 PCMC | 55 | 0.037 [0.035–0.039] | 1.2 |
| C3 Dehu Road–Talegaon | 97 | 0.025 [0.023–0.028] | 0.8 |
| **Whole corridor** | 229 | **0.120 [0.116–0.125]** | **3.8** |

Corridor pixels are assigned to the cluster of their nearest waypoint, so zones don't overlap. The corridor zones are only 1–2 TROPOMI pixels wide, so some emission smears across zone edges. The equal-radius hotspot circles above are the fairer Pune-vs-PCMC comparison.

![Flux-divergence NOx emission map](../outputs/phase1/figures/divergence_map.png)
![Emission by zone](../outputs/phase1/figures/divergence_zones.png)

### 4.5 Do the two methods agree?

| Radius around source | 5 | 10 | 15 | 20 | **25** | 30 | 35 km |
|---|---|---|---|---|---|---|---|
| Flux divergence (kg/s) | 0.068 | 0.204 | 0.341 | 0.467 | **0.570** | 0.643 | 0.699 |

- **At 25 km, flux divergence (0.57 kg/s) agrees with EMG (0.52 kg/s) within 9%**, and both put the main source at the same pixel.
- **Unlike the synthetic test, the real total doesn't level off with radius.** Splitting it into its two terms:
  - the **flux term** levels off at ~0.16 kg/s, as expected;
  - the **lifetime (sink) term** keeps growing and is ~70% of the 25 km total. NO₂ 30–35 km out is still ~24% above the chosen background.
- **So absolute flux-divergence totals depend on the lifetime and the background choice**, while the spatial *pattern* does not:

| Sensitivity run | Corridor total (kg/s) | Corridor share of 25 km total | C2 / Pune core |
|---|---|---|---|
| Main | 0.120 | 0.211 | 0.219 |
| Lifetime × 0.7 | 0.156 | 0.210 | 0.228 |
| Lifetime × 1.3 | 0.101 | 0.212 | 0.213 |
| Lifetime ÷ 0.84 (synthetic-bias corrected) | 0.107 | 0.211 | 0.215 |
| Background 5th percentile | 0.124 | 0.208 | 0.220 |
| Background 25th percentile | 0.113 | 0.218 | 0.218 |
| Wind at 100 m | 0.119 | 0.218 | 0.231 |

**The absolute corridor total ranges −16% to +30%; the corridor share varies by only ±2.4%.** This is the basis for D10: the **city total comes from EMG**, and the **split between zones from flux-divergence shares**.

![Flux divergence vs EMG](../outputs/phase1/figures/divergence_vs_emg.png)

### 4.6 NOx → fossil CO₂ and comparison with inventories

**Inventories used** (clipped to the study box; roles per the proposal's design rule):
- **EDGAR v8.1 NOx + v8.0 fossil CO₂.** Both share the FT2022 activity data; 0.1° annual grids, 2019–2022 totals, all sectors for 2021. **Role: source of the CO₂:NOx ratio (a prior) and a plausibility comparison.**
- **ODIAC v2024.** 1 km monthly grid, 35 October–May months to December 2023. **Units: tonnes of carbon per cell per month** (US GHG Center documentation), converted ×44/12. **Role: plausibility comparison only**. It spreads emissions using nighttime lights, so it isn't independent of VIIRS.

**Comparison area:** within 25 km of the source, where the two satellite methods agree (§4.5).

**NOx: satellite vs EDGAR**

| | NOx (kt/yr) |
|---|---|
| Satellite (EMG, midday rate) | **16.5** [95% CI 15.4–17.5] |
| EDGAR v8.1 (2019–2022 mean) | 21.1 (2019 21.2 · 2020 20.4 · 2021 21.0 · 2022 21.7) |
| **Satellite / EDGAR** | **0.78** |

A midday rate would normally be *higher* than the daily mean (traffic and industry peak in the day), so the satellite being 22% lower suggests either EDGAR overestimates Pune's NOx, or the fitted background in the EMG absorbs diffuse emissions. **Not yet resolved.**

**The CO₂:NOx ratio (EDGAR, same area)**

| | 2019 | 2020 | 2021 | 2022 | Mean |
|---|---|---|---|---|---|
| t CO₂ per t NOx | 175.9 | 165.5 | 170.8 | 176.1 | **172.1** |

Excluding NOx with no fossil-CO₂ counterpart (agricultural soils and crop burning) gives 175.0. **By sector (2021) the ratio varies roughly threefold:**

| Sector (EDGAR 2021, within 25 km) | NOx (t) | CO₂ (t) | CO₂:NOx |
|---|---|---|---|
| Industry (combustion) | 13,479 | 1,548,077 | 115 |
| Road transport | 4,149 | 723,788 | 174 |
| Residential & commercial | 2,083 | 819,005 | 393 |
| Power generation | 580 | 164,583 | 284 |
| Aviation (landing/take-off) | 73 | 21,420 | 295 |
| Chemicals (CO₂ only) | 0 | 187,708 | – |

**So the city-wide ratio hinges on how much of Pune's NOx really comes from industry versus traffic and households.** That is exactly what the NO₂ data alone can't tell us, and why TROPOMI CO (D4) and OCO-3 (D8) matter.

**Fossil CO₂, Pune + PCMC within 25 km**

| Estimate | Fossil CO₂ (Mt/yr) |
|---|---|
| **Satellite (TROPOMI NO₂ × EDGAR ratio), midday rate** | **2.83 ± 32% (1σ) → 1.93–3.74** |
| EDGAR v8.0 (2019–2022 mean) | 3.63 |
| ODIAC v2024 (October–May months × 12) | 11.8 |

- The satellite CO₂ is **not independent of EDGAR**: it uses EDGAR's ratio. It differs from EDGAR only because the satellite NOx is 22% lower.
- **ODIAC is 3.2× EDGAR in the same area.** A plausible explanation (to be checked) is ODIAC's nighttime-light-based allocation concentrating emissions in brightly lit cities. Inventory disagreement of this size at city scale is itself a finding.

![City CO₂: satellite vs inventories](../outputs/phase1/figures/co2_city_comparison.png)

**Zones (city CO₂ × flux-divergence share, D10)**

| Zone | Share of city | Satellite CO₂ (Mt/yr) |
|---|---|---|
| Pune core (outside the corridor) | 29.5% | 0.84 |
| C1 Shivajinagar–Kasarwadi | 10.1% | 0.29 |
| C2 PCMC | 6.5% | 0.18 |
| C3 Dehu Road–Talegaon | 4.5% | 0.13 |
| **Corridor** | **21.1%** | **0.60** |

Inventory corridor totals for comparison: EDGAR 1.15 Mt/yr, ODIAC 4.04 Mt/yr. The corridor extends beyond the 25 km circle toward Talegaon, so the shares don't sum to 100%.

**First uncertainty budget (relative, 1σ, root-sum-square)**

| Term | 1σ |
|---|---|
| EDGAR ratio representativeness (the base paper's value) | 25.0% |
| EMG method bias (synthetic test; systematic, kept uncorrected) | 12.0% |
| Wind regime (E-SE vs W-NW, half-difference) | 11.4% |
| NOx/NO₂ ratio (1.32 ± 0.1) | 7.6% |
| Wind level (850 hPa vs 100 m, half-difference) | 6.4% |
| EMG fit + sampling (bootstrap) | 3.3% |
| EDGAR ratio: year-to-year + combustion-only choice | 3.1% |
| **Total** | **31.9%** |

The 25% term comes from the base paper and **may be optimistic** here, given the sector ratios above. The OCO-3 mass-balance check (D8) is designed to test it directly.

![Uncertainty budget](../outputs/phase1/figures/co2_uncertainty_budget.png)

### 4.7 Independent check with OCO-3 / OCO-2 (D8, exploratory)

**Method (plume-model scaling).** For each of the 8 dates:
1. Take the flux-divergence emission map scaled to 2.83 Mt CO₂/yr.
2. Carry it downwind as a Gaussian column plume on that day's ERA5 850 hPa wind, at the OCO overpass hour.
3. Regress observed XCO₂ on the predicted enhancement, plus a linear regional gradient.

The slope β measures observed ÷ predicted: β = 1 means OCO agrees with our estimate, and β × 2.83 Mt/yr is an emission estimate **independent of EDGAR's CO₂:NOx ratio**.

| Date (IST) | Soundings | Wind (m/s, from) | Predicted max (ppm)* | β ± 1σ* |
|---|---|---|---|---|
| OCO-3 2019-10-14 08:52 | 167 | 8.9, 98° | 0.04 | 10.9 ± 5.8 |
| OCO-3 2020-04-21 15:31 | 208 | 7.0, 288° | 0.06 | −7.9 ± 3.9 |
| OCO-3 2020-12-20 15:16 | 890 | 6.1, 100° | 0.07 | −3.7 ± 1.8 |
| OCO-3 2020-12-24 13:42 | 917 | 3.7, 122° | 0.11 | 5.0 ± 0.8 |
| OCO-3 2021-01-01 10:34 | 252 | 4.8, 159° | 0.08 | 1.7 ± 3.9 |
| OCO-3 2022-01-27 14:03 | 397 | 3.2, 113° | 0.13 | −0.2 ± 0.9 |
| OCO-3 2022-11-21 16:04 | 247 | 2.9, 66° | 0.15 | −10.1 ± 1.8 |
| OCO-2 2024-01-23 13:51 | 230 | **0.6**, 106° | 0.41 | 1.16 ± 0.33 |

\* *With emissions confined to 10 km of the source. Spreading them over 25 km lowers the predicted maxima to 0.02–0.07 ppm.*

**Combined (inverse-variance, error inflated for between-date scatter):**

| Emission prior | β | Between-date χ² | 95% upper limit | 3σ detection threshold |
|---|---|---|---|---|
| Confined to 10 km | **1.02 ± 0.94** | 11.1 | E < 7.3 Mt/yr | ~8 Mt/yr |
| Spread over 25 km | 2.00 ± 1.81 | 14.3 | E < 14.1 Mt/yr | ~15 Mt/yr |
| 10 km, without the near-calm date | 0.65 ± 1.93 | 12.9 | E < 10.8 Mt/yr | – |

**What this means**
- **Not a detection.** The predicted plume is 10–20× smaller than the sounding scatter (0.5–1.1 ppm) and the **swath-to-swath stripes** visible on the Snapshot Area Map dates (retrieval artefacts of 0.5–1 ppm). The dates disagree with each other far more than their error bars allow.
- β ≈ 1 with the 10 km prior is **consistent with, not a confirmation of**, the NO₂-based estimate. It leans heavily on the one near-calm OCO-2 date, where a steady-state plume model is not valid.
- **EDGAR (β = 1.28) is consistent in every variant.** ODIAC (β = 4.16) is 3.3σ away with the 10 km prior but only 1.2σ with the 25 km prior: **a tentative, non-robust hint that ODIAC is too high for Pune.**
- **Answer to the research question for this corridor:** current CO₂ satellites give an *upper bound* on Pune's emissions, not an independent measurement, because Pune (~3–4 Mt/yr) is below the ~8–15 Mt/yr detection threshold of these 8 overpasses. The proposal's success criteria (§11) count this as a valid result.
- A possible improvement before finalising: per-swath offset terms in the regression, to absorb the stripe artefacts.

![OCO soundings vs predicted plume](../outputs/phase1/figures/oco_dates_r10.png)
![Scale factor per date](../outputs/phase1/figures/oco_beta_r10.png)

### 4.8 TROPOMI CO: constraining the sector mix and the CO₂:NOx ratio (D4)

**Why:** the NOx → CO₂ ratio was the largest error term (§4.6), and OCO could not test it (§4.7). Sectors differ strongly in how much CO they emit per NOx, so measuring Pune's CO:NOx tells us the sector mix, and with it which CO₂:NOx ratio applies.

**Data:** TROPOMI OFFL L3 CO via Earth Engine (pre-filtered qa > 0.5; solar zenith ≤ 70°), same 0.01° grid as NO₂: **907 overpasses**, 608 with 2–8 m/s wind. SRTM elevation on the same grid. EDGAR v8.1 CO (totals 2019–2022, sectors 2021).

**The terrain problem.** A CO column measures all the air above the ground. The Pune plateau (~560 m) and the Konkan lowlands (~0 m) differ by ~6% in air mass, **more than Pune's own CO signal (~2%)**; the raw January mean peaked over the Konkan, not Pune.

**Method (robust to terrain):**
1. Divide each column by the relative air mass, exp(−z/H) with H = 8.4 km, using elevation smoothed to the ~5 km CO footprint.
2. Remove each day's box median.
3. **Remove each pixel's long-term mean.** Anything fixed in space disappears, including residual terrain and the city's direction-averaged CO dome.
4. Rotate each day by its wind. The downwind-minus-upwind line density (20–40 km windows) equals the full step, so E(CO) = step ÷ ⟨1/w⟩.

**Synthetic test** (`tests/test_co_step.py`): an inert source of 100 mol/s with a static terrain pattern *larger than the plume* is recovered as **98.6 mol/s (−1.4%)**; **terrain alone gives −0.8 mol/s (≈ 0)**.

**Result:**

| | Value |
|---|---|
| CO step (downwind − upwind line density) | 65.0 mol/m |
| **E(CO)** | **6.73 kg/s** |
| **CO:NOx emission ratio** (NOx from EMG) | **21.2 mol/mol [95% CI 18.7–23.8]** |
| EDGAR CO:NOx, same 25 km area | 16.0 mol/mol → **observed is 33% higher** |

| Sensitivity | CO:NOx |
|---|---|
| Scale height 7.5 / 9.5 km | 21.4 / 21.0 |
| No terrain correction | 19.5 |
| October–January only | 22.0 |
| February–May only (fire season) | 20.5 (no sign of fire inflation) |

![CO step over Pune](../outputs/phase1/figures/co_step.png)

**What the excess CO means (EDGAR 2021 sector ratios, same area):**

| Sector | CO:NOx (mol/mol) | CO₂:NOx (t/t) | EDGAR share of NOx |
|---|---|---|---|
| Industry | 9.9 | 115 | 64% |
| Road transport | 1.95 | 174 | 20% |
| Residential & commercial | 77.9 | 393 | 10% |
| Power | 0.38 | 284 | 3% |

Re-splitting one sector pair at a time (all others held at EDGAR shares) to match the observed 21.2:

| Scenario | Feasible? | Implied change | CO₂:NOx [95%] |
|---|---|---|---|
| A: high-CO group (residential + crop burning) vs rest | yes | high-CO share of NOx 18.5% (EDGAR 11%) | 188 [179–197] |
| B: industry vs transport | **no** (needs 154% industry) | – | – |
| C: residential vs industry | yes | residential 24% of pair (EDGAR 13%) | 181 [171–192] |
| D: residential vs transport | yes | residential 57% of pair (EDGAR 33%) | 174 [167–182] |

- **The excess CO can't come from industry replacing transport.** It needs more high-CO (residential/biomass-type) combustion than EDGAR assumes.
- **CO-constrained CO₂:NOx = 181 (95% range 167–197)**, against EDGAR's 172 and an unconstrained sector span of 115–393.

**Revised CO₂ estimate and uncertainty budget (proposed D12):**

| | EDGAR ratio (§4.6) | **CO-constrained ratio** |
|---|---|---|
| CO₂:NOx | 172 | **181** (167–197) |
| City fossil CO₂ (midday rate) | 2.83 Mt/yr | **2.98 Mt/yr** (1σ 2.28–3.69) |
| Total uncertainty (1σ) | 31.9% | **23.6%** |

In the revised budget, the base paper's 25% "ratio representativeness" term becomes **8.1%** (half-range of the feasible scenarios) **+ 10%** (assumed, for EDGAR's per-sector ratios). The other terms are unchanged (bootstrap 3.3%, wind level 6.4%, wind regime 11.4%, EMG bias 12%, NOx/NO₂ 7.6%, EDGAR year/choice 3.1%). **Adding TROPOMI CO cuts the dominant error term by about two thirds.** This is the clearest answer yet to the primary research question.

**Caveats:**
- The mixing model trusts EDGAR's per-sector CO:NOx and CO₂:NOx ratios, and re-splits only one pair at a time.
- Secondary CO from VOC oxidation in the plume, and the EMG's +12% NOx bias, would both make the true CO:NOx *higher*, pushing toward more residential share and a higher CO₂:NOx.
- EDGAR gives Indian road transport a low CO:NOx (1.95); whether that's realistic is itself an inventory assumption.
- Residential CO₂ here is fossil only (EDGAR's framing); biomass CO₂ is biogenic and excluded.

### 4.9 Seasonal emissions and the COVID-19 lockdown check

**Seasonal EMG fits** (`src/ecotrack/inversion/run_seasonal.py`; same settings as §4.3, 100-member bootstrap):

| Season | Windy overpasses | E(NOx) kg/s [95% CI] | τ (h) | R² | Corridor share |
|---|---|---|---|---|---|
| 2019–20 | 161 | **0.405** [0.345–0.465] | 1.89 | 0.997 | 21.6% |
| 2020–21 | 135 | 0.538 [0.459–0.638] | 1.51 | 0.982 | 19.7% |
| 2021–22 | 165 | 0.568 [0.513–0.653] | 1.36 | 0.994 | 22.8% |
| 2022–23 | 158 | 0.502 [0.453–0.574] | 2.17 | 0.968 | 19.9% |
| 2023–24 | 162 | **0.621** [0.538–0.682] | 1.62 | 0.995 | 21.8% |

- **Seasons are resolvable:** the between-season SD (0.081 kg/s) is **2.3×** the typical within-season 1σ (0.036).
- **The corridor share is stable** (19.7–22.8%).
- These support *seasonal* Phase 3 labels (D16). Monthly fits are too noisy.

**COVID-19 lockdown, a model-free check.** City NO₂ excess (mean within 10 km of the source minus a 35–45 km rural ring), 25 March – 31 May of each year:

| Year | City (µmol/m²) | Rural ring | **Excess** | vs 2022–24 mean |
|---|---|---|---|---|
| **2020 (national lockdown from 25 Mar)** | 37.1 | 29.3 | **7.8** | **−74%** |
| **2021 (Maharashtra second-wave restrictions)** | 53.0 | 31.5 | **21.5** | **−29%** |
| 2022 | 60.8 | 33.5 | 27.3 | – |
| 2023 | 61.6 | 32.2 | 29.3 | – |
| 2024 | 69.5 | 35.2 | 34.3 | – |

- **The satellite data capture both COVID periods, in the right order of severity**, plus growth over 2022–2024. That's independent evidence that the pipeline responds to real changes in emissions.
- Caveats:
  - this is the column *excess*, not an emission rate;
  - spring meteorology varies between years (same-calendar windows limit this);
  - the EMG fit for the 2020 lockdown window alone is degenerate (R² 0.62, τ 8.8 h) because the plume is too weak, so its −84% is not used.

![Seasonal city NOx](../outputs/phase1/figures/seasonal.png)

### 4.10 A CO flux-divergence map: an NO₂-independent emission map (D16 feasibility)

**Why:** Phase 3 labels built from the NO₂ map are circular with the NO₂ feature (D16). A map built from **CO** would be independent of NO₂.

**Method** (`src/ecotrack/inversion/run_co_divergence.py`): CO is inert, so E_CO = ∇·(V′·w), with no sink term. V′ is the CO column after:
- terrain normalisation (as in §4.8);
- removing each day's box median;
- **removing each pixel's long-term mean**.

**Why the static removal is essential:** Pune's winds are directional (mean wind ~1 m/s of a 3.4 m/s mean speed), so a fixed terrain imprint × the mean wind fakes a divergence. Synthetic test with **Pune's real wind record**:

| Synthetic, real winds | 25 km total (true 100 mol/s) | Terrain only (true 0) |
|---|---|---|
| raw CO flux divergence | 26.6 ✗ | **−70** ✗ |
| static pattern removed | **88.4** (−12%) | **−2.5** ✓ |

(With isotropic random winds both variants work: 97.7 and ≈ 0. That's why a test with the *real* wind distribution matters.)

**Real data (748 overpasses):**

| Check | Result |
|---|---|
| Total within 25 km | **248 mol/s (6.94 kg/s)**, bootstrap 95% 217–280 |
| vs the CO step method (§4.8) | 240 mol/s → **ratio 1.03**: two independent CO methods agree |
| Levels off with radius? | 207 / 248 / 262 / 272 at 20/25/30/35 km: **yes** (unlike NO₂, which has a sink term) |
| Cell-level agreement with the NO₂ map (5 km smoothing, ≤ 25 km) | **r = 0.75** |
| Corridor share | **CO 14.5%** [10.9–18.7] vs **NO₂ 21.1%** |
| Main CO peak | 18.455 N, 73.835 E (central/south Pune); edge peaks at the box boundary are artefacts |

![CO flux-divergence map](../outputs/phase1/figures/co_divergence_map.png)

**Interpretation:**
1. **L-co is feasible as a second, NO₂-independent label**, at ~5 km scale. It's noisier than NO₂: the corridor-share CI is about ±27% relative, vs ±2.4% for NO₂.
2. **A first hint of source separation (exploratory):** the corridor holds a smaller share of the city's CO (14.5%) than of its NOx (21.1%), so its CO:NOx is lower: ≈ 0.69 × 21.2 ≈ **15 mol/mol**, vs the city's 21.2. The map shows why:
   - CO is concentrated in the dense **old city core** (residential/biomass combustion: high CO:NOx);
   - the **Pimpri-Chinchwad industrial belt** is a strong NO₂ hotspot but only a moderate CO one (industry: low CO:NOx).

   This is the industrial-vs-residential separation the proposal aimed for, seen in independent satellite data. It is **not yet validated** (one estimator, a −12% synthetic bias, wide CI).

### 4.11 From the midday October–May rate to an annual mean (D17)

**Why:** TROPOMI sees Pune only at ~11:30–13:30 IST (overpasses: 34% in the 12:00 hour, 57% in 13:00, 9% in 14:00), and we use October–May only. Daytime traffic and seasonal patterns make this window unrepresentative of the annual mean.

**Method** (`src/ecotrack/inversion/temporal_adjust.py`): E_annual = E_observed / F, with F = Σ_s w_s · f_hour · f_week · f_month.
- **w_s:** EDGAR 2021 NOx share of each sector within 25 km.
- **The f factors:** from **EDGAR temporal profiles** (Crippa et al., 2020): hourly per month and day type, weekly, and monthly. Weighted by *our actual* overpass-hour, weekday and month distribution.
- **Monthly profiles matched on IPCC codes:** India-specific for residential (1A4); EDGAR world region 7 otherwise.
- *Bug fixed on the way:* a first version matched sector *names*, silently fell back to flat for most sectors, and matched agricultural soils to "rice cultivation".

| Sector | NOx share | Overpass-hour factor | Oct–May factor | Combined |
|---|---|---|---|---|
| Industry (1A2) | 64.3% | 1.08 | 1.00 | 1.08 |
| **Road transport (1A3b)** | 19.8% | **1.59** | 1.00 | **1.60** |
| Residential (1A4, India) | 9.9% | 1.05 | 1.33 | 1.39 |
| Power (1A1a) | 2.8% | 1.13 | 0.97 | 1.09 |
| Others (soils, crop burning, rail/air, refineries) | 3.2% | 1.0–1.6 | ≈ 1 | – |
| **Overall F** | | | | **1.231** |

**Caveat:** EDGAR's India residential *monthly* profile is heating-shaped (January ≈ 17.5% of the year, July ≈ 2.9%), but Pune's household fuel use is mostly cooking. With a flat residential month profile, **F = 1.197**.

| | Midday Oct–May rate | **Annual mean (F = 1.20–1.23)** | EDGAR | ODIAC |
|---|---|---|---|---|
| NOx (kt/yr) | 16.5 | **13.4–13.8** | 21.1 | – |
| Fossil CO₂, CO-constrained ratio (Mt/yr) | 2.98 | **2.42–2.49** | 3.63 | 11.8 |
| Fossil CO₂, EDGAR ratio (Mt/yr) | 2.83 | 2.30–2.37 | | |

- **The satellite-vs-EDGAR NOx gap widens on a like-for-like basis: −36% (annual)**, not −22% (midday vs annual). EDGAR's own profiles say the overpass window runs ~23% above the annual mean.
- The profiles are generic (regional, not Pune-specific), so F carries roughly ±10% uncertainty (judgement; the flat-residential variant moves it 3%).
- **Both numbers are reported from now on:** the midday rate (what the satellite measures) and the annual-mean equivalent (for comparison with inventories).

### 4.12 Monte Carlo uncertainty (D18)

**Why:** the root-sum-square budget (§4.8) assumes independent, symmetric Gaussian errors. A Monte Carlo (200,000 draws, `src/ecotrack/inversion/mc_budget.py`):
- multiplies every factor through the chain (bootstrap E_NOx, wind level, wind regime, method bias, NOx/NO₂, CO-constrained CO₂:NOx, per-sector ratio, EDGAR year, and for annual means the temporal factor F);
- uses lognormal (non-negative) errors;
- gives asymmetric ranges.

The +11–12% EMG synthetic bias is a *known* overestimate, so it is handled two ways:
- **symmetric:** ±12% uncertainty, no correction (as in the RSS budget);
- **bias-corrected:** ÷ (1 + b), b ~ N(0.115, 0.03).

| Fossil CO₂, Pune + PCMC ≤ 25 km (Mt/yr) | Median | 68% | 95% |
|---|---|---|---|
| Midday Oct–May rate, symmetric | **2.98** | 2.40–3.69 (−19 / +24%) | 1.94–4.54 |
| **Annual mean, symmetric** | **2.45** | 1.93–3.10 | **1.54–3.90** |
| Annual mean, bias-corrected | 2.20 | 1.78–2.71 | 1.46–3.31 |

| NOx (kt/yr) | Median | 95% |
|---|---|---|
| Midday, symmetric | 16.5 | 11.3–23.7 |
| Annual, symmetric | 13.5 | 9.0–20.4 |

- **The medians reproduce the earlier point estimates** (2.98 midday; 2.45 annual), so the RSS shortcut was fine for the centre. The Monte Carlo adds honest, asymmetric ranges.
- **ODIAC (11.8 Mt/yr) lies far outside the 95% range** in every variant (3× the upper bound). Together with the tentative OCO hint (§4.7), **ODIAC's value for Pune is inconsistent with the satellite evidence.**
- **EDGAR (3.63 Mt/yr)** is just inside the symmetric annual 95% range, and outside it once the method bias is corrected.
- **Reporting choice (D18):** the headline uses the symmetric treatment (conservative); the bias-corrected values are shown as a sensitivity.

![Monte Carlo uncertainty](../outputs/phase1/figures/mc_budget.png)

### 4.13 What Phase 1 has *not* yet produced

**Items against the proposal's own Phase 1 definition** (checked 2026-09-24):
- ✅ **IQR outlier removal** of TROPOMI NO₂ (proposal step 1): done (D13). Per-pixel time series, Tukey k = 3; removes 0.09% of pixels; every result moved < 2%.
- ✅ **Differential Evolution settings sensitivity test** (proposal step 4): done. 36 combinations, identical optimum (spread < 0.001%).
- ✅ **Phase 1 report** (proposal deliverable): [phase1_report.md](phase1_report.md). `findings.md` remains the complete running results record.
- Per-sub-zone line-density plots were replaced by cluster-scale flux divergence (D1, D10). This is a documented deviation, not an omission.

**Other gaps:**

- No *direct* observational test of the CO₂:NOx ratio (OCO couldn't provide one, §4.7). TROPOMI CO constrains it indirectly through EDGAR's sector ratios (§4.8).

---

## 4b. Phase 2 — multi-source feature table (**complete: v2 frozen**, 2026-10-04)

**Goal (proposal Phase 2):** every data layer on one 1 km grid → a frozen table with one row per cell per month.

**Grid (D15):** 1 km UTM 43N squares kept if ≥ 50% inside the corridor → **268 cells** (C1 91 · C2 63 · C3 114), 268 km² vs a 269 km² corridor (`src/ecotrack/grid.py`).

**Layers:**

| Feature | Source | Time step | Status |
|---|---|---|---|
| `no2` | TROPOMI NO₂ cube (IQR-filtered), bilinear at the cell centre | monthly | ✅ |
| `co_norm` | TROPOMI CO cube ÷ relative air mass (terrain-normalised) | monthly | ✅ |
| `hcho` | TROPOMI HCHO, chemistry/VOC proxy (D14) | monthly | ✅ |
| `ws850`, `wd850`, `blh_m`, `frac_ese` | ERA5 at overpass (uniform over the corridor: one 0.25° cell) | monthly | ✅ |
| `t2m_k`, `ssrd_j_m2` | ERA5 at 07 UTC, photochemistry drivers (D14) | monthly | ✅ |
| `viirs_rad` | VIIRS DNB monthly radiance (stray-light corrected) | monthly | ✅ |
| `ndvi`, `ndbi` | Sentinel-2 SR median, SCL-masked (40–47 scenes per season) | seasonal | ✅ |
| `road_major/mid/minor/total_km` | **v2: OpenStreetMap** (Geofabrik extract `western-zone-261003.osm.pbf`, read locally); v1: GRIP4 fallback (D20) | static | ✅ v2 (OSM; GRIP4 kept as `grip_*`) |
| `industrial_frac` | **v2, new:** share of the cell under OSM `landuse=industrial` (MIDC estates), the proposal's "industrial-land fraction" | static | ✅ v2 |
| `ref_edgar_*`, `ref_odiac_*` | Inventories: **reference only, never features** (§5 rule, D2) | annual / monthly | ✅ |
| OCO-3 XCO₂ | – | – | not a feature (too sparse, D11) |

**Feature table v1** (`data/processed/feature_table_v1.csv`, road source in `feature_table_v1.meta.json`): **10,720 rows = 268 cells × 40 months, all 16 features, 0 missing values.**

- **Roads:** the OpenStreetMap servers, mirrors and Geofabrik were overloaded for hours (504/429), with only 16 of 35 road tiles downloaded. So v1 uses **GRIP4** (Global Roads Inventory Project; GEE community catalogue). Per cell: total median 2.6 km (max 20.7); 145 of 268 cells contain a major road.
- **Caveat:** GRIP4's local-road coverage is sparse and older (source years ~2014): `road_minor_km` median 0.07 km/cell. When OSM completes, **v2** will use OSM, with GRIP4 kept as `grip_*` cross-check columns.

| Feature | 1st percentile | median | 99th percentile |
|---|---|---|---|
| NO₂ (mol/m²) | 2.8e-5 | 5.8e-5 | 9.5e-5 |
| CO_norm (mol/m²) | 0.034 | 0.043 | 0.051 |
| HCHO (mol/m²) | 1.3e-4 | 2.4e-4 | 3.2e-4 |
| VIIRS (nW/cm²/sr) | 3.0 | 17.9 | 47.1 |
| NDVI / NDBI | 0.16 / −0.08 | 0.29 / 0.03 | 0.49 / 0.15 |
| t2m (°C) / solar (MJ/m²/h) | 23.4 / 2.2 | 28.1 / 2.9 | 35.1 / 3.5 |

- NO₂ is highest in C1 and lowest in C3, consistent with Phase 1.
- VIIRS rises from a median of 15.6 (2019) to 23.6 (2024).
- CO_norm is bimodal (seasonal).
- EDGAR is blocky: ~16 distinct values over 268 cells, a visible illustration of inventory coarseness.

![Feature histograms (QA)](../outputs/phase2/qa_histograms.png)

### Feature table v2 (final Phase 2 deliverable, 2026-10-04)

`data/processed/feature_table_v2.csv`: **10,720 rows, 17 features, 0 missing**. The meta file records the OSM extract and the CSV's **SHA-256** (`de0200d6…`). A rebuild gave the identical hash, so the table is deterministic. v1 is kept unchanged.

**How OSM was finally obtained.** Overpass was still failing (504; 16 of 35 tiles after days). Geofabrik was back, so the whole **India western-zone extract** (221 MB, MD5 checked) was downloaded and read locally with `pyosmium` (`src/ecotrack/acquire/osm_pbf.py`, 2.5 minutes, no server needed). It gave **36,082 road ways** and **223 industrial areas** in the box.

**OSM vs GRIP4 roads (per cell, 268 cells):**

| Class | OSM median (km) | GRIP4 median (km) | Spearman |
|---|---|---|---|
| major | 0.79 | 0.25 | 0.84 |
| mid | 1.08 | 0.88 | 0.70 |
| minor | **4.20** | **0.07** | 0.59 |
| total | 7.31 | 2.62 | 0.78 |

GRIP4 ranks major roads similarly (0.84) but misses almost all local streets: OSM has ~60× more minor road. This confirms the v1 caveat. 170 of 268 cells contain a major road (GRIP4: 145).

**Industrial land.** The corridor mean is 5.3%; 19 cells are > 25% industrial. The top cells are exactly the known estates: MIDC Bhosari (18.65 N, 73.82 E; 97%), the Chinchwad/Akurdi belt (18.66 N, 73.79 E) and Talegaon MIDC (18.79 N, 73.69 E). By cluster: C2 PCMC 10.4%, C1 4.6%, C3 3.1%. Its correlation with every other feature is ≤ 0.4 (VIIRS), so **it adds information no other feature carries**.

**Correlation QA** (Spearman, `outputs/phase2/qa_correlation_v2.png`). Pairs with |r| ≥ 0.8:
- road_minor–road_total 0.93 (total is mostly minor roads);
- blh–ssrd 0.90 and t2m–ssrd 0.80 (all driven by season);
- wd850–frac_ese −0.84 (two descriptions of the same wind).

These are expected and matter for **interpreting** the ML ablation (correlated features share importance), not for dropping columns now.

**Where does each feature vary: between cells or between months?** This is the share of variance that is spatial:

| Feature | Spatial share | What it means |
|---|---|---|
| roads, industrial_frac | 1.00 | static by construction |
| NDVI, NDBI | 0.97 | mostly spatial (land cover) |
| VIIRS | 0.89 | mostly spatial, with a growth trend |
| **NO₂** | **0.34** | two-thirds temporal (season, weather) |
| **CO, HCHO** | **0.02** | almost purely temporal at 1 km |
| ERA5 weather | 0.00 | one ERA5 cell covers the corridor |

**Consequence for Phases 4–6:** at 1 km, the *where* comes almost entirely from the activity layers (VIIRS, NDBI, roads, industry) and partly from NO₂. CO, HCHO and weather tell the model *when*, not *where*. Experiment B (+CO) can therefore only improve the temporal skill of the labels, and spatial-block cross-validation is essential so the model can't memorise static cell properties. This is recorded here before any model is trained, so it can't be read as a post-hoc excuse.

![Feature correlations (v2)](../outputs/phase2/qa_correlation_v2.png)

**NDBI caveat (found while writing the Phase 2 report).** NDBI is highest in the *rural* C3 cluster (0.05 vs 0.00 in C1) and correlates **negatively** with NO₂ (−0.28) and night lights (−0.33). In the dry season, bare soil and dry fields reflect short-wave infrared like concrete, a known NDBI weakness. So NDBI is not a reliable built-up indicator here. Roads, industrial land and VIIRS are the dependable activity layers, and Experiment D's NDBI importance must be read with this caveat.

Full write-up: [phase2_report.md](phase2_report.md).

**Bugs fixed on the way (details in the research log):**
1. Earth Engine names a single-band reduction `mean` → VIIRS/HCHO were blank → outputs now named explicitly.
2. ERA5 reduced at 27.8 km left 7,560 cells empty → sampled at 1 km.
3. Overpass refused large tiles → 0.05° tiles, cached and rotating across mirrors.
4. A Windows console encoding crash.

---

## 5. Design decisions so far

| # | Decision | Driven by |
|---|---|---|
| D1 | Invert NO₂ over 3 clusters, not 10 waypoints | Waypoints closer together than one TROPOMI pixel |
| D2 | Layers used to build CO₂ labels are excluded from model features | Avoids a circular "Experiment D always wins" result |
| D3 | OCO-3 as an independent observed target | Later narrowed by D8 |
| D4 | Add TROPOMI CO as a source-type tracer | No ground truth separating traffic from industry |
| D5 | Tree models + spatial-block CV + bootstrap CIs; drop the U-Net | ~270 cells × 40 months is too little for deep learning |
| D6 | ERA5 hourly as the primary meteorology | Resolution; overpass-time matching |
| D7 | October 2019 – May 2024, October–May only | TROPOMI pixel change (Aug 2019); monsoon cloud |
| D8 *(proposed)* | OCO-3 (7 dates) + OCO-2 (1 date) as a city-scale mass-balance check on NO₂-derived CO₂ | G1: too sparse for ML, but direct CO₂ |
| D9 | Corridor = highway centreline ± 3.5 km + Talegaon MIDC | G4: waypoint errors up to 4.4 km; MIDC outside |
| D10 | City total from EMG; spatial split from flux-divergence shares | Phase 1: FD totals sensitive, FD shares robust |
| D11 *(proposed)* | OCO gives consistency + an upper limit + a detection threshold, not an independent estimate | D8 run: no detection (plume ≪ noise and swath artefacts) |
| D12 *(proposed)* | CO₂:NOx from the TROPOMI-CO-constrained sector mix (181, 167–197); headline 2.98 Mt/yr ± 24% | D4 run: CO:NOx 21.2 vs EDGAR 16.0 |
| D13 | IQR outlier removal = per-pixel time series, k = 3 | "local" removed 29% of real pixels (L3 oversampling); "domain" clips the plume |
| D14 | Chemistry proxy = TROPOMI HCHO + ERA5 temperature/radiation (not MERRA-2/CAMS O₃) | TROPOMI O₃ is a stratosphere-dominated total column; reanalysis chemistry too coarse |
| D15 | 1 km UTM grid, cells ≥ 50% inside the corridor → 268 cells | True 1 km² cells; matches the corridor area |
| D16 *(proposed)* | Phase 3: seasonal FD labels + NO₂-independent CO-label test + circularity-aware evaluation | FD labels derive from NO₂ (a feature); seasons resolvable |
| D17 | Report the annual-mean equivalent (÷ F = 1.20–1.23, EDGAR temporal profiles) alongside the midday rate | The satellite samples a busy window; inventories are annual |
| D18 | Monte Carlo uncertainty (200k draws, lognormal); headline symmetric, bias-corrected as sensitivity | Asymmetric ranges; known EMG bias handled explicitly |
| D19 | EMG fit window ≤ 45 km + sloped background; unconstrained-fit fallback; structure term in the budget | The 60 km window included a second source → NOx biased ~20% low |
| D20 | Roads: GRIP4 fallback for feature table v1; OSM for v2 (done 2026-10-04 via a Geofabrik extract) | OSM servers overloaded for hours |

Full reasoning for each is in [decisions.md](decisions.md).

---

## 6. Processing notes (for the Methods chapter)

- **GES DISC access:** the account needs the "NASA GESDISC DATA ARCHIVE" application approved; "GESDISC Test Data Archive" is a different (test) server.
- **OCO-2 versions:** the newest version (11.3r) covers only 2024, so the scan takes the newest version available **per day** (11.2r for 2019–2023). Selecting a single version silently dropped four of the five seasons in the first attempt.
- **OCO-3 operation mode** codes used here: 0 nadir, 1 glint, 2 target, 3 transition, 4 Snapshot Area Map. *To confirm against the Lite file's attribute documentation before publication.*
- **Network outage:** 159 OCO-2 days failed during a DNS outage and were re-scanned successfully. A restarted OCO-3 run logged 41 days twice; the summaries count distinct days.
- **TROPOMI cube:** 1,004 usable overpasses, reprojected to one fixed 0.01° grid (90 × 95 pixels, 73.35–74.30 E, 18.15–19.05 N); 89% of pixel-days valid. ERA5 matched to every overpass within 30 minutes.
- **GEE L3 oversampling:** GEE's 1 km TROPOMI L3 grid copies each ~3.5 × 5.5 km pixel into several cells. Any per-pixel spatial statistic (e.g. a local IQR filter) therefore sees footprint edges, not independent pixels; a local filter removed 29% of real pixels and was rejected (D13).
- **ERA5 resolution:** C2 and C3 fall in the same 0.25° cell, so the corridor effectively has one wind per overpass. Flux divergence uses this as a uniform wind over the box (a stated approximation).

---

## 7. Limitations and open issues

| Issue | Effect | Status / mitigation |
|---|---|---|
| EMG synthetic bias (+12% E, −16% τ) | City total likely slightly high | Measured; enters the uncertainty budget |
| Flux-divergence totals depend on lifetime and background | Absolute zone totals ±25% | Use shares (±2.5%), not absolute FD totals (D10) |
| Wind-level choice | 0.35–0.52 kg/s across 10 m / 100 m / 850 hPa | 850 hPa justified physically; reported as a sensitivity |
| Corridor zones are 1–2 TROPOMI pixels wide | Emission smears across zone edges | Hotspot circles as a cross-check |
| Uniform wind over the box in flux divergence | Local wind variations ignored | Stated approximation; ERA5 can't resolve finer |
| Central Pune (the largest source) lies outside the corridor | Corridor results include transported Pune NO₂ | Explicit Pune-core zone; regime split |
| Chakan industrial area outside the corridor to the NE | Possible upwind contamination on NE-wind days | To note; could be tested by wind direction |
| Midday, October–May only | "kt/yr" figures are not annual totals | Always labelled "midday rate" |
| Fixed NOx/NO₂ = 1.32 | Scales all NOx values | Literature value; ±0.1 in the budget (7.6%) |
| NOx → CO₂ ratio (EDGAR 172; sectors 115–393) | Was the largest error term (25%) | **Constrained by TROPOMI CO to 148–180 (D12, post-D19)**; still relies on EDGAR's per-sector ratios (assumed 10%) |
| Satellite NOx below EDGAR | Pre-D19 −36%; **post-D19 −17 to −19% (annual)** | The sloped-background test found the main cause (a second source in the fit window, D19); the remaining gap is within the uncertainty |
| EMG structure (background model, fit window) | ±5.4% on E | Budget term (D19); unconstrained small-subset fits fall back to a flat background |
| EDGAR and ODIAC disagree by 3.2× | Inventory "plausibility" range is very wide | Report both; don't treat either as truth. **ODIAC is outside the satellite 95% range (D18)** |
| Midday October–May rate vs annual inventories | Not like-for-like | **Done (D17):** F = 1.20–1.23 from EDGAR temporal profiles → annual NOx 13.4–13.8 kt, CO₂ 2.42–2.49 Mt; profiles generic (~±10%) |
| OCO-3/OCO-2 can't detect the Pune plume | No *direct* test of the CO₂:NOx ratio | Upper limit only (D11); ratio constrained indirectly via TROPOMI CO (D12) |
| TROPOMI CO terrain imprint (~6%) larger than Pune's signal | Could fake or hide the CO step | Air-mass normalisation + static-pattern removal; synthetic test −1.4% / ≈0 with terrain only |
| Secondary CO (VOC oxidation) and EDGAR's per-sector ratios | CO:NOx → CO₂:NOx mapping | Both push toward a higher ratio; 10% term assumed |
| D8 not yet approved | Changes Experiment B's meaning | **Awaiting guide review** |
| OSM is a 2026 snapshot used for 2019–2024 | Roads/industry built after 2019 counted for all years | Stated assumption; static layers vary little at 1 km over 5 years |
| CO, HCHO and weather barely vary between 1 km cells (spatial share ≤ 2%) | They can't help the model locate emissions, only time them | Documented before modelling (§4b); spatial CV in Phases 4–6 |
| NDBI confused by dry bare soil | "Built-up" highest in rural C3; negative correlation with NO₂/VIIRS | Caveat for Experiment D; roads/industry/VIIRS are the reliable activity layers |

---

## 8. Next steps

1. **Send the progress report PDF, the Phase 1 report and the Phase 3 design note to the guide; get sign-off on D8/D11/D12/D16/D19.** Headline (post-D19): 2.79 Mt fossil CO₂/yr annual mean [95%: 1.79–4.36].
2. ~~Finish Phase 2~~ **Done (2026-10-04):** feature table v2 (OSM roads + industrial land, GRIP4 cross-check, correlation QA, SHA-256).
3. **Phase 3 (labels)** per the guide's answer on D16; then Phase 4 (feature tensor: standardise, spatial-block folds).
4. **Optional:** per-swath offsets in the OCO regression; a wider across-wind window for the CO step. (The sloped EMG background was done as D19.)

---

## 9. How to reproduce

```powershell
.venv\Scripts\activate
# Feasibility
python -m ecotrack.feasibility.g4_verify_waypoints ; python -m ecotrack.feasibility.g4_map
python -m ecotrack.feasibility.g2_tropomi_coverage
python -m ecotrack.feasibility.g3_no2_signal
python -m ecotrack.feasibility.g1_oco_soundings --product oco3   # likewise --product oco2
python -m ecotrack.acquire.era5_overpass
# Phase 1
python -m ecotrack.acquire.tropomi_cube
python -m ecotrack.inversion.run_city
python -m ecotrack.inversion.run_divergence
python -m ecotrack.acquire.edgar ; python -m ecotrack.acquire.odiac
python -m ecotrack.inversion.run_co2
python -m ecotrack.inversion.run_oco_check ; python -m ecotrack.inversion.run_oco_check --prior-radius 10 --tag _r10
python -m ecotrack.acquire.tropomi_cube --product co ; python -m ecotrack.acquire.dem
python -m ecotrack.inversion.run_co_ratio
python -m ecotrack.inversion.de_sensitivity
python -m ecotrack.inversion.run_seasonal ; python -m ecotrack.inversion.run_co_divergence ; python -m ecotrack.inversion.temporal_adjust
python -m ecotrack.inversion.mc_budget
# Phase 2
python -m ecotrack.grid ; python -m ecotrack.acquire.grid_layers_gee
python -m ecotrack.acquire.roads_grip                       # GRIP4 roads (cross-check columns)
# download data/raw/osm/western-zone-<date>.osm.pbf from Geofabrik (check its .md5), then:
python -m ecotrack.acquire.osm_pbf                          # OSM roads + industrial land (v2)
python -m ecotrack.features                                 # feature table v2
# Illustrated progress report (docs/EcoTrack_Progress_Report.pdf)
python -m ecotrack.progress_report
# Method tests
python -m pytest
```

| Output | File |
|---|---|
| Feasibility summaries | `outputs/feasibility/g1_*_summary.json`, `g2_tropomi_summary.json`, `g3_no2_signal.json`, `g4_waypoints.json` |
| First-corridor results (before D9) | `outputs/feasibility/v1_waypoint_corridor/` |
| EMG results | `outputs/phase1/city_fit.json` |
| Flux-divergence results and map | `outputs/phase1/divergence_totals.json`, `divergence_map.npz` |
| CO₂ conversion, inventory comparison, uncertainty budget | `outputs/phase1/co2_summary.json` |
| OCO check (D8) | `outputs/phase1/oco_check.json`, `oco_check_r10.json` |
| TROPOMI CO ratio, sector scenarios, revised budget (D4/D12) | `outputs/phase1/co_ratio.json` |
| DE settings sensitivity (36 fits) | `outputs/phase1/de_sensitivity.json` |
| Seasonal fits; CO flux-divergence map; annual-mean adjustment; Monte Carlo budget | `outputs/phase1/seasonal.json`, `co_divergence.json`, `temporal_adjust.json`, `mc_budget.json` |
| Phase 1 results before IQR filtering (for comparison) | `outputs/phase1/v1_before_iqr/` |
| Figures | `outputs/phase1/figures/` |
| Feasibility memo for the guide | [feasibility_memo.md](feasibility_memo.md) |
