# Chapter 5 — The Feasibility Checks (G1–G4), Step by Step

**Why do checks first at all?** The proposal made several assumptions: that TROPOMI sees Pune
often enough, that Pune's NO₂ stands out, that OCO-3 has data here, that the waypoints are right.
If any of these is false, months of later work are wasted. So before building anything, we ran
four **go/no-go gates**, each with a pass/fail rule decided *in advance*. That's good scientific
practice: you can't move the goalposts after seeing the answer.

---

## G4 — Are the places in the right place? (geometry)

**Question:** are the 10 waypoint coordinates in the proposal correct, and does the corridor cover
the industrial areas we care about?

**Steps:**
1. `g4_verify_waypoints.py` asks **Nominatim** (OSM's place search) for each place name, e.g.
   "Khadki, Pune, Maharashtra, India", and measures the distance to our coordinate with the
   **haversine formula** (the distance between two points on a sphere). More than 500 m → flag it.
   - Nominatim's usage policy allows 1 request per second, so the script waits 1.1 s between calls.
2. **Result:** 6 of 10 were off by more than 500 m. **Dehu Road by 4.4 km** (the coordinate pointed
   at Dehu town, not the Dehu Road cantonment); Talegaon 2.1 km; Pimpri, Chinchwad, Nigdi and
   Kasarwadi 1.3–1.5 km.
3. `g4_map.py` builds an **interactive HTML map** (Leaflet library) with draggable markers, the OSM
   positions, the corridor, the clusters and 259 OSM industrial polygons. You clicked "use OSM" for all 10.
4. **Problem:** OSM place positions are *neighbourhood centres*, not points on the highway. A line
   through them zigzags (Nigdi's centre is east of Akurdi's).
5. **Fix (decision D9):** snap each waypoint to the **nearest point of the actual highway** (fetched
   from OSM via Overpass: roads named "Old Pune–Mumbai Highway"), in road order. That makes a
   30.2 km centreline, a median 200 m from the real road. The corridor = centreline buffered ±3.5 km.
6. **Industrial check:** MIDC Bhosari is 99–100% inside ✅. **Talegaon MIDC is outside**: it's
   ~5 km north of the town. We added a 2.5 km circle over it. (2.0 km left a gap that split the
   corridor into two pieces; 2.5 km joins them.)
7. **Final corridor: one polygon, 269 km² (≈ 269 grid cells of 1 km).**

**Concepts:** buffering (§2.8); UTM metres, so the 3.5 km is real kilometres; a MultiPolygon (a
shape in several pieces) vs a Polygon (one piece). Earth Engine code expects one piece.

---

## G2 — Does TROPOMI see the corridor often enough? (coverage)

**Question:** after removing clouds and bad retrievals, how many usable days per month?
**Pass rule:** ≥ ~8 usable days in most months → monthly averages are possible.

**Steps (`g2_tropomi_coverage.py`):**
1. For each study month, take all TROPOMI L3 images touching the corridor.
2. Apply QC: cloud fraction ≤ 0.3, solar zenith ≤ 70°.
3. For each image, count the valid corridor pixels ÷ all 230 corridor pixels = the **valid fraction**.
4. An overpass is **usable** if the valid fraction ≥ 0.5. Count the **distinct usable days** per month.

**Result: PASS.** Median **26 usable days per month**; minimum 13 (October 2019 and October 2020,
late-monsoon cloud); no month below 5.

| Oct | Nov | Dec | Jan | Feb | Mar | Apr | May |
|---|---|---|---|---|---|---|---|
| 17.4 | 21.8 | 23.4 | 26.4 | 27.6 | 28.8 | 26.2 | 24.6 |

(Mean usable days per month over 5 seasons.)

**Things we learned:**
- GEE returned ~440 images per month, because its footprints are loose and it includes orbits that
  never cover Pune. So count *days*, not images.
- The first version also processed the month *after* the end date (an off-by-one bug). Fixed.
- The GEE NO₂ product has **no qa_value band** (see chapter 3).

---

## G3 — Is Pune's NO₂ visibly above background? (signal)

**Question:** is there a clear NO₂ excess over each cluster?
**Pass rule:** enhancement ≥ ~1.5× → cluster-scale analysis is worth trying.

**Steps (`g3_no2_signal.py`):**
1. For each season (October–May), average all QC'd TROPOMI images into one **composite** map.
2. **Background** = the 10th percentile of that map over a wide rural box
   (73.30–74.30°E, 18.20–19.00°N, including Western Ghats forest). This is "clean air".
3. **Enhancement ratio** = cluster mean ÷ background.

**Result: PASS.**

| Season | C1 Shivajinagar–Kasarwadi | C2 PCMC | C3 Dehu–Talegaon |
|---|---|---|---|
| 2019–20 | 2.22× | 2.10× | 1.74× |
| 2023–24 | 2.37× | 2.25× | 1.78× |

(All 5 seasons are between these; see findings.md.)

**The caveat we flagged, and later confirmed:** a high value doesn't prove a cluster *emits* that
much. C1 sits next to central Pune, and C3 is downwind of PCMC. G3 proves a **signal exists**,
not that the clusters can be **separated**. Phase 1 did the separating.

---

## G1 — Do CO₂ satellites see Pune? (OCO-3 / OCO-2)

**Question:** how many good-quality XCO₂ soundings fall on Pune?
**Rule (set in advance):**
- ≥ ~15 usable days → OCO can be a training target;
- 5–15 → a case study;
- < 5 → qualitative only.

**Steps (`g1_oco_soundings.py`):**
1. Search NASA's catalogue for OCO-3 Lite files in the study months (893 days); OCO-2 likewise (1,177 days).
2. **For each daily global file**, stream only the `latitude`/`longitude` arrays, find soundings near
   Pune (the box ± 0.25°), and save those rows to `data/interim/oco/oco3_soundings.csv`.
   - The script records finished days in `oco3_scanned.txt`, so it **resumes** after interruptions.
3. Keep only `xco2_quality_flag == 0` (good).
4. Count per day: inside the corridor; inside the box (city scale).

**Result: PARTIAL.**
- Corridor only: 6 usable days.
- City scale: **7 strong OCO-3 days** (≥ 50 good soundings), 6 of them **Snapshot Area Maps**,
  plus **1 OCO-2 day** (2024-01-23).
- **Pune is an OCO-3 SAM target.**
- No OCO-3 data after November 2023 (except that OCO-2 track).
- Conclusion: a city-scale case study, not an ML target (D8). Phase 1 later showed even that
  can't *detect* Pune (D11; chapter 6).

**Things we learned (all in chapter 7):** the "granule count" trap; the 403 error from approving the
wrong NASA application; the OCO-2 version bug; the network outage (159 days re-scanned); duplicate
lines in the progress file.

---

## Wind check (ERA5), done at the end of feasibility

`era5_overpass.py` matched each usable TROPOMI overpass to ERA5 (the nearest hour).
- Wind classes at 850 hPa: **192 calm** (< 2 m/s) · 429 at 2–4 · 334 at 4–7 · 73 above 7 m/s.
  That's enough calm days to locate the source, and enough windy days to fit plumes.
- **Two regimes:** October–March from the ESE (Pune → up the corridor); April–May from the WNW.

## The feasibility memo

All of this was written up for your guide in `docs/feasibility_memo.md`, with an update box added
later for the Phase 1 surprises.
