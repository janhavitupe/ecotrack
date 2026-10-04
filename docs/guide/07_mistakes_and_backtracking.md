# Chapter 7 — Every Mistake, Detour and Fix

Real research is full of wrong turns. Knowing ours makes you (a) able to avoid them when you
replicate the project, and (b) able to answer "what went wrong and how did you handle it?", a
favourite viva question. They're in the order they happened. Each has: **what happened → how we
noticed → the fix → the lesson.**

---

## Setup and access

**1. The C: drive was full (47 MB free).**
- pip failed with "No space left on device".
- **Fix:** we pointed pip's temp and cache folders at D:.
- **Lesson:** check disk space first; keep projects on the big drive.

**2. The original draft scripts assumed a `qa_value` band.**
- The GEE TROPOMI L3 product has no such band; the first script would have crashed. We found this
  by listing the band names.
- **Fix:** QC now uses cloud fraction + solar zenith + GEE's own pre-filter, and says so in the Methods.
- **Lesson:** list a dataset's actual contents before writing code against it.

**3. The draft OCO check "counted granules".**
- The week-1 plan counted how many OCO files a bounding-box search returned. But every file is
  **global**, so the search returns almost every day whatever the coverage.
- **Fix:** open each file and count the soundings that actually fall near Pune (G1).
- **Lesson:** understand what one "file" or "granule" covers.

**4. The Earthdata password was pasted into chat.**
- **Fix:** we used the saved `_netrc` login instead, and advised changing the password.
- **Lesson:** never paste credentials anywhere.

**5. "403 Forbidden" from NASA.**
- The login worked, but downloads were refused. A test download showed `error=access_denied`.
  Your screenshot showed "GESDISC **Test** Data Archive" approved, a different application.
- **Fix:** approve "NASA GESDISC DATA ARCHIVE".
- **Lesson:** a 403 after a successful login means authorisation, not a wrong password.

## Feasibility (G1–G4)

**6. G2 counted images, not days, and had an off-by-one.**
- The first output said "439 overpasses" in one month, which is impossible for a once-a-day
  satellite. GEE's loose footprints include orbits that never cover Pune. The date loop also
  processed the month *after* the end date.
- **Fix:** count distinct usable days; treat the end date as exclusive.
- **Lesson:** sanity-check counts against physics ("at most ~1–2 overpasses a day").

**7. OCO-2 only found 2024.**
- The log showed 152 days, all starting in January 2024. OCO-2's newest version (11.3r) covers only
  2024; 2019–2023 is 11.2r. The code had picked one "newest" version.
- **Fix:** choose the newest version **per day** → 1,177 days.
- **Lesson:** data archives mix versions across time.

**8. A network outage killed 159 OCO-2 days.**
- The log filled with `getaddrinfo failed`, a DNS/internet drop.
- **Fix:** the script records finished days, so a rerun retried only the failures. 0 left.
- **Lesson:** long downloads must be **resumable**.

**9. Duplicate lines in the progress file** (a restarted OCO-3 run, 41 days logged twice) made "days
scanned" read 236 instead of 195.
- **Fix:** count distinct days.

**10. The waypoints were wrong (G4).**
- 6 of 10 were more than 500 m off; Dehu Road by 4.4 km.
- **Fix:** OSM positions via the map tool, then snapped to the actual highway (D9).
- **Lesson:** verify coordinates from an independent source.

**11. The map showed "Access blocked".**
- OpenStreetMap's tile server refuses pages opened from a local file (they send no "Referer").
- **Fix:** CARTO and Esri tiles.

**12. OSM place centres make a zigzag corridor.**
- Neighbourhood centres aren't on the highway.
- **First attempt:** use the OSM highway itself. But it was incomplete: it stopped near Dehu Road,
  with 9 gaps where flyovers carry other names.
- **Second attempt:** a routed driving line (OSRM). **Rejected:** 42 km instead of ~30, and only 46%
  on the highway, because the stops landed on the wrong side of the dual carriageway, forcing U-turns.
- **Final:** snap each waypoint to the nearest highway point and join them in road order. That's
  30.2 km, a median 200 m from the road. Good enough: 200 m is tiny next to the 3.5 km buffer and
  the TROPOMI pixel size.
- **Lesson:** match the precision you need, not the precision you can imagine.

**13. Talegaon MIDC lay outside the corridor.**
- An overlap calculation showed 0% of Talegaon-area industry inside.
- **Fix:** add a circle. **2.0 km left a gap** (two separate pieces, which Earth Engine code can't
  handle as one shape) → 2.5 km.

**14. The Overpass API timed out (504).** A server-side issue. **Fix:** retry.

## Phase 1

**15. The GEE box returned 91 × 96 instead of 90 × 95** (the edges sat on pixel boundaries).
- **Fix:** shrink the box by a quarter pixel on each side.

**16. The pandas time-join crashed** (millisecond vs microsecond dates).
- **Fix:** convert both to nanoseconds.

**17. The EMG method is biased +12% on synthetic data.**
- The same error in two random seeds, so systematic, not bad luck.
- **Response:** we didn't hide it. We found its three causes and put 12% in the uncertainty budget.

**18. The first flux-divergence test failed**, but the *test* was wrong: it compared per-pixel
averages across areas of very different size.
- **Fix:** compare totals. The method itself was fine (−4%).
- **Lesson:** when a test fails, check the test too.

**19. Real flux-divergence totals don't level off with radius.**
- Unlike on synthetic data. Splitting into terms showed the sink term (~70%) keeps growing,
  because NO₂ 30 km out is still above the chosen background.
- **Response:** use flux divergence for **shares** (robust to ±2.4%), not totals (D10).

**20. ODIAC vs EDGAR: a 2.6× mismatch.**
- Before trusting it we checked ODIAC's units in NASA's documentation. They're tonnes of **carbon**,
  not CO₂. Even after converting (×44/12), ODIAC is 3.2× EDGAR in the same area. That's a real
  disagreement, and a finding in itself.
- **Lesson:** a surprising number → check units first.

**21. We expected OCO to confirm the CO₂. It can't.**
- The predicted Pune plume (0.02–0.15 ppm) is 10–20× smaller than the noise and the swath stripes.
- **Response:** report a non-detection with an upper limit (D11) rather than over-interpreting the
  lucky β ≈ 1. We also checked that β leaned on one near-calm day where the model is least valid.
- **Lesson:** a null result, honestly quantified, is still a result.

**22. The wrong assumption about CO sectors.**
- I first grouped **road transport** with the "high-CO" sectors (thinking of two-wheelers). EDGAR says
  Pune's road transport has a *low* CO:NOx (1.95); residential is the high one (77.9).
- **Fix:** group sectors by EDGAR's own numbers, not by assumption. Then scenario tests showed
  "industry replacing transport" is impossible → the excess CO means more household/biomass burning.
- **Lesson:** let the data define the groups.

**23. The CO terrain trap.**
- The raw CO map peaked over the Konkan coast, not Pune: more air above low ground means more CO.
- **Fix:** normalise by air mass, and remove static patterns (§6.10). Synthetic test: −1.4%, and ≈ 0
  with terrain alone.

**24. The IQR filter removed 29% of the real data.**
- The "local" filter looked perfect on synthetic data but flagged footprint edges in the real,
  oversampled L3 grid. We stopped the rerun immediately.
- **Fix:** the "temporal, k = 3" filter: 0.09% removed, plume preserved.
- **Lesson:** synthetic tests are only as good as their noise model. Check real-data removal rates.

**25. Phase 1 was declared "complete" too early.**
- A check against the proposal's own list found three missing items: IQR, the DE sensitivity test,
  and the report.
- **Fix:** all three were done, and the README was corrected in the meantime.
- **Lesson:** check "done" against the written plan, not memory.

**26. The fit window was too long (D19), and the biggest correction of the project.**
- A routine robustness test (adding a sloped background) changed the emission by 42%.
- **Investigated rather than picked:** on synthetic data the sloped model was fine. On real data the answer depended on how far downwind we fitted. Beyond ~45 km, PCMC and Talegaon add a *second* source, which the single-source model misread as slow decay.
- **Fix:** fit to 45 km with a sloped background. NOx rose ~20% (0.522 → 0.663 kg/s).
- **Knock-on:** the CO:NOx ratio fell from 21.2 to 16.7, and the earlier claim "Pune has more household burning than EDGAR" turned out to be an **artefact and was withdrawn**.
- **Lesson:** when a method is fixed, **rerun everything downstream and re-check every conclusion**, not just the headline number.

**27. The fix introduced its own instability.**
- With 6 parameters, small subsets (the westerly regime, one season) gave unphysical lifetimes (0.42 h) and huge bootstrap ranges. One of them inflated the uncertainty budget to a spurious ±52%.
- **Fix:** a quality rule (τ < 0.6 h or bootstrap range > ×2 → refit with a flat background).
- The DE test also showed CR = 0.3 doesn't converge in time with 6 parameters. All converged runs still agree exactly.

## Later Phase 1 analyses and Phase 2

**28. The lockdown EMG fit was degenerate.** For 25 Mar – 31 May 2020 alone, the EMG gave −84%, but with R² 0.62, a
parameter at its bound and an 8.8 h lifetime. The plume was too weak to fit.
- **Response:** don't use it; switch to a **model-free** check (city minus rural NO₂ excess): −74% (2020), −29% (2021).
- **Lesson:** when a model's assumptions fail, use a simpler, assumption-free measurement.

**29. A synthetic test that was too kind.** The CO flux-divergence test passed with random wind directions, but
Pune's real winds mostly blow one way, and then fixed terrain fakes a −70 mol/s source.
- **Fix:** test with the **real wind record**, and remove static patterns.
- **Lesson:** synthetic tests must mimic the real conditions that matter.

**30. EDGAR temporal profiles: name matching failed silently.** The first version matched sectors by *name*, fell back to
"flat" for most of them, and matched agricultural soils to "rice cultivation".
- **Fix:** match on IPCC codes (India for residential, region 7 otherwise).
- **Lesson:** print what was actually matched.

**31. Windows reserved names.** A folder called `aux` can't be created on Windows (`aux`, `con`, `nul` and `prn` are reserved).
Renamed to `edgar_aux_tables`. The `.rar` file was opened with Windows' built-in `tar.exe`.

**32. Earth Engine names single-band outputs `mean`.** VIIRS and HCHO came back blank for every cell.
- **Fix:** `setOutputs([name])`.
- **Lesson:** look at the first rows of every new output before running the full job.

**33. Sampling a coarse raster at its native scale over small polygons.** ERA5 (27.8 km) reduced over 1 km cells
left 7,560 of 10,720 rows empty, because most cells contain no pixel centre.
- **Fix:** sample at 1 km.

**34. The OpenStreetMap servers were overloaded for hours.** Smaller tiles, caching, mirrors and lighter queries all
helped, but too slowly (16/35 tiles).
- **Response:** a published fallback (GRIP4, inside Earth Engine), documented as D20, with OSM kept as the plan for v2.
- **Lesson:** don't let one external service block the whole project; have a documented plan B.

**35. The C: drive filled up again (76 MB)**, and Windows refused to start Python. Fixed by clearing the pip cache and temp files.

**36. Windows console encoding.** Printing "→" crashed when the output was piped (cp1252). Prints were switched to ASCII.

**37. Asking Earth Engine for the newest image of all of Sentinel-2** hung the check. Filter by place and date first.

**38. Waiting days for an overloaded API when a bulk file existed.** Overpass kept failing (16 of 35 tiles). The
Geofabrik regional extract (one 221 MB file, MD5-checked) gave the same OpenStreetMap data in 2.5 minutes of local
reading. Lesson: when a query service is the bottleneck, look for a bulk download of the same data.

**39. A "share" above 100%.** The first spatial-variance-share output gave 1.004 for static roads, which is impossible
for a fraction. The cause: the between-cell variance used n − 1 = 267 in the denominator and the total variance used
n − 1 = 10,719 (pandas' default sample variance). Fix: population variance (`ddof=0`) for both, which gives exactly 1.000.
Caught because a fraction can't exceed 1.

**40. A feature that didn't mean what its name said.** NDBI ("built-up index") was highest in rural C3 and negatively
correlated with NO₂ and night lights. Dry-season bare soil reflects SWIR like concrete. Caught only when writing the
per-cluster table for the Phase 2 report. Lesson: sanity-check each feature against layers you trust.

## Small tooling issues (for completeness)
- Git Bash sometimes choked on long inline Python heredocs. Scripts were written to files instead.
- Matplotlib titles were clipped by long axis labels. The fix was to anchor titles to the figure (`suptitle`).
- A mistyped memory path ("JANHAV" for "JANHAVI"). Retried.

## The pattern across all 40
Almost every problem was caught by one of three habits:
1. **Sanity-check numbers against physics** (439 overpasses? 29% outliers? a 2.6× mismatch?).
2. **Test methods on synthetic data with known answers**, and check real-data behaviour too.
3. **Write everything down** (the research log), so decisions can be explained later.
