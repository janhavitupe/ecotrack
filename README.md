# EcoTrack

Meteorology-informed, multi-source satellite estimation of urban fossil-fuel CO₂ emissions
along the Shivajinagar → Talegaon Dabhade corridor (Old Mumbai–Pune Highway), Pune.
Study period: October 2019 – May 2024, October–May seasons.

- Proposal: [docs/EcoTrack_Project_Proposal.md](docs/EcoTrack_Project_Proposal.md)
- **Findings to date: [docs/findings.md](docs/findings.md)**
- Design decisions (changes from the proposal, with reasons): [docs/decisions.md](docs/decisions.md)
- **New here? Learning guide (everything from zero, chapters 1–14): [docs/guide/00_START_HERE.md](docs/guide/00_START_HERE.md)**
- **Phase 1 report: [docs/phase1_report.md](docs/phase1_report.md)**
- **Phase 2 report: [docs/phase2_report.md](docs/phase2_report.md)**
- **Phase 3 report (labels): [docs/phase3_report.md](docs/phase3_report.md)**
- **Phase 4 report (regional training grid, model table, CV blocks): [docs/phase4_report.md](docs/phase4_report.md)** · **Analysis plan for the ML experiments: [docs/phase5_analysis_plan.md](docs/phase5_analysis_plan.md)**
- **Illustrated progress report (PDF, 25 pages, for faculty/panel): [docs/EcoTrack_Progress_Report.pdf](docs/EcoTrack_Progress_Report.pdf)**. Rebuild with `python -m ecotrack.progress_report`
- Current stage: **Phase 1 complete** (D8, D11, D12 await the guide's sign-off). **Phase 2 complete:** feature table **v2** frozen (268 cells × 40 months, 17 features, 0 missing; OpenStreetMap roads + industrial land from a Geofabrik extract, GRIP4 cross-check, correlation QA, SHA-256 in the meta file). Done: (NO₂ inversion, NOx → CO₂, inventory comparison, OCO check, TROPOMI CO sector constraint). Headline (Pune + PCMC, ≤ 25 km; after D19): **2.79 Mt fossil CO₂/yr annual mean [95%: 1.79–4.36]** (midday Oct–May rate 3.39 [2.26–5.08]). **Phase 3 built:** labels v1 (1,340 cell-seasons; L-fd from NO₂, noise ceiling 0.97; L-co from CO, spatial-only, 0.75; D16/D21 await the guide). **Phase 4 done:** regional training grid (2,894 cells, D22), model table, 15 km CV blocks from the label-error variogram (D23, ~13 independent areas). Next: freeze the analysis plan, then Phase 5 (Experiments A–D + controls); guide review of D8/D11/D12/D16/D19/D21–D23. See [docs/findings.md §8](docs/findings.md)
- **Overall architecture, Phase 1 + Phase 2 (compact, Figma-importable): [docs/figures/architecture_p1p2.svg](docs/figures/architecture_p1p2.svg) · [PNG](docs/figures/architecture_p1p2.png)**. Rebuild with `python docs/figures/make_architecture_p1p2.py`
- **Methodology tree diagram (datasets → image / numerical → processing → estimation → ML → outputs; Figma-importable): [docs/figures/methodology_tree.svg](docs/figures/methodology_tree.svg) · [PNG](docs/figures/methodology_tree.png)**. Rebuild with `python docs/figures/make_methodology_tree.py`
- Datasets + methodology architecture diagram (for the guide; Figma-importable SVG, OCO excluded): [docs/figures/architecture_diagram.svg](docs/figures/architecture_diagram.svg) · PNG: [architecture_diagram.png](docs/figures/architecture_diagram.png). Rebuild with `python docs/figures/make_architecture_diagram.py`. One-page compact version: [methodology_compact.svg](docs/figures/methodology_compact.svg) / [.png](docs/figures/methodology_compact.png) (`python docs/figures/make_methodology_compact.py`)
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
