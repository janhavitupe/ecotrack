# Chapter 8 — Replicate It Yourself

Three levels. Do them in order.
- **Level 1:** re-run the whole pipeline and check you get the same numbers.
- **Level 2:** redo the key calculations by hand, so you know where every number comes from.
- **Level 3:** rewrite the core pieces yourself. Once you can do this, you truly own the project.

---

## Level 1 — Re-run everything (≈ one day, mostly waiting)

Tick each box and compare with the **expected** value. Small differences (< 1%) are fine.
Anything bigger means something is wrong; see the troubleshooting table at the end.

### A. Setup
- [ ] Free at least 5 GB on C: (the login files live there).
- [ ] Clone or copy the repo to `D:\EcoTrack`.
- [ ] `python -m venv .venv` → `.venv\Scripts\Activate.ps1` → `pip install -r requirements.txt` → `pip install -e .`
- [ ] `earthengine authenticate` → then `python -c "import ee; ee.Initialize(project='ecotrack-509517'); print(ee.Number(1).getInfo())"` → **prints 1**.
- [ ] Earthdata login saved:
      `python -c "import earthaccess; earthaccess.login(strategy='interactive', persist=True)"`.
      Also confirm "NASA GESDISC DATA ARCHIVE" is approved in your profile.
- [ ] `python -m pytest` → **11 passed**.

### B. Geometry
- [ ] `python -m ecotrack.geometry` → expect **"Corridor area: 269 km²"**; it writes `data/interim/corridor.geojson`.
- [ ] `python -m ecotrack.feasibility.g4_verify_waypoints` → expect every waypoint within ~0 m
      (the config now holds the OSM positions).
- [ ] `python -m ecotrack.feasibility.g4_map` → open `outputs/feasibility/g4_map.html` and look:
      the corridor follows the highway; the purple Bhosari and Talegaon MIDC areas are inside.

### C. Feasibility
- [ ] `python -m ecotrack.feasibility.g2_tropomi_coverage` → expect **median 26 usable days/month, min 13**.
- [ ] `python -m ecotrack.feasibility.g3_no2_signal` → expect C1 ≈ 2.2–2.4×, C2 ≈ 2.1–2.3×, C3 ≈ 1.7–1.8×.
- [ ] `python -m ecotrack.feasibility.g1_oco_soundings --product oco3` (hours; rerun if interrupted),
      then `--product oco2` → expect 7 strong OCO-3 days (`bbox_days_with_>=50_good`) and 1 OCO-2
      day (2024-01-23).
- [ ] `python -m ecotrack.acquire.era5_overpass` → expect ~1,031 overpasses and a median 850 hPa wind of ~3.5 m/s.

### D. Phase 1 data
- [ ] `python -m ecotrack.acquire.tropomi_cube` → 40 monthly files, **1,004 overpasses**.
- [ ] `python -m ecotrack.acquire.tropomi_cube --product co` → **907 overpasses**.
- [ ] `python -m ecotrack.acquire.dem` → elevation **14–1180 m**.
- [ ] `python -m ecotrack.acquire.edgar` → e.g. "NOx 2021 TOTALS box total 43,216 Tonnes".
- [ ] `python -m ecotrack.acquire.odiac` → 35 months, ~400,000–500,000 t C per month.

### E. Phase 1 analysis (run in this order: each step uses the previous one's output; numbers after D19)
- [ ] `python -m ecotrack.inversion.run_city` → **"IQR ... removed 0.09%"**, source **18.485 N, 73.855 E**,
      **MAIN: E(NOx) = 0.663 kg/s, tau = 1.09 h, R² = 0.998**, and a "[Westerly regime] sloped fit unconstrained → flat
      background fallback" message (expected: the D19 quality rule at work). Structure lines: flat 45 km 0.591, sloped 30 km 0.651, original flat 60 km 0.522.
- [ ] `python -m ecotrack.inversion.run_divergence` → 25 km: **0.787**; corridor **0.165** kg/s (share 21.0%).
- [ ] `python -m ecotrack.inversion.run_co2` → **SATELLITE fossil CO₂: 3.60 Mt/yr, ± 31%** (EDGAR ratio); EDGAR 3.63; ODIAC 11.78.
- [ ] `python -m ecotrack.inversion.run_oco_check` and `... --prior-radius 10 --tag _r10` →
      **beta = 1.57 ± 1.44** and **0.81 ± 0.74**.
- [ ] `python -m ecotrack.inversion.run_co_ratio` → **CO:NOx = 16.68**, CO₂:NOx 163, **city CO₂ 3.40 Mt/yr** (midday), uncertainty **23.0%**.
- [ ] `python -m ecotrack.inversion.run_seasonal` → five seasons 0.434 / 0.602 / 0.733 / 0.666 / 0.663, ratio 2.8 (2023–24 uses the flat fallback).
- [ ] `python -m ecotrack.inversion.run_co_divergence` → 25 km 248 mol/s vs CO step 240 (ratio 1.03); corridor share 14.5%.
- [ ] `python -m ecotrack.inversion.temporal_adjust` → F = 1.231 (flat residential 1.197); annual CO₂ 2.76–2.84 Mt/yr.
- [ ] `python -m ecotrack.inversion.mc_budget` → annual CO₂ (symmetric) median **2.79**, 95% **1.79–4.36**.
- [ ] `python -m ecotrack.inversion.de_sensitivity` → all converged fits give **0.6627 kg/s**; CR = 0.3 runs may not converge with the 6-parameter model (expected).
- [ ] Open every figure in `outputs/phase1/figures/` and check it looks like the ones in the report.

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `EEException ... project` | Earth Engine not initialised / wrong project | `earthengine authenticate`; check `accounts.gee_project` |
| OCO: `403 Forbidden` / `access_denied` | GES DISC app not approved | Approve "NASA GESDISC DATA ARCHIVE" (not "Test") |
| OCO: `getaddrinfo failed` / timeouts | Internet dropped | Rerun; it resumes |
| `No space left on device` | C: full | Free space; set TMP/PIP_CACHE_DIR to D: |
| `FileNotFoundError ... cube` | Ran analysis before download | Run `acquire.tropomi_cube` first |
| Overpass `504` | OSM server busy | Retry later |
| Numbers differ > 1% | Different data version / config edited | `git diff configs/study.yaml`; check the GEE collection dates |

---

## Level 2 — Redo the key numbers by hand

Open the JSON files in `outputs/phase1/` and check these with a calculator (current D19 values):
1. **Lifetime:** `city_fit.json` → results[0] → x0_km = 16.28, wind_ms = 4.1446. τ = 16,277 / 4.1446 = ? s → ? h. (Expect ≈ 3,927 s = 1.09 h.)
2. **Emission:** burden_mol = 42,856. E(NO₂) = burden / τ(s) = ? mol/s. × 1.32 = E(NOx) mol/s. × 0.046 = kg/s. (Expect 0.663.)
3. **Per year:** 0.663 × 31,557,600 / 10⁶ = ? kt. (Expect 20.9, the midday rate.)
4. **CO₂:** 20.91 kt × 163 / 1000 = ? Mt. (Expect 3.40, midday.) Then ÷ F = 1.231 for the annual mean (expect ≈ 2.76).
5. **CO:NOx:** `co_ratio.json` → e_co_mol_s = 240.3. NOx mol/s = 0.663 / 0.046 = ? → ratio = ? (Expect 16.7.)
6. **Uncertainty:** √(3.6² + 0.8² + 8.8² + 12² + 7.6² + 3.1² + 5.4² + 9.9² + 10²) = ? (Expect 23.0%.)
7. **ODIAC:** a month of ~410,000 t C × 12 × 44/12 = ? Mt CO₂ for the whole box. (The 25 km circle is 11.8.)
8. **Plume signal:** 90 kg/s ÷ (4 m/s × 50,000 m) → kg/m² → ÷ 0.044 → mol/m² → ÷ 331,000 → × 10⁶ → ppm. (Expect ~0.03 ppm.)

If you can do all 8 without looking at chapter 6, you understand the pipeline.

---

## Level 3 — Rewrite the core yourself (exercises)

Create a scratch notebook, reuse `load_cube()` and `match_wind()` for the data, and write these
from scratch. Compare against our functions: they should agree.

1. **Rotation.** Write `rotate(dx, dy, u, v)` returning (along, across). Test it: with a wind blowing
   exactly toward the east (u = 1, v = 0), a point 5 km east must give along = +5, across = 0.
   A point 5 km north must give along = 0, across = +5.
2. **Line density.** Bin one day's rotated pixels into 2 km along-bins; average across; multiply by 40,000 m.
3. **EMG.** Code f(x) from its formula, check numerically that it integrates to 1 (`scipy.integrate.quad`), and fit it to our
   line density with `scipy.optimize.differential_evolution`. You should get x₀ ≈ 25 km.
4. **Synthetic test.** Make a fake plume (copy the idea of `tests/test_emg.py`) with E = 1 mol/s, τ = 2 h,
   and see what your pipeline recovers. Do you also get a positive bias?
5. **Flux divergence.** Compute the mean flux maps (V·u, V·v), then `np.gradient` → the divergence; add the sink;
   sum within 25 km. Expect ~0.57 kg/s.
6. **CO step.** Implement the four steps of §6.10 and get the step ≈ 65 mol/m.
7. **Stretch:** add a sloped background (B + c·x) to the EMG and see how E changes. That's one of our open items.
