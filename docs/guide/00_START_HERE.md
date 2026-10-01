# EcoTrack Learning Guide — Start Here

This guide teaches you **everything** about the EcoTrack project from zero: what problem it solves,
every dataset (what it is, who makes it, what the numbers mean), every tool, every step we took,
every mistake we made and fixed, and every technical word. It assumes you know basic school
physics and chemistry and a little Python, **nothing more**.

By the end you should be able to:
- explain the project to anyone, including a viva panel;
- defend every choice we made ("why 850 hPa?", "why not OCO-3 as a feature?");
- **rebuild the whole project yourself**, from an empty folder to the final numbers.

## Reading order

| # | Chapter | What you'll learn | Time |
|---|---|---|---|
| 1 | [01_big_picture.md](01_big_picture.md) | The problem, the idea, the answer, in plain words | 20 min |
| 2 | [02_science_basics.md](02_science_basics.md) | The physics and chemistry you need: gases, columns, wind, lifetime, emissions, units | 1 h |
| 3 | [03_data.md](03_data.md) | **Every dataset, A to Z**: TROPOMI, OCO-2/3, ERA5, SRTM, EDGAR, ODIAC, OpenStreetMap | 1.5 h |
| 4 | [04_tools_and_setup.md](04_tools_and_setup.md) | Python, libraries, accounts, Earth Engine, the repo, the config file | 45 min |
| 5 | [05_feasibility_steps.md](05_feasibility_steps.md) | The four go/no-go checks (G1–G4), step by step | 1 h |
| 6 | [06_phase1_methods.md](06_phase1_methods.md) | **Every Phase 1 method, with worked examples on our real numbers** | 2–3 h |
| 7 | [07_mistakes_and_backtracking.md](07_mistakes_and_backtracking.md) | Every wrong turn, how we noticed it, how we fixed it | 45 min |
| 8 | [08_replicate_it_yourself.md](08_replicate_it_yourself.md) | A hands-on checklist to rebuild everything, with the numbers you should get | a day of doing |
| 9 | [09_glossary.md](09_glossary.md) | Every term, A to Z | reference |
| 10 | [10_viva_questions.md](10_viva_questions.md) | Questions an examiner might ask, with model answers | 1 h |
| 11 | [11_code_walkthrough.md](11_code_walkthrough.md) | **How to read the code**: reading order, what produces what, hands-on snippets, tracing a number back | 8 short sessions |

**How to study it:** read chapters 1–3 carefully (the foundation), skim 4, then read 5–7 with
the code open beside you, following the reading order in chapter 11. Do chapter 8 on your own machine. Keep chapter 9 open in another tab
the whole time: every **bold technical word** in the guide is defined there.

## Where everything lives

```
D:\EcoTrack\
├── configs\study.yaml        ← every setting and threshold (chapter 4)
├── src\ecotrack\             ← all the code
│   ├── acquire\              ← downloads data (chapter 3)
│   ├── feasibility\          ← the G1–G4 checks (chapter 5)
│   ├── inversion\            ← the science methods (chapter 6)
│   ├── geometry.py, qc.py, config.py
├── tests\                    ← the synthetic "does the method work?" tests (chapter 6)
├── data\                     ← downloaded data (not in git; you re-download it)
├── outputs\                  ← results: JSON numbers + PNG figures
└── docs\                     ← proposal, decisions, log, findings, reports, and this guide
```

The other docs, and when to use them:
- `docs/phase1_report.md`: the formal report for your guide (the "what").
- `docs/findings.md`: every result and table (the "how much").
- `docs/decisions.md`: D1–D13, the reasoning behind every change (the "why").
- `docs/research_log.md`: the diary, day by day (the "when").
- **This guide**: the "how does any of this actually work", written to teach.
