# Weeks 0–2 — Feasibility Checks (G1–G4)

Goal: answer four questions before building the main pipeline. The answers decide the final
design. The result of this stage is a **2-page feasibility memo** for your guide, written from
the JSON files in `outputs/feasibility/`.

## Setup (Day 1)
```bash
cd D:\EcoTrack
.venv\Scripts\activate
pip install -e .
earthengine authenticate          # once; note your GCP project id
```
Earthdata: create `%USERPROFILE%\_netrc` with
`machine urs.earthdata.nasa.gov login <user> password <pass>` (or let `earthaccess` prompt you).
In your Earthdata profile, also approve the **NASA GESDISC DATA ARCHIVE** application, otherwise downloads return 401.

Every day, add one dated entry to `docs/research_log.md`.

## G4 — Waypoints and corridor (Day 1–2, ~1 hour)
- [ ] `python -m ecotrack.feasibility.g4_verify_waypoints`
- [ ] Fix any `CHECK` rows in `configs/study.yaml`, and set `status: verified OSM <date>`
- [ ] `python -m ecotrack.geometry`, then drag `data/interim/corridor.geojson` onto https://geojson.io
- [ ] Check the corridor covers **Bhosari MIDC** (≈4 km east of Pimpri, so it may be clipped at 3.5 km), Chinchwad MIDC and Talegaon MIDC. Widen the buffer or add a waypoint if not, and log the change.

## G2 — TROPOMI coverage (Day 2)
- [ ] Test on one month first: `python -m ecotrack.feasibility.g2_tropomi_coverage --project <id> --start 2020-01-01 --end 2020-02-01`
- [ ] Note in the log whether `qa_value` was present (the GEE L3 product is pre-filtered, so it affects the QC wording in Methods)
- [ ] Full run (default dates) → `outputs/feasibility/g2_tropomi_summary.json`

## G1 — OCO-3 / OCO-2 soundings (start Day 2, runs for hours; resumable)
- [ ] One season first: `python -m ecotrack.feasibility.g1_oco_soundings --product oco3 --start 2019-10-01 --end 2020-05-31`
- [ ] Then the full period: `python -m ecotrack.feasibility.g1_oco_soundings --product oco3`
- [ ] Same for `--product oco2` as a fallback
- [ ] Record usable days, the operation mode breakdown (are there Snapshot Area Map (SAM) observations over Pune?), and any gap in the record (D7)

## G3 — NO₂ signal over the clusters (Day 3)
- [ ] `python -m ecotrack.feasibility.g3_no2_signal --project <id>`
- [ ] Open the exported seasonal map from Drive in QGIS. Is the enhancement on PCMC, or only on central Pune?

## Week 1 manual run (Day 3–4)
- [ ] `python -m ecotrack.acquire.tropomi_gee --start 2020-01-01 --end 2020-01-08 --project <id>` and inspect the GeoTIFF

## Decision point (end of week 2)
Fill in this table in the memo, and add D8+ entries to `docs/decisions.md`:

| Check | Result | Decision |
|---|---|---|
| G1 OCO-3 usable days | | Validation target / case study / qualitative only |
| G2 usable overpasses per month | | Monthly vs. seasonal composites |
| G3 cluster enhancement ratios | | 3 clusters vs. one city source |
| G4 waypoints / corridor | | Final buffer, final waypoint list |
