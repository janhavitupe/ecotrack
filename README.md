# EcoTrack

Meteorology-informed, multi-source satellite estimation of urban fossil-fuel CO₂ emissions
along the Shivajinagar → Talegaon Dabhade corridor (Old Mumbai–Pune Highway), Pune.
Study period: October 2019 – May 2024, October–May seasons.

- Proposal: [docs/EcoTrack_Project_Proposal.md](docs/EcoTrack_Project_Proposal.md)
- Design decisions (changes from the proposal, with reasons): [docs/decisions.md](docs/decisions.md)
- Current stage: [docs/week1_checklist.md](docs/week1_checklist.md)
- Research log: [docs/research_log.md](docs/research_log.md)

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
src/ecotrack/          package: config, geometry, acquire/, feasibility/ (later: qc, grid, inversion, labels, models, validate)
data/raw, data/interim not in git; recreated by the acquire scripts
outputs/               figures, tables, feasibility results
docs/                  proposal, decisions, research log, checklists
archive/               superseded first-draft scripts, kept for reference
```
