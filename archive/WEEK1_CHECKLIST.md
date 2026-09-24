# EcoTrack — Week 1 Kickoff Checklist
Corridor: Shivajinagar → Talegaon Dabhade (Old Mumbai-Pune Highway)

Goal for the week: a working, QC'd TROPOMI NO2 pull over the corridor, plus every
account and folder you'll need for the next five months. Nothing fancy yet —
just prove the pipeline breathes.

---

## Day 1 — Accounts + repo skeleton
- [ ] Create Google Earth Engine account: https://earthengine.google.com (use a
      Google account you'll keep for the whole project — don't use a throwaway one)
- [ ] Create NASA Earthdata account: https://urs.earthdata.nasa.gov
      (needed later for OCO-3 and MERRA-2; do it now so it's not a blocker later)
- [ ] Create Copernicus Data Space account: https://dataspace.copernicus.eu
      (fallback for raw TROPOMI L2 if GEE's L3 product isn't detailed enough)
- [ ] Set up the project folder structure locally:
  ```
  ecotrack/
    data/raw/{tropomi,oco3,merra2,viirs,sentinel2,osm,edgar,odiac}/
    data/grid/
    src/
    notebooks/
    outputs/{figures,tables,models}/
    docs/research_log.md
  ```
- [ ] Start `docs/research_log.md` — one dated entry per day, even if it's
      just "installed X, it broke because Y". This log is what makes Phase 8
      (write-up) possible six months from now.

## Day 2 — Corridor geometry (ground-truth the waypoints)
- [ ] Open `corridor_geometry.py`. The waypoint coordinates in it are
      approximate — verify each one against OpenStreetMap or Google Maps and
      correct any that are off by more than ~500m. Record the correction and
      source in the code comments.
- [ ] Install geometry deps: `pip install shapely pyproj geopandas`
- [ ] Run `python corridor_geometry.py` — confirm it prints all 10 waypoints
      and (if libs installed) writes `corridor.geojson`
- [ ] Open `corridor.geojson` in QGIS or https://geojson.io to visually confirm
      the buffered corridor actually follows the highway and doesn't clip off
      Bhosari/Chinchwad MIDC or Talegaon MIDC industrial land. Adjust
      `CORRIDOR_BUFFER_KM` if it does.
- [ ] Decide now: will Phase 1's DE/line-density analysis run per waypoint
      sub-zone (Khadki, Pimpri-Chinchwad, Akurdi, Talegaon, etc.) or on the
      corridor as one long integrated source? Recommendation: per sub-zone,
      since that's what lets you compare industrial vs. traffic-dominated
      segments later — write this decision in the research log.

## Day 3 — First TROPOMI pull
- [ ] Install: `pip install earthengine-api geemap`
- [ ] Run `earthengine authenticate` once (opens browser login)
- [ ] Run a ONE-WEEK test pull first, not the full study period:
      `python pull_tropomi_gee.py --start 2025-01-01 --end 2025-01-08`
- [ ] Confirm it prints a nonzero image count and a plausible mean NO2 value
      (typical polluted-urban tropospheric NO2 column density is roughly
      1e-5 to 1e-4 mol/m², so sanity-check against that order of magnitude —
      if you get exactly 0 or NaN, something's wrong with geometry or dates,
      not the atmosphere)
- [ ] Check the export task at https://code.earthengine.google.com/tasks and
      confirm the GeoTIFF lands in your Google Drive folder

## Day 4 — Inspect what you actually got
- [ ] Download the exported GeoTIFF, open in QGIS or with `rioxarray` in Python
- [ ] Visually confirm: is there a visible NO2 enhancement along the corridor
      vs. the surrounding area? (You should see elevated values around
      Pimpri-Chinchwad especially — if the whole image looks flat/uniform,
      something in the QC masking is wrong)
- [ ] Check for cloud-masking gaps — January (dry season) should have
      relatively good coverage; if it's mostly masked out even in January,
      revisit the QA/cloud thresholds
- [ ] Log every observation, including anything unexpected, in the research log

## Day 5 — Decide the full study period, kick off MERRA-2/ERA5 pull
- [ ] Based on Day 3-4 results, confirm October–May as your primary study
      window for the corridor (avoids monsoon cloud gaps) — or adjust if
      January data looked patchy for an unexpected reason
- [ ] Start the wind data pull in parallel (ERA5 via GEE is the fastest path —
      no separate Earthdata auth needed):
  ```python
  import ee
  corridor_bbox = ee.Geometry.Rectangle([73.65, 18.50, 73.87, 18.75])
  era5 = (ee.ImageCollection('ECMWF/ERA5_LAND/HOURLY')
          .filterBounds(corridor_bbox)
          .filterDate('2025-01-01', '2025-01-08')
          .select(['u_component_of_wind_10m', 'v_component_of_wind_10m']))
  ```
- [ ] Kick off the OCO-3 feasibility query in parallel (this determines how
      much you can lean on Experiment B/D later — see below)

## Also this week, in parallel (don't block on these) — OCO-3 feasibility check
- [ ] Install: `pip install earthaccess`
- [ ] Run:
  ```python
  import earthaccess
  earthaccess.login()
  results = earthaccess.search_data(
      short_name="OCO3_L2_Lite_FP", version="11r",
      bounding_box=(73.65, 18.50, 73.87, 18.75),
      temporal=("2024-10-01", "2025-05-31"),
  )
  print(len(results))
  ```
- [ ] Record the count in the research log. This is your single biggest
      go/no-go signal for how much weight OCO-3 can carry in the final model —
      note it now, revisit at the Week 4 checkpoint, don't panic either way yet.

---

## End-of-week success criteria
By Friday you should be able to say all of the following are true:
- [ ] All three accounts created and working
- [ ] `corridor.geojson` exists, verified against a real map, matches the
      intended highway corridor
- [ ] At least one real TROPOMI NO2 GeoTIFF has been pulled, QC'd, and
      visually inspected over the corridor
- [ ] ERA5/MERRA-2 wind pull has started
- [ ] OCO-3 sounding count for the corridor is known and logged
- [ ] Research log has at least 5 dated entries

If any of these is not true by Friday, that's fine — but write down exactly
what's blocking it before the weekend, so Week 2 starts by solving that
specific problem instead of re-discovering it.
