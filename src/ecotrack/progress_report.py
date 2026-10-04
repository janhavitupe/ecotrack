"""
Build the illustrated progress report PDF (docs/EcoTrack_Progress_Report.pdf).

Makes a few explanatory figures that don't exist elsewhere (pipeline diagram, study-area map with
the grid, coverage chart, COVID check, D19 fit-window comparison, per-cell feature maps, phase status)
into outputs/report/figures/, then lays out the PDF with reportlab, reusing the result figures in
outputs/phase1/ and outputs/phase2/. Every number is read from the result files or quoted from
docs/findings.md (post-D19 values).

Usage:
    python -m ecotrack.progress_report
"""

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon as MplPolygon
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from ecotrack.config import DATA_INTERIM, OUTPUTS, ROOT
from ecotrack.inversion.run_city import BLUE, GRID, INK, INK2, ORANGE, SEQ, SURFACE

FIG = OUTPUTS / "report" / "figures"
P1 = OUTPUTS / "phase1" / "figures"
PDF = ROOT / "docs" / "EcoTrack_Progress_Report.pdf"
AQUA, RED, VIOLET = "#1baf7a", "#e34948", "#4a3aa7"
CLUSTER_COL = {"C1_shivajinagar_kasarwadi": BLUE, "C2_pcmc": ORANGE, "C3_dehu_talegaon": AQUA}
plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "axes.edgecolor": GRID, "font.size": 10,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
                     "axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": 200})


# ============================================================================ figures
def fig_pipeline():
    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.set_xlim(0, 10); ax.set_ylim(0, 6); ax.axis("off")

    def box(x, y, w, h, text, col, txtcol="white"):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12", fc=col, ec="none"))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8.5, color=txtcol, wrap=True)

    def arrow(x0, y0, x1, y1):
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=12, color=INK2, lw=1.2))

    # inputs
    ins = [("TROPOMI NO₂\n1,004 days", BLUE), ("TROPOMI CO\n907 days", BLUE), ("ERA5 wind\n& weather", AQUA),
           ("OCO-3 / OCO-2\nXCO₂, 8 dates", VIOLET), ("EDGAR / ODIAC\ninventories", INK2), ("VIIRS, Sentinel-2,\nHCHO, OSM roads\n& industry", ORANGE)]
    for i, (t, c) in enumerate(ins):
        box(0.1, 5.05 - i * 0.86, 1.9, 0.7, t, c)
    # phase 1 chain
    box(2.7, 4.65, 2.2, 0.9, "1. Find the source\n(calm-day NO₂ peak)", "#256abf")
    box(2.7, 3.45, 2.2, 0.9, "2. How much NOx?\nwind rotation + EMG fit\n0.663 kg/s, τ 1.09 h", "#256abf")
    box(2.7, 2.25, 2.2, 0.9, "3. Where exactly?\nflux-divergence map\ncorridor = 21%", "#256abf")
    box(5.5, 3.45, 2.1, 0.9, "4. NOx → CO₂\nratio from TROPOMI CO\n= 163 (148–180)", "#1c5cab")
    box(5.5, 2.25, 2.1, 0.9, "5. Checks\nOCO (upper limit), COVID,\nseasons, synthetic tests", "#1c5cab")
    box(8.1, 3.0, 1.8, 1.6, "HEADLINE\n2.79 Mt CO₂/yr\n(annual mean)\n95%: 1.79–4.36", ORANGE)
    # phase 2
    box(2.7, 0.55, 4.9, 1.0, "PHASE 2 — 1 km grid (268 cells) × 40 months\nfeature table v2: 17 features, 0 missing", AQUA)
    box(8.1, 0.55, 1.8, 1.0, "NEXT\nPhase 3 labels →\nML experiments", INK2)
    for y in (5.4, 4.54, 3.68):
        arrow(2.0, y, 2.7, 4.0)
    arrow(3.8, 4.65, 3.8, 4.35); arrow(3.8, 3.45, 3.8, 3.15)
    arrow(4.9, 3.9, 5.5, 3.9); arrow(4.9, 2.7, 5.5, 2.7)
    arrow(7.6, 3.9, 8.1, 3.9); arrow(7.6, 2.7, 8.1, 3.3)
    arrow(2.0, 0.93, 2.7, 1.05); arrow(7.6, 1.05, 8.1, 1.05)
    ax.text(0.1, 5.85, "DATA", fontsize=10, weight="bold", color=INK2)
    ax.text(2.7, 5.85, "PHASE 1 — satellite emission estimate", fontsize=10, weight="bold", color=INK2)
    fig.tight_layout(); fig.savefig(FIG / "pipeline.png", bbox_inches="tight"); plt.close(fig)


def fig_study_area():
    corr = json.loads((DATA_INTERIM / "corridor.geojson").read_text())
    cells = json.loads((DATA_INTERIM / "grid" / "cells.geojson").read_text())
    meta = pd.read_csv(DATA_INTERIM / "grid" / "cells.csv").set_index("cell_id")
    fig, ax = plt.subplots(figsize=(7, 6.4))
    for f in cells["features"]:
        ring = np.array(f["geometry"]["coordinates"][0])
        col = CLUSTER_COL[meta.loc[f["properties"]["cell_id"], "cluster"]]
        ax.add_patch(MplPolygon(ring, closed=True, fc=col, ec=SURFACE, lw=0.4, alpha=0.75))
    for f in corr["features"]:
        g = f["geometry"]
        if f["properties"].get("name") == "corridor":
            polys = g["coordinates"] if g["type"] == "Polygon" else [p[0] for p in g["coordinates"]]
            for ring in (polys if g["type"] == "Polygon" else polys):
                r = np.array(ring if g["type"] != "Polygon" else ring)
                ax.plot(r[:, 0], r[:, 1], color=INK, lw=1.2)
        elif g["type"] == "Point":
            x, y = g["coordinates"]
            ax.plot(x, y, "o", ms=4, color=INK)
            ax.text(x + 0.006, y, f["properties"]["name"], fontsize=7, color=INK, va="center")
    ax.plot(73.855, 18.485, "*", ms=16, mfc=RED, mec=SURFACE, mew=1.5)
    ax.text(73.862, 18.478, "Main source\n(central Pune)", fontsize=8, color=RED, va="top")
    ax.plot(73.795, 18.625, "*", ms=13, mfc=VIOLET, mec=SURFACE, mew=1.5)
    ax.text(73.70, 18.612, "PCMC hotspot", fontsize=8, color=VIOLET)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=BLUE, label="C1 Shivajinagar–Kasarwadi (91 cells)"),
                       Patch(color=ORANGE, label="C2 PCMC (63 cells)"),
                       Patch(color=AQUA, label="C3 Dehu Road–Talegaon (114 cells)")],
              loc="lower left", frameon=False, fontsize=8)
    ax.set_xlabel("Longitude (°E)"); ax.set_ylabel("Latitude (°N)"); ax.set_aspect(1 / np.cos(np.radians(18.6)))
    ax.set_title("Study corridor (269 km²) and the 1 km grid (268 cells)", fontsize=11, loc="left")
    fig.tight_layout(); fig.savefig(FIG / "study_area.png", bbox_inches="tight"); plt.close(fig)


def fig_coverage():
    m = pd.read_csv(OUTPUTS / "feasibility" / "g2_tropomi_monthly.csv")
    m["mon"] = m.month.str[5:7].astype(int)
    order = [10, 11, 12, 1, 2, 3, 4, 5]
    names = ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May"]
    mean = m.groupby("mon").usable_days.mean().reindex(order)
    fig, ax = plt.subplots(figsize=(7, 2.8))
    bars = ax.bar(names, mean.values, color=BLUE, width=0.6)
    for b, v in zip(bars, mean.values):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.5, f"{v:.0f}", ha="center", fontsize=8, color=INK)
    ax.axhline(8, color=ORANGE, ls="--", lw=1.2); ax.text(7.6, 8.6, "pass\nline (8)", ha="left", fontsize=8, color=ORANGE)
    ax.set_ylabel("Usable days / month"); ax.set_ylim(0, 33); ax.set_xlim(-0.6, 8.3); ax.grid(axis="x", visible=False)
    ax.set_title("TROPOMI coverage over the corridor (G2): median 26 usable days per month", fontsize=10, loc="left")
    fig.tight_layout(); fig.savefig(FIG / "coverage.png", bbox_inches="tight"); plt.close(fig)


def fig_covid():
    yrs = ["2020\nlockdown", "2021\nrestrictions", "2022", "2023", "2024"]
    vals = [7.8, 21.5, 27.3, 29.3, 34.3]  # research log 2026-10-01 (model-free city-minus-rural NO2 excess)
    cols = [RED, ORANGE, BLUE, BLUE, BLUE]
    fig, ax = plt.subplots(figsize=(7, 2.9))
    bars = ax.bar(yrs, vals, color=cols, width=0.6)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.6, f"{v:.1f}", ha="center", fontsize=8, color=INK)
    ax.text(0, 12, "−74%", ha="center", fontsize=10, weight="bold", color=RED)
    ax.text(1, 25.5, "−29%", ha="center", fontsize=10, weight="bold", color=ORANGE)
    ax.set_ylabel("City NO₂ excess (µmol/m²)"); ax.grid(axis="x", visible=False)
    ax.set_title("The satellite sees COVID-19: 25 March – 31 May of each year (model-free check)", fontsize=10, loc="left")
    fig.tight_layout(); fig.savefig(FIG / "covid.png", bbox_inches="tight"); plt.close(fig)


def fig_d19():
    win = ["60 km\n(original)", "45 km\n(adopted)", "30 km"]
    flat, sloped = [0.522, 0.591, 0.609], [0.740, 0.663, 0.651]
    x = np.arange(3)
    fig, ax = plt.subplots(figsize=(7, 3.0))
    ax.bar(x - 0.17, flat, 0.32, color=INK2, label="flat background")
    ax.bar(x + 0.17, sloped, 0.32, color=BLUE, label="sloped background")
    for i in range(3):
        ax.text(i - 0.17, flat[i] + 0.01, f"{flat[i]:.3f}", ha="center", fontsize=8)
        ax.text(i + 0.17, sloped[i] + 0.01, f"{sloped[i]:.3f}", ha="center", fontsize=8)
    ax.add_patch(FancyBboxPatch((0.6, 0), 0.8, 0.79, boxstyle="round,pad=0", fc=ORANGE, alpha=0.08, ec="none"))
    ax.set_xticks(x, win); ax.set_ylabel("City NOx (kg/s)"); ax.set_ylim(0, 0.85); ax.grid(axis="x", visible=False)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    ax.set_title("D19: how far downwind to fit? Beyond ~45 km a second source (PCMC/Talegaon) biases NOx low",
                 fontsize=9.5, loc="left")
    fig.tight_layout(); fig.savefig(FIG / "d19.png", bbox_inches="tight"); plt.close(fig)


def fig_cells():
    cells = json.loads((DATA_INTERIM / "grid" / "cells.geojson").read_text())
    ft = pd.read_csv(ROOT / "data" / "processed" / "feature_table_v2.csv")
    means = ft.groupby("cell_id")[["no2", "viirs_rad", "road_total_km", "industrial_frac"]].mean()
    fig, axes = plt.subplots(1, 4, figsize=(13, 4.3))
    for ax, (col, label, scale) in zip(axes, [("no2", "NO₂ (µmol/m²)", 1e6), ("viirs_rad", "Night lights (nW/cm²/sr)", 1),
                                              ("road_total_km", "Road length (km per cell, OSM)", 1),
                                              ("industrial_frac", "Industrial land (% of cell)", 100)]):
        v = means[col] * scale
        norm = plt.Normalize(v.quantile(0.02), v.quantile(0.98))
        for f in cells["features"]:
            ring = np.array(f["geometry"]["coordinates"][0])
            ax.add_patch(MplPolygon(ring, closed=True, fc=SEQ(norm(v[f["properties"]["cell_id"]])), ec="none"))
        ax.autoscale_view(); ax.set_aspect(1 / np.cos(np.radians(18.6))); ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
        sm = plt.cm.ScalarMappable(norm=norm, cmap=SEQ)
        cb = fig.colorbar(sm, ax=ax, shrink=0.75, orientation="horizontal", pad=0.03)
        cb.set_label(label, color=INK2, fontsize=8); cb.outline.set_edgecolor(GRID); cb.ax.tick_params(labelsize=7); cb.ax.locator_params(nbins=5)
    fig.suptitle("Four of the 17 features on the 1 km grid (average over 40 months)", fontsize=10, x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(FIG / "cells.png", bbox_inches="tight"); plt.close(fig)


def fig_spatial_share():
    q = json.loads((OUTPUTS / "phase2" / "qa_feature_table_v2.json").read_text())["spatial_variance_share"]
    groups = [("Roads (4) & industrial land", ["road_total_km", "industrial_frac"]), ("NDVI / NDBI", ["ndvi", "ndbi"]),
              ("Night lights", ["viirs_rad"]), ("NO₂", ["no2"]), ("HCHO", ["hcho"]), ("CO", ["co_norm"]),
              ("Weather (6)", ["ws850", "wd850", "blh_m", "frac_ese", "t2m_k", "ssrd_j_m2"])]
    names = [g for g, _ in groups]
    vals = [float(np.mean([q[c] for c in cols])) for _, cols in groups]
    fig, ax = plt.subplots(figsize=(7, 3.0))
    cols = [AQUA if v > 0.8 else (BLUE if v > 0.1 else INK2) for v in vals]
    ax.barh(names, vals, color=cols, height=0.6)
    for i, v in enumerate(vals):
        ax.text(v + 0.01, i, f"{v:.2f}", va="center", fontsize=8)
    ax.invert_yaxis(); ax.set_xlim(0, 1.12); ax.grid(axis="y", visible=False)
    ax.set_xlabel("Share of variance that is between cells (1 = only 'where', 0 = only 'when')")
    ax.set_title("Which features can tell the model WHERE emissions are?", fontsize=10, loc="left")
    fig.tight_layout(); fig.savefig(FIG / "spatial_share.png", bbox_inches="tight"); plt.close(fig)


def fig_status():
    phases = ["Feasibility (G1–G4)", "Phase 1: NO₂ → CO₂", "Phase 2: feature table", "Phase 3: labels",
              "Phase 4: feature tensor", "Phase 5: models A–D", "Phase 6: ablation", "Phase 7: validation", "Phase 8: write-up"]
    done = [1.0, 1.0, 1.0, 0.25, 0.0, 0.0, 0.0, 0.35, 0.3]
    notes = ["done", "done (guide sign-off pending)", "done: feature table v2 frozen", "designed + tested; needs guide (D16)",
             "next after labels", "", "", "uncertainty, COVID, maps done early", "reports + guide written"]
    fig, ax = plt.subplots(figsize=(9, 3.9))
    for i, (p, d, n) in enumerate(zip(phases, done, notes)):
        ax.barh(i, 1, color=GRID, height=0.55)
        ax.barh(i, d, color=AQUA if d >= 1 else (BLUE if d > 0 else GRID), height=0.55)
        ax.text(1.02, i, n, va="center", fontsize=8, color=INK2)
    ax.set_yticks(range(len(phases)), phases); ax.invert_yaxis(); ax.set_xlim(0, 1.6); ax.set_xticks([])
    for s in ("bottom", "left"):
        ax.spines[s].set_visible(False)
    ax.grid(False)
    ax.set_title("Where the project stands (share of each phase complete)", fontsize=10, loc="left")
    fig.tight_layout(); fig.savefig(FIG / "status.png", bbox_inches="tight"); plt.close(fig)


# ============================================================================ PDF
def styles():
    pdfmetrics.registerFont(TTFont("Arial", r"C:\Windows\Fonts\arial.ttf"))
    pdfmetrics.registerFont(TTFont("Arial-Bold", r"C:\Windows\Fonts\arialbd.ttf"))
    pdfmetrics.registerFont(TTFont("Arial-Italic", r"C:\Windows\Fonts\ariali.ttf"))
    pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold", italic="Arial-Italic", boldItalic="Arial-Bold")
    ss = getSampleStyleSheet()
    base = dict(fontName="Arial", textColor=colors.HexColor(INK))
    return {
        "title": ParagraphStyle("t", parent=ss["Title"], fontName="Arial-Bold", fontSize=24, leading=29, textColor=colors.HexColor(INK)),
        "sub": ParagraphStyle("s", parent=ss["Normal"], fontSize=13, leading=18, alignment=TA_CENTER, textColor=colors.HexColor(INK2), fontName="Arial"),
        "h1": ParagraphStyle("h1", parent=ss["Heading1"], fontName="Arial-Bold", fontSize=16, leading=20, spaceBefore=6, spaceAfter=8, textColor=colors.HexColor("#1c5cab")),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontName="Arial-Bold", fontSize=12, leading=15, spaceBefore=8, spaceAfter=4, textColor=colors.HexColor(INK)),
        "body": ParagraphStyle("b", parent=ss["BodyText"], fontSize=10, leading=14, spaceAfter=5, **base),
        "bullet": ParagraphStyle("bl", parent=ss["BodyText"], fontSize=10, leading=14, leftIndent=12, bulletIndent=2, spaceAfter=2, **base),
        "cap": ParagraphStyle("c", parent=ss["Italic"], fontName="Arial-Italic", fontSize=8.5, leading=11, textColor=colors.HexColor(INK2), spaceAfter=10),
        "cell": ParagraphStyle("cl", parent=ss["BodyText"], fontSize=8.5, leading=11, **base),
        "box": ParagraphStyle("bx", parent=ss["BodyText"], fontSize=10, leading=14, backColor=colors.HexColor("#eef4fd"),
                              borderColor=colors.HexColor(BLUE), borderWidth=0.8, borderPadding=7, spaceBefore=6, spaceAfter=12, **base),
    }


def build_pdf():
    S = styles()
    W = A4[0] - 4 * cm
    c2 = lambda s: s.replace("CO2", "CO<sub>2</sub>").replace("NO2", "NO<sub>2</sub>")

    def P(text, st="body"):
        return Paragraph(c2(text), S[st])

    def bullets(items):
        return [Paragraph(c2(t), S["bullet"], bulletText="•") for t in items]

    def img(path, width=W, cap=None):
        from reportlab.lib.utils import ImageReader
        iw, ih = ImageReader(str(path)).getSize()
        out = [Image(str(path), width=width, height=width * ih / iw)]
        if cap:
            out.append(P(cap, "cap"))
        return KeepTogether(out)

    def table(rows, widths, head=True):
        data = [[Paragraph(c2(str(c)), S["cell"]) for c in r] for r in rows]
        t = Table(data, colWidths=widths, repeatRows=1 if head else 0)
        st = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor(GRID)), ("VALIGN", (0, 0), (-1, -1), "TOP"),
              ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
        if head:
            st += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#cde2fb"))]
        t.setStyle(TableStyle(st))
        return t

    mc = json.loads((OUTPUTS / "phase1" / "mc_budget.json").read_text())["results"]["symmetric"]["co2_annual_mt_yr"]
    city = json.loads((OUTPUTS / "phase1" / "city_fit.json").read_text())["results"][0]
    E, ci, tau = city["emission"]["e_nox_kg_s"], city["bootstrap"]["e_nox_kg_s_ci95"], city["emission"]["tau_h"]

    story = []
    # ---------------------------------------------------------------- cover
    story += [Spacer(1, 3.2 * cm), P("EcoTrack", "title"),
              P("Satellite-based estimation of urban fossil-fuel CO2 emissions<br/>Shivajinagar → Talegaon Dabhade corridor, Pune", "sub"),
              Spacer(1, 0.8 * cm), P("Progress report: what has been done, what was found, and what comes next", "sub"),
              Spacer(1, 0.5 * cm), P("Janhavi Tupe · Final-year project · October 2026", "sub"), Spacer(1, 1.2 * cm),
              P(f"<b>Headline so far:</b> Pune + Pimpri-Chinchwad emit about <b>{mc[2]:.2f} million tonnes of fossil CO2 per year</b> "
                f"(annual mean; 95% range {mc[0]:.2f}–{mc[4]:.2f}), estimated from satellite NO2, CO and wind data. One of the two "
                "official inventories (EDGAR, 3.6) agrees; the other (ODIAC, 11.8) is ruled out.", "box"),
              PageBreak()]

    # ---------------------------------------------------------------- 1 problem
    story += [P("1. The problem and the idea", "h1"),
              P("Cities produce most fossil CO2, but the official numbers (emission <i>inventories</i>) are slow, coarse and often "
                "disagree. For Pune, two respected inventories differ by a factor of 3.2. Measuring CO2 directly from space is hard: "
                "Pune adds only ~0.1 ppm to a ~420 ppm background, far below the noise of today's CO2 satellites."),
              P("<b>The idea</b> (from the base paper, Xie et al. 2026): burning fuel releases CO2 <i>and</i> NO2. NO2 is easy to see "
                "from space (low background, lives only ~1–2 hours, measured daily by TROPOMI). So measure the city's NO2 emission, then "
                "convert it to CO2 with a CO2:NOx ratio. That ratio is the weak link, and the base paper's largest error term."),
              P("<b>Research question:</b> can combining several satellites (NO2 + CO + CO2), weather and human-activity data "
                "estimate urban CO2 better than relying on NO2 alone?"),
              img(FIG / "pipeline.png", cap="Figure 1. The whole workflow so far: data → Phase 1 emission estimate → checks → headline; "
                  "Phase 2 builds the 1 km feature table for the machine-learning phases."),
              PageBreak()]

    # ---------------------------------------------------------------- 2 study area & data
    story += [P("2. Study area and data", "h1"),
              P("A 33 km strip along the Old Mumbai–Pune Highway where factories (MIDC Bhosari, Chinchwad, Talegaon) and heavy traffic sit "
                "side by side. The corridor is the highway centreline ± 3.5 km plus Talegaon MIDC (269 km²), divided into 268 grid cells "
                "of 1 km and three clusters."),
              img(FIG / "study_area.png", width=W * 0.66, cap="Figure 2. The corridor, its 1 km grid coloured by cluster, the ten waypoints, the main "
                  "emission source found in Phase 1 (central Pune, just south of the corridor) and the second hotspot (Pimpri–Chinchwad)."),
              table([["Dataset", "What it measures", "Used for"],
                     ["TROPOMI (Sentinel-5P)", "NO2, CO, HCHO columns; daily, ~3.5 × 5.5 km", "Emissions, sector mix, chemistry proxy"],
                     ["OCO-3 / OCO-2 (NASA)", "Column CO2 (XCO2); 8 usable dates over Pune", "Direct CO2 check"],
                     ["ERA5 (ECMWF)", "Hourly wind, boundary layer, temperature, sunlight", "Moving the plumes; features"],
                     ["EDGAR, ODIAC", "Bottom-up emission inventories", "CO2:NOx prior, comparison (never truth)"],
                     ["VIIRS, Sentinel-2", "Night lights; NDVI/NDBI", "Human-activity features"],
                     ["OpenStreetMap / GRIP4", "Roads, places, industrial land", "Corridor geometry, road density"],
                     ["SRTM", "Ground height", "Terrain correction for CO"]],
                    [3.6 * cm, 6.8 * cm, W - 10.4 * cm]),
              PageBreak()]

    # ---------------------------------------------------------------- 3 feasibility
    story += [P("3. First: checking the data exist (feasibility, G1–G4)", "h1"),
              P("Before building anything, four go/no-go checks with pass rules set in advance:"),
              table([["Check", "Result", "Verdict"],
                     ["G2 TROPOMI coverage", "Median 26 usable days per month; worst month 13", "PASS"],
                     ["G3 NO2 signal", "All clusters 1.7–2.4× above clean background, every season", "PASS"],
                     ["G1 OCO-3 / OCO-2", "Pune is an OCO-3 'snapshot' target; 8 strong dates", "Case study only"],
                     ["G4 Waypoints", "6 of 10 were > 500 m off (Dehu Road 4.4 km); corridor rebuilt on the real highway", "FIXED"]],
                    [3.8 * cm, 9.2 * cm, W - 13 * cm]),
              Spacer(1, 8), img(FIG / "coverage.png", cap="Figure 3. Usable TROPOMI overpasses per month (5-season average). October is "
                                "weakest (late-monsoon cloud); every month clears the pass line comfortably."),
              PageBreak()]

    # ---------------------------------------------------------------- 4 phase 1 method
    story += [P("4. Phase 1: measuring the city's emissions from space", "h1"),
              P("<b>Step 1, find the source.</b> On calm days NO2 piles up over its source. The calm-day average peaks over central Pune "
                "(Swargate/Camp), just south of the corridor."),
              img(P1 / "calm_composite.png", width=W * 0.66, cap="Figure 4. Average NO2 on 187 calm days. Orange dot: the main source."),
              P("<b>Step 2, how much?</b> Each day's image is rotated so its wind points the same way, then averaged; summing across the "
                "wind gives the <i>line density</i>. A plume curve (EMG) is fitted, giving the NO2 in the plume and how far it travels "
                f"before decaying. Result: <b>{E:.3f} kg/s NOx</b> [95% CI {ci[0]:.3f}–{ci[2]:.3f}], lifetime <b>{tau:.2f} h</b>."),
              img(P1 / "line_density_main.png", cap="Figure 5. Line density (blue dots) and the fitted plume curve (orange), fitted up to 45 km "
                  "downwind. The grey band is excluded because a second source sits there (see section 6)."),
              PageBreak(),
              P("<b>Step 3, where exactly?</b> A second method (flux divergence) maps emission pixel by pixel: what flows out minus what "
                "flows in, plus what chemistry destroys. It finds two hotspots 16.7 km apart: central Pune and Pimpri–Chinchwad. "
                "<b>The corridor produces about 21% of the metro's NOx</b>, a share stable to ±2.4% in every test."),
              img(P1 / "divergence_map.png", width=W * 0.7, cap="Figure 6. Emission map from flux divergence. Red = emitting."),
              PageBreak()]

    # ---------------------------------------------------------------- 5 CO2
    story += [P("5. From NOx to CO2, and the inventories", "h1"),
              P("NOx is turned into CO2 with a CO2:NOx ratio. Inventories say it varies by sector from 115 (industry) to 393 (households), "
                "so the city's mix matters. <b>TROPOMI CO measures that mix:</b> CO does not decay, so downwind of the city it steps up "
                "and stays up. After removing the Western Ghats terrain imprint, the step gives a CO:NOx of <b>16.7</b>, close to the "
                "inventory's 16.0, and narrows the CO2:NOx ratio to <b>163 (148–180)</b>."),
              img(P1 / "co_step.png", cap="Figure 7. The CO 'step' over Pune: upwind plateau (left) to downwind plateau (right)."),
              P("<b>Uncertainty</b> was propagated with a Monte Carlo (200,000 simulations) through every step, and the satellite's "
                "busy midday window was converted to an annual mean with published hour-by-hour emission profiles."),
              img(P1 / "mc_budget.png", cap="Figure 8. Fossil CO2 for Pune + PCMC: median, 68% and 95% ranges. EDGAR (dashed) is inside; "
                  "ODIAC (11.8, off the chart) is far outside."),
              PageBreak(),
              P("<b>Can CO2 satellites confirm it?</b> Not yet: Pune's CO2 plume (~0.02–0.15 ppm) is 10–20× smaller than the noise and "
                "scan-stripe artefacts of OCO-3/OCO-2. The 8 snapshots are consistent with our estimate but only set an upper limit "
                "(about 7–14 Mt/yr). <b>So multi-satellite data help through CO, not through direct CO2.</b>"),
              img(P1 / "oco_dates_r10.png", cap="Figure 9. OCO soundings on the 8 dates (colour) vs the predicted Pune plume (contours). "
                  "The stripes are instrument artefacts larger than the plume."),
              PageBreak()]

    # ---------------------------------------------------------------- 6 validation & correction
    story += [P("6. Testing the method, and a correction it caught", "h1"),
              P("Every method was first run on <b>fake data with a known answer</b>: a simulated city on the real grid with real-like "
                "winds and noise. The plume fit recovers emissions within +12% (a measured, systematic bias kept in the uncertainty), "
                "flux divergence within −4%, the CO step within −1.4%."),
              P("A robustness test (letting the background slope) then changed the answer by 42%. Investigating showed the original fit "
                "reached 60 km downwind, where <b>PCMC and Talegaon add a second source</b> that the single-source model misread. "
                "Fitting only to 45 km fixed it: both background shapes agree, and NOx rose ~20%. Everything downstream was rerun, and one "
                "earlier conclusion that depended on the low value (\"more household burning than the inventory\") was withdrawn."),
              img(FIG / "d19.png", cap="Figure 10. City NOx by fit window and background shape. Inside 30–45 km the two agree (decision D19)."),
              P("<b>Does the method see real changes?</b> A model-free check (city minus rural NO2) for late March–May of each year:"),
              img(FIG / "covid.png", cap="Figure 11. The 2020 national lockdown (−74%) and the 2021 Maharashtra restrictions (−29%) are both "
                  "detected, in the right order, plus growth to 2024."),
              PageBreak()]

    # ---------------------------------------------------------------- 7 phase 2
    story += [P("7. Phase 2: the 1 km feature table", "h1"),
              P("For the machine-learning phases, every layer was put on the 1 km grid, one row per cell per month: 268 cells × 40 months = "
                "<b>10,720 rows, 17 features, 0 missing values</b> (feature table v2, frozen with a SHA-256 fingerprint). The features are "
                "NO2, CO, HCHO (a chemistry proxy), wind and weather, night lights, vegetation and built-up indices, road density and "
                "industrial-land fraction. Inventories are kept only as reference columns, never as inputs."),
              img(FIG / "cells.png", cap="Figure 12. Four features averaged over 40 months. NO2 is highest near Pune; night lights and roads "
                  "trace the urban core and PCMC; industrial land picks out MIDC Bhosari, Chinchwad and Talegaon MIDC."),
              P("<b>Roads and industry from OpenStreetMap.</b> The OpenStreetMap query servers were overloaded for days, so the whole "
                "western-India map file (221 MB, checksum-verified) was downloaded once and read locally in 2.5 minutes. It gives 36,082 roads "
                "and 223 industrial areas. A second published road map (GRIP4) agrees on major roads (rank correlation 0.84) but misses "
                "almost all local streets (0.07 vs 4.2 km per cell), so OpenStreetMap is the better source."),
              PageBreak(),
              P("<b>A check before any machine learning: which inputs can say <i>where</i>?</b> For each feature we measured how much of "
                "its variation is between cells rather than between months. Roads, industry, land cover and night lights vary in space; "
                "CO, HCHO and weather barely differ between 1 km cells. So at this scale the location of emissions must come from the "
                "activity layers (and partly NO2), while CO and weather help with timing. This is written down <i>before</i> training, and "
                "it is why the models will be tested on held-out map areas (spatial cross-validation)."),
              img(FIG / "spatial_share.png", cap="Figure 13. Share of each feature's variance that is spatial (between cells)."),
              img(OUTPUTS / "phase2" / "qa_correlation_v2.png", width=W * 0.72,
                  cap="Figure 14. Correlation between features. Only expected pairs are strongly related (minor vs total roads; "
                      "boundary layer, sunlight and temperature; two wind descriptors). Industrial land is nearly independent of everything."),
              PageBreak()]

    # ---------------------------------------------------------------- 8 decisions & lessons
    story += [P("8. Key decisions and lessons", "h1"),
              P("Twenty design decisions are recorded with their evidence (docs/decisions.md). The most important:"),
              table([["#", "Decision", "Why"],
                     ["D1/D10", "Measure the city total with the plume fit; split it by area with flux-divergence shares", "Waypoints are closer than one satellite pixel; shares are robust"],
                     ["D9", "Corridor built on the real highway + Talegaon MIDC", "Proposal waypoints up to 4.4 km off"],
                     ["D11", "OCO used as an upper limit, not a measurement", "Pune's CO2 plume is below detection"],
                     ["D12", "CO2:NOx ratio constrained by TROPOMI CO", "Largest error term; CO reveals the sector mix"],
                     ["D13", "Outlier filter: each pixel vs its own history", "Other filters clipped the plume or removed 29% of data"],
                     ["D17/D18", "Annual-mean conversion; Monte Carlo uncertainty", "Like-for-like comparison; honest ranges"],
                     ["D19", "Fit only to 45 km downwind, sloped background", "A second source biased NOx ~20% low"],
                     ["D14/D15/D20", "HCHO as chemistry proxy; 1 km UTM grid; OSM roads via a bulk file (GRIP4 as fallback and cross-check)", "Data availability and quality"]],
                    [2.5 * cm, 7.4 * cm, W - 9.9 * cm]),
              Spacer(1, 10), P("<b>Lessons that shaped the work</b>", "h2")]
    story += bullets(["Test every method on fake data with a known answer before trusting it, and use realistic conditions (Pune's real winds).",
                      "Check outputs against physics: 439 'overpasses' in a month, 29% 'outliers' or a 2.6× unit mismatch were all bugs.",
                      "When a method is fixed, rerun everything downstream and re-check every conclusion.",
                      "Report null results honestly: OCO's non-detection is a finding, not a failure.",
                      "When a server is the bottleneck, look for a bulk download of the same data (OpenStreetMap: days of failures vs 2.5 minutes).",
                      "Write everything down: a research log, a decision record and a findings document were kept throughout."])
    story += [PageBreak()]

    # ---------------------------------------------------------------- 9 status & next
    story += [P("9. Where the project stands, and what comes next", "h1"),
              img(FIG / "status.png", cap="Figure 15. Progress by phase."),
              P("<b>Next steps</b>", "h2")]
    story += bullets(["<b>Guide review and sign-off</b> of the open decisions: OCO's role (D8/D11), the CO-constrained ratio (D12), "
                      "the fit-window correction (D19) and the Phase 3 label design (D16).",
                      "<b>Phase 3, labels:</b> CO2 per cell and season = city total × flux-divergence share; test a CO-based label "
                      "that is independent of NO2, so the experiments are not circular.",
                      "<b>Phases 4–6, machine learning:</b> train tree models for Experiments A–D (NO2 only → + CO → + weather → + "
                      "human activity), with spatial-block cross-validation and an ablation, to measure what each data source adds.",
                      "<b>Phase 7–8:</b> validation maps, final uncertainty, and the final report."])
    story += [Spacer(1, 10),
              P("<b>Questions for the guide:</b> (1) Is the seasonal flux-divergence label acceptable, given its link to NO2 is stated? "
                "(2) Should the CO-based label become a second label? (3) Is seasonal resolution (1,340 labelled samples) enough? "
                "(4) Should Experiment B be redefined around TROPOMI CO, since OCO cannot be a per-cell feature?", "box"),
              P("Full detail: docs/phase1_report.md, docs/findings.md, docs/decisions.md, docs/phase3_design.md, and the learning guide in docs/guide/.", "cap")]

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Arial", 8); canvas.setFillColor(colors.HexColor(INK2))
        canvas.drawString(2 * cm, 1.2 * cm, "EcoTrack — progress report")
        canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"{doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(str(PDF), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                            title="EcoTrack progress report", author="Janhavi Tupe")
    doc.build(story, onLaterPages=footer)
    print(f"Saved {PDF}")


def run():
    FIG.mkdir(parents=True, exist_ok=True)
    for f in (fig_pipeline, fig_study_area, fig_coverage, fig_covid, fig_d19, fig_cells, fig_spatial_share, fig_status):
        f()
    build_pdf()


if __name__ == "__main__":
    run()
