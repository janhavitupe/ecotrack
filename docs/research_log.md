# EcoTrack — Research Log

One dated entry per working day: what was run, what came out, what broke, what was decided.
This log is the raw material for the Methods chapter.

---

## 2026-09-23
- Study period fixed: October 2019 – May 2024, October–May seasons only (D7).
- Reviewed the proposal and recorded design changes D1–D6 in `docs/decisions.md` (cluster-scale inversion, no overlap between label and feature layers, OCO-3 as independent target, TROPOMI CO, tree models instead of the U-Net, ERA5 hourly).
- Set up the repo: `configs/study.yaml`, the `src/ecotrack` package, feasibility scripts G1–G4.
- Next: run G4, then G2 and G1 (see `docs/week1_checklist.md`).
- Environment: `.venv` (Python 3.11). The C: drive was full, so pip was run with TMP and PIP_CACHE_DIR on D:.
- G4 first pass (Nominatim): 4 of 10 waypoints within 500 m; 6 flagged. Dehu Road is off by 4.4 km: the config point (18.7167, 73.7500) is probably Dehu town, while OSM's Dehu Road cantonment is at about 18.680, 73.734. Also flagged: Talegaon (2.1 km), Nigdi, Chinchwad, Pimpri, Kasarwadi (1.3–1.5 km). Check each on the map before editing `configs/study.yaml`. Corridor area at a 3.5 km buffer: 260 km².
- G2 test, January 2020: 25 of 31 days usable (≥50% of the 221 corridor pixels pass QC). GEE's L3 footprints are loose (439 images returned for one month), so G2 now counts distinct usable days, not images. Fixed an off-by-one where the exclusive end month was also processed. Full-period G2 run started.
- G1 first attempt: the Earthdata login is valid, but GES DISC returns 403 / `error=access_denied`, so the account isn't authorized for the GES DISC archive yet. The search found 195 in-season OCO-3 Lite v11r days for 2019-10 to 2020-05, with a gap from 2019-10-20 to 2019-11-26 (early-mission outage?). G1 now stops after 3 consecutive access errors.
- **G2 result (full period, 40 months): PASS.** Median 26 usable days per month, minimum 13 (October 2019 and October 2020; October is the weakest month, likely late-monsoon cloud). No month below 5. Decision: monthly composites are viable (to be recorded as D8 once G1/G3 are in).
- The GEE `COPERNICUS/S5P/OFFL/L3_NO2` product has **no `qa_value` band**; GEE pre-filters on qa during its HARP L3 conversion. Methods must say our QC is cloud_fraction ≤ 0.3 plus SZA ≤ 70° on top of GEE's built-in qa filter, not qa ≥ 0.7 applied by us. If Phase 1 needs pixel-level qa control, use the L2 swaths from Copernicus Data Space.

## 2026-09-24
- GES DISC access fixed: the account had approved "GESDISC Test Data Archive" (the test server) instead of "NASA GESDISC DATA ARCHIVE".
- **G1, OCO-3 season 2019–20 (195 distinct days scanned):** 72 good-quality soundings inside the corridor, on only **2 days**, both above the 20-sounding "usable" threshold:
  - 2019-10: 25 soundings in **mode 4 = Snapshot Area Map (SAM)**. OCO-3 did a dedicated SAM over the Pune area. Check whether Pune is a regular SAM target; if so, later seasons may add more.
  - 2020-04: 47 soundings in mode 0 = nadir.
  - Quality filtering removes most soundings (1237 near the corridor at any quality vs. 122 good in the bbox).
  - The per-cluster counts add up to more than the corridor total because the 5 km cluster circles overlap and extend past the corridor.
- The OCO-3 progress file had 41 duplicate lines from a restarted run; the summary now counts distinct days.
- Started in background: the full OCO-3 period, the full OCO-2 period, and G3.
- **G3 result (5 seasons): PASS.** NO₂ enhancement over regional background (10th percentile of the regional box):
  - C1 Shivajinagar–Kasarwadi: 2.23–2.38×
  - C2 PCMC: 2.09–2.25×
  - C3 Dehu–Talegaon: 1.67–1.76×
  - All seasons are ≥1.5×, and the ranking is the same every season. Background: 2.5–3.3e-5 mol/m².
  - Caveat: C1 > C2 is consistent with central-Pune spillover. C3's enhancement may partly be PCMC outflow carried downwind. The ratios show there is a signal, not that the clusters can be separated; Phase 1's wind-rotated line densities test whether they can. The 2021–22 composite map was exported to Drive/ecotrack_feasibility for visual inspection.
- OCO-2 G1 run restarted: it had picked only version 11.3r, which covers 2024 only. It now picks the newest version per day (11.2r for 2019–2023, 11.3r for 2024), giving 1,177 in-season days.
- **G1 OCO-3 result (full period, 893 distinct days, 0 failed downloads):**
  - Corridor-only: 236 good soundings over 10 days, of which 6 are usable (≥20). Nothing usable after November 2022.
  - City scale (bbox): **7 strong days with ≥50 good soundings**: 2019-10-14, 2020-12-20, 2020-12-24, 2021-01-01, 2022-01-27, 2022-11-21 (all SAM) and 2020-04-21 (nadir). The 2020-12-20/24 SAMs have more than 1,100 good soundings each in the padded box.
  - **Pune is an OCO-3 SAM target**: SAMs on at least 9 dates between 2019 and 2023. Several were lost to quality filtering (e.g. 2021-05: 427 soundings, 0 good; pre-monsoon cloud).
  - OCO-3 gap confirmed: only 15 in-season days of data after Oct 2023; nothing from Dec 2023 to May 2024.
  - Most good soundings fall outside the 7 km-wide corridor, so corridor-cell counting undersells OCO-3. It is a city-scale instrument here.
- Proposed D8 (see decisions.md), to discuss with the guide.
- Drafted `docs/feasibility_memo.md` (OCO-2 and G4 still pending).
- **ERA5 matched to all 1,028 usable TROPOMI overpasses** (`src/ecotrack/acquire/era5_overpass.py` → `data/interim/era5/overpass_met.csv`). Overpasses are at 06–08 UTC (11:30–13:30 IST); 50 days have two usable orbits.
  - C2 and C3 share one ERA5 0.25° cell, so in practice there is one wind per overpass for the corridor.
  - Median wind speed: 2.5 m/s at 10 m, 3.2 at 100 m, 3.5 at 850 hPa. Median boundary-layer height 1.66 km (10th–90th percentile 1.06–2.94 km).
  - 850 hPa speed classes: 192 calm (<2 m/s), 429 at 2–4, 334 at 4–7, 73 above 7. Enough calm cases for source location and 2–7 m/s cases for the rotation fit.
  - **Wind regimes:** Oct–Mar from E–SE (central Pune upwind of PCMC and C3; pollution carried along the corridor). Apr–May from W–NW (reversed). This supports the G3 caveat that C1 > C2 and C3's enhancement are partly inherited from upwind. It also means each cluster is seen from both sides, which helps separate them in Phase 1. Consider running the inversion separately for the two regimes.
- **G1 OCO-2 result (1,177 days: first pass, plus a retry of the 159 days lost to a network outage; 0 failures after the retry):** only **1 strong day**, 2024-01-23: a glint-mode track crossing C1 and C2, with 62 good soundings in the corridor and 93 in the bbox. It usefully falls in the 2023–24 season, when OCO-3 has no data. As expected, OCO-2's narrow track rarely crosses the corridor. D8's direct-CO₂ set becomes 7 OCO-3 dates + 1 OCO-2 transect = 8.
- G4 map tool: `python -m ecotrack.feasibility.g4_map` → `outputs/feasibility/g4_map.html`. It shows draggable waypoints, OSM positions, the corridor, the clusters and 259 OSM industrial-land polygons.
- **MIDC Bhosari is 100% inside the current 3.5 km corridor**, so no buffer change is needed for it. The Chakan industrial area is outside (off-corridor, to the NE); it is a possible upwind source on NE-wind days, to note in Limitations.
- **G4 done → D9.** The user accepted OSM place centres for all 10 waypoints via the map tool. Built the corridor from the highway-snapped centreline plus Talegaon MIDC (269 km², one polygon). Extended the bbox to 73.62–73.89 E, 18.50–18.82 N. Rerunning G1 summaries, G2, G3 and ERA5 on the new corridor.
- **Rerun on the D9 corridor (269 km², 230 TROPOMI pixels):**
  - G2: unchanged (median 26 usable days/month, min 13).
  - G3: C1 2.22–2.37×, C2 2.10–2.25×, C3 1.71–1.81× (C3 slightly up: it now includes Talegaon MIDC).
  - OCO-3: unchanged (6 corridor days, 7 bbox days).
  - OCO-2: 60 corridor soundings on 2024-01-23 (was 62).
  - ERA5: 1,031 overpasses.
  The map step first failed with an Overpass 504; regenerated on retry, now with the centreline drawn. Memo updated to final draft.
