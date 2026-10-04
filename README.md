# EcoTrack

Meteorology-informed, multi-source satellite estimation of urban fossil-fuel CO₂ emissions
along the Shivajinagar → Talegaon Dabhade corridor (Old Mumbai–Pune Highway), Pune.
Study period: October 2019 – May 2024, October–May seasons.

- Proposal: [docs/EcoTrack_Project_Proposal.md](docs/EcoTrack_Project_Proposal.md)
- **Findings to date: [docs/findings.md](docs/findings.md)**
- Design decisions (changes from the proposal, with reasons): [docs/decisions.md](docs/decisions.md)
- **New here? Learning guide (everything from zero, chapters 1–12): [docs/guide/00_START_HERE.md](docs/guide/00_START_HERE.md)**
- **Phase 1 report: [docs/phase1_report.md](docs/phase1_report.md)**
- **Illustrated progress report (PDF, 13 pages, for faculty/panel): [docs/EcoTrack_Progress_Report.pdf](docs/EcoTrack_Progress_Report.pdf)**. Rebuild with `python -m ecotrack.progress_report`
- Current stage: **Phase 1 complete** (D8, D11, D12 await the guide's sign-off). **Phase 2 complete:** feature table **v2** frozen (268 cells × 40 months, 17 features, 0 missing; OpenStreetMap roads + industrial land from a Geofabrik extract, GRIP4 cross-check, correlation QA, SHA-256 in the meta file). Done: (NO₂ inversion, NOx → CO₂, inventory comparison, OCO check, TROPOMI CO sector constraint). Headline (Pune + PCMC, ≤ 25 km; after D19): **2.79 Mt fossil CO₂/yr annual mean [95%: 1.79–4.36]** (midday Oct–May rate 3.39 [2.26–5.08]). Next: guide review of D8/D11/D12/D16/D19, then Phase 3 labels. See [docs/findings.md §8](docs/findings.md)
- Feasibility memo for the guide: [docs/feasibility_memo.md](docs/feasibility_memo.md) · Weeks 0–2 checklist: [docs/week1_checklist.md](docs/week1_checklist.md)
- Research log: [docs/research_log.md](docs/research_log.md)
- Data dictionary (feature table columns): [docs/data_dictionary.md](docs/data_dictionary.md)
- Phase 3 design note (labels; for guide review): [docs/phase3_design.md](docs/phase3_design.md)

## Setup
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
earthengine authenticate
```

## Layout
```
configs/study.yaml     every threshold and region definition (single source of truth)
src/ecotrack/          package: config, geometry, grid (Phase 2), features (Phase 2 table), acquire/ (TROPOMI, ERA5, OCO, EDGAR, ODIAC), feasibility/ (G1–G4),
                       inversion/ (EMG, flux divergence, CO2 conversion, OCO check, CO ratio); later: grid, labels, models, validate
tests/                 synthetic-plume recovery tests for the inversion methods (python -m pytest)
data/raw, data/interim not in git (recreated by the acquire scripts); data/processed (frozen feature table) is committed
outputs/               figures, tables, feasibility results
docs/                  proposal, decisions, research log, checklists
archive/               superseded first-draft scripts, kept for reference
```
