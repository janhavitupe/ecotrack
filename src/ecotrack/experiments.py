"""
Phases 5–6 — the ML experiments, run exactly as frozen in docs/phase5_analysis_plan.md.

Descriptive runs
  Experiments  A (NO2) → B (+CO) → C (+weather, HCHO) → D (+human activity), on L-fd and L-co
  Controls     N0 geography-only null; N1 D's features shuffled; residual ("beyond geography") target;
               feature-group ablation of D
  Splits       15 km block folds (+ 10/20 km), corridor transfer, PCMC hold-out, leave-one-season-out
  Models       Random Forest (primary); ridge and XGBoost (robustness)

Primary hypotheses H1–H4: GROUP PERMUTATION TESTS (plan §3.1, §7)
  "Does feature group G add predictive skill to model M?"
  - fit M + G with the real G values -> out-of-fold score s_obs
  - refit R times with G's rows shuffled in the training data (same columns, same model, same splits)
    -> s_1 … s_R
  - effect = s_obs - mean(s_r); one-sided p = (1 + #{s_r >= s_obs}) / (R + 1); significant if p <= 0.05
  Why not simply compare two experiments with a bootstrap: on pure-noise labels that rule flagged 7 of 9
  contrasts as significant. Models with different inputs differ in how much their predictions wobble,
  and a test-set bootstrap measures that systematic difference very precisely (research log 2026-10-10).
  In a permutation test both arms have identical inputs and the refits carry the training randomness.
  Geography (distance to source, x, y) is in every hypothesis model, so each test asks whether G adds
  skill beyond location.

Before running, the input model table's SHA-256 is checked against the plan, and the plan must say FROZEN.
  --smoke        noise labels, tiny models: tests the code end to end, reveals nothing
  --calibrate N  noise labels, real settings: false-positive rate of the H1–H4 permutation tests

Output: outputs/phase5/results.json, oof_predictions.csv, figures/

Usage:
    python -m ecotrack.experiments              # the real run (after the frozen plan is committed)
    python -m ecotrack.experiments --smoke
    python -m ecotrack.experiments --calibrate 5
"""

import argparse
import hashlib
import itertools
import json
import re
import time
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from sklearn.ensemble import RandomForestRegressor
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from ecotrack.config import OUTPUTS, ROOT
from ecotrack.inversion.run_city import BLUE, GRID, INK, INK2, ORANGE, SURFACE
from ecotrack.tensor import block_folds

warnings.filterwarnings("ignore", message=".*sklearn.utils.parallel.delayed.*")  # harmless; floods the logs

TABLE = ROOT / "data" / "processed" / "model_table_v1_region.csv"
PLAN = ROOT / "docs" / "phase5_analysis_plan.md"
OUT = OUTPUTS / "phase5"
SEED = 42
R_PRIMARY, R_ROBUST, R_CALIBRATE = 99, 9, 19

GEO = ["dist_to_source_km", "x_utm", "y_utm"]
WEATHER = ["ws850", "wd850_sin", "wd850_cos", "blh_m", "frac_ese", "t2m_k", "ssrd_j_m2", "hcho"]
ACTIVITY = ["viirs_rad", "ndvi", "ndbi", "road_major_km", "road_mid_km", "road_minor_km", "road_total_km", "industrial_frac"]
SETS = {"A": ["no2"], "B": ["no2", "co_norm"], "C": ["no2", "co_norm"] + WEATHER,
        "D": ["no2", "co_norm"] + WEATHER + ACTIVITY, "N0": GEO}
GROUPS = {"NO2": ["no2"], "CO": ["co_norm"], "weather+HCHO": WEATHER, "night lights": ["viirs_rad"],
          "land cover": ["ndvi", "ndbi"], "roads": ["road_major_km", "road_mid_km", "road_minor_km", "road_total_km"],
          "industrial land": ["industrial_frac"]}
CEILING = {("label_fd", "all"): 0.99, ("label_fd", "corridor"): 0.97, ("label_co", "all"): 0.78, ("label_co", "corridor"): 0.75}

# Primary hypotheses (plan §3.1): base features + tested group, label, split, score, scored rows, target
HYPOTHESES = {
    "H1 activity layers add spatial skill (L-fd)": dict(
        label="label_fd", scheme="blocks15", base=GEO + SETS["C"], group=ACTIVITY, score="spatial_r2", rows="all",
        perm="spin"),
    "H2a CO adds spatial skill (L-fd)": dict(
        label="label_fd", scheme="blocks15", base=GEO + ["no2"], group=["co_norm"], score="spatial_r2", rows="all",
        perm="spin"),
    "H2b CO adds temporal skill (L-fd)": dict(
        label="label_fd", scheme="loso", base=GEO + ["no2"], group=["co_norm"], score="temporal_r2", rows="all",
        perm="seasons"),
    "H3 all features predict beyond geography (L-fd residual)": dict(
        label="label_fd", scheme="blocks15", base=[], group=SETS["D"], score="r2", rows="all", residual=True,
        perm="spin"),
    "H4 NO2 locates emissions in the CO label (L-co, corridor)": dict(
        label="label_co", scheme="blocks15", base=GEO, group=["no2"], score="spatial_r2", rows="corridor",
        perm="spin"),
}


def feature_set(name, label):
    """Plan §3: on L-co, co_norm is removed and B is undefined."""
    if label == "label_co" and name == "B":
        return None
    base = SETS["D"] if name == "N1" else SETS[name]
    return [f for f in base if not (label == "label_co" and f == "co_norm")]


# ============================================================================ models
def make_model(kind, smoke):
    if kind == "rf":
        return RandomForestRegressor(n_estimators=20 if smoke else 500, min_samples_leaf=5, max_features=0.5,
                                     random_state=SEED, n_jobs=-1)
    if kind == "xgb":
        return XGBRegressor(n_estimators=20 if smoke else 400, max_depth=4, learning_rate=0.05, subsample=0.8,
                            colsample_bytree=0.8, random_state=SEED, n_jobs=-1)
    raise ValueError(kind)


def fit_predict(kind, Xtr, ytr, Xte, groups_tr, smoke):
    if kind == "ridge":
        n_groups = len(np.unique(groups_tr)) if groups_tr is not None else 0
        cv = list(GroupKFold(n_splits=min(5, n_groups)).split(Xtr, ytr, groups_tr)) if n_groups >= 2 else 5
        model = make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-3, 4, 30), cv=cv))
    else:
        model = make_pipeline(StandardScaler(), make_model(kind, smoke))
    model.fit(Xtr, ytr)
    return model.predict(Xte)


# ============================================================================ splits and targets
def splits(tab, scheme):
    """List of (fold name, train mask, test mask)."""
    if scheme.startswith("blocks"):
        km = int(scheme[6:])
        fold = tab.fold_block.to_numpy() if km == 15 else block_folds(tab, km, 5, SEED)[1].to_numpy()
        return [(f"fold{f}", fold != f, fold == f) for f in range(5)]
    if scheme == "corridor":
        return [("corridor", (tab.split_corridor == "train").to_numpy(), (tab.split_corridor == "test").to_numpy())]
    if scheme == "pcmc":
        return [("pcmc", (tab.split_pcmc == "train").to_numpy(), (tab.split_pcmc == "test").to_numpy())]
    if scheme == "loso":
        return [(s, (tab.season != s).to_numpy(), (tab.season == s).to_numpy()) for s in sorted(tab.season.unique())]
    raise ValueError(scheme)


def residual_target(y, dist, train):
    """Plan §3: subtract a decreasing isotonic fit of label vs distance, fitted on training rows only."""
    iso = IsotonicRegression(increasing=False, out_of_bounds="clip").fit(dist[train], y[train])
    return y - iso.predict(dist)


def oof(tab, label, feats, scheme, kind, smoke, residual=False, shuffle_cols=None, perm_seed=None, X=None):
    """Pooled out-of-fold predictions and targets. `shuffle_cols`: column indices whose training rows are
    permuted together (N1 and the permutation tests); test rows keep their real values. `X`: a ready
    feature matrix (used by the season permutation)."""
    X = tab[feats].to_numpy(float) if X is None else X
    y = tab[label].to_numpy(float)
    pred, target = np.full(len(tab), np.nan), np.full(len(tab), np.nan)
    rng = np.random.default_rng(perm_seed)
    for _, tr, te in splits(tab, scheme):
        yy = residual_target(y, tab.dist_to_source_km.to_numpy(), tr) if residual else y
        Xtr = X[tr].copy()
        if shuffle_cols is not None and len(shuffle_cols):
            Xtr[:, shuffle_cols] = Xtr[rng.permutation(len(Xtr))][:, shuffle_cols]
        pred[te] = fit_predict(kind, Xtr, yy[tr], X[te], tab.block_id.to_numpy()[tr], smoke)
        target[te] = yy[te]
    return pred, target


# ============================================================================ metrics
def r2(y, p):
    ok = np.isfinite(y) & np.isfinite(p)
    y, p = y[ok], p[ok]
    return float(1 - np.sum((y - p) ** 2) / np.sum((y - y.mean()) ** 2)) if len(y) > 2 else np.nan


def scores(cells, y, p):
    ok = np.isfinite(p) & np.isfinite(y)
    d = pd.DataFrame({"cell": np.asarray(cells)[ok], "y": y[ok], "p": p[ok]})
    cm = d.groupby("cell")[["y", "p"]].mean()
    anom = d[["y", "p"]] - d.groupby("cell")[["y", "p"]].transform("mean")
    return {"r2": r2(d.y.to_numpy(), d.p.to_numpy()), "rmse": float(np.sqrt(np.mean((d.y - d.p) ** 2))),
            "mae": float(np.mean(np.abs(d.y - d.p))), "spatial_r2": r2(cm.y.to_numpy(), cm.p.to_numpy()),
            "temporal_r2": r2(anom.y.to_numpy(), anom.p.to_numpy()), "n_rows": int(ok.sum())}


def row_mask(tab, rows):
    if rows == "all":
        return np.ones(len(tab), bool)
    if rows == "corridor":
        return tab.in_corridor.to_numpy(bool)
    if rows == "without_fold3":
        return (tab.fold_block != 3).to_numpy()
    raise ValueError(rows)


# ============================================================================ spatial null: rotations
def spin_maps(tab, n, seed=SEED):
    """n rotation/reflection maps about the emission source (the regional grid is a 30 km disk around it).
    Map k sends each cell to the grid cell nearest its rotated position; transforms alternate plain
    rotations and mirror-then-rotate, at angles spread over 20-340 deg (near-identity excluded).
    A rotated feature map keeps its smoothness and its rings around the city; only its directions
    (e.g. the PCMC lobe to the north-west) stop lining up with the label. Corridor cells beyond 30 km
    (the Talegaon end) rotate off the grid and take the nearest grid cell: a small edge distortion."""
    cells = tab.drop_duplicates("cell_id")[["cell_id", "x_utm", "y_utm", "dist_to_source_km"]].reset_index(drop=True)
    xy = cells[["x_utm", "y_utm"]].to_numpy()
    # source position: the point whose distances best match dist_to_source_km (least squares)
    d = cells.dist_to_source_km.to_numpy() * 1000
    A = np.column_stack([2 * xy[:, 0], 2 * xy[:, 1], -np.ones(len(xy))])
    b = (xy ** 2).sum(1) - d ** 2
    sx, sy, _ = np.linalg.lstsq(A, b, rcond=None)[0]
    rel = xy - [sx, sy]
    tree = cKDTree(xy)
    rng = np.random.default_rng(seed)
    angles = np.linspace(20, 340, n) + rng.uniform(-5, 5, n)
    maps = []
    for k, a in enumerate(np.radians(angles)):
        r = rel * [-1, 1] if k % 2 else rel  # odd k: mirror (east <-> west) first
        rot = np.column_stack([r[:, 0] * np.cos(a) - r[:, 1] * np.sin(a), r[:, 0] * np.sin(a) + r[:, 1] * np.cos(a)])
        _, j = tree.query(rot + [sx, sy])
        maps.append(dict(zip(cells.cell_id, cells.cell_id.to_numpy()[j])))
    return maps


# ============================================================================ permutation test
def perm_test(tab, h, n_perm, kind="rf", smoke=False, scheme=None, rows=None, seed=SEED):
    """Group permutation test (module docstring). Returns the observed score, the permuted scores,
    the effect and the one-sided p-value."""
    scheme = scheme or h["scheme"]
    rows = rows or h["rows"]
    feats = h["base"] + h["group"]
    cols = list(range(len(h["base"]), len(feats)))
    m = row_mask(tab, rows)
    cells = tab.cell_id.to_numpy()[m]

    def score(perm_seed=None):
        p, y = oof(tab, h["label"], feats, scheme, kind, smoke, h.get("residual", False),
                   shuffle_cols=cols if perm_seed is not None else None, perm_seed=perm_seed)
        return scores(cells, y[m], p[m])[h["score"]], p

    lookup = tab.set_index(["cell_id", "season"])[h["group"]]

    def score_mapped(src_cells, src_seasons):
        """Structured null: every row takes the group's values from (src_cell, src_season), for training
        and test rows alike, so the group's maps stay realistic and only their alignment with the label
        is broken. Seasons: CO's seasonal structure is kept (row shuffling destroyed it and biased the
        temporal test). Spin: smoothness is kept (row shuffling made unrelated smooth maps look
        informative: 8 false alarms in 12 tests on smooth null labels). Research log 2026-10-10."""
        X = tab[feats].to_numpy(float, copy=True)  # writable: pandas may return a read-only view
        X[:, cols] = lookup.loc[pd.MultiIndex.from_arrays([src_cells, src_seasons])].to_numpy(float)
        p, y = oof(tab, h["label"], feats, scheme, kind, smoke, h.get("residual", False), X=X)
        return scores(cells, y[m], p[m])[h["score"]]

    def score_seasons(order):
        seasons = sorted(tab.season.unique())
        return score_mapped(tab.cell_id.to_numpy(), tab.season.map(dict(zip(seasons, order))).to_numpy())

    obs, p_obs = score()
    if h.get("perm") == "spin":
        null = [score_mapped(tab.cell_id.map(mp).to_numpy(), tab.season.to_numpy()) for mp in spin_maps(tab, n_perm, seed)]
    elif h.get("perm") == "seasons":
        seasons = sorted(tab.season.unique())
        orders = [o for o in itertools.permutations(seasons) if list(o) != seasons]  # 119 for 5 seasons
        if n_perm < min(len(orders), R_PRIMARY):  # primary run: all 119 orders (plan §7); calibration/robustness: a random subset
            rng = np.random.default_rng(seed)
            orders = [orders[i] for i in rng.choice(len(orders), n_perm, replace=False)]
        null = [score_seasons(o) for o in orders]
        n_perm = len(null)
    else:
        null = [score(seed + 1000 + r)[0] for r in range(n_perm)]
    k = int(np.sum(np.array(null) >= obs))
    return {"observed": obs, "null_mean": float(np.mean(null)), "null_sd": float(np.std(null)),
            "null_max": float(np.max(null)), "effect": float(obs - np.mean(null)),
            "p_value": (1 + k) / (n_perm + 1), "significant": bool((1 + k) / (n_perm + 1) <= 0.05),
            "n_perm": n_perm, "model": kind, "scheme": scheme, "rows": rows}, p_obs


# ============================================================================ checks
def check_inputs(smoke):
    sha = hashlib.sha256(TABLE.read_bytes()).hexdigest()
    plan = PLAN.read_text(encoding="utf-8")
    if sha not in plan:
        raise SystemExit(f"Model table SHA-256 {sha[:12]}… is not the one frozen in the plan: stop.")
    if not smoke and not re.search(r"\*\*Status:\*\* \*\*FROZEN", plan):
        raise SystemExit("The analysis plan is not marked FROZEN: stop.")
    return sha


def noise_labels(tab, seed, smooth_km=0.0):
    """Null labels unrelated to every feature. smooth_km = 0: independent noise per row.
    smooth_km > 0: a smooth random map (Gaussian-weighted white noise, sigma = smooth_km), the same in
    every season plus 10% independent noise: as smooth as the real labels, but meaningless."""
    rng = np.random.default_rng(seed)
    for c in ("label_fd", "label_co"):
        if smooth_km <= 0:
            tab[c] = rng.normal(size=len(tab))
            continue
        cells = tab.drop_duplicates("cell_id")[["cell_id", "x_utm", "y_utm"]].reset_index(drop=True)
        xy = cells[["x_utm", "y_utm"]].to_numpy() / 1000
        w = rng.normal(size=len(cells))
        d2 = ((xy[:, None, :] - xy[None, :, :]) ** 2).sum(-1)
        field = np.exp(-d2 / (2 * smooth_km ** 2)) @ w
        field = (field - field.mean()) / field.std()
        tab[c] = tab.cell_id.map(dict(zip(cells.cell_id, field))).to_numpy() + 0.1 * rng.normal(size=len(tab))
    return tab


# ============================================================================ calibration
def calibrate(n_seeds, smooth_km=0.0, only=None):
    """False-positive rate of the H1–H4 permutation tests on null labels, real model settings.
    smooth_km > 0 uses smooth random maps (as smooth as the real labels); `only` restricts the tests."""
    tab0 = pd.read_csv(TABLE)
    rows, t0 = [], time.time()
    for seed in range(1, n_seeds + 1):
        tab = noise_labels(tab0.copy(), seed, smooth_km)
        for name, h in HYPOTHESES.items():
            if only and not any(name.startswith(o + " ") for o in only):
                continue
            r, _ = perm_test(tab, h, R_CALIBRATE, seed=seed * 100)
            rows.append({"seed": seed, "hypothesis": name, **{k: r[k] for k in ("observed", "effect", "p_value", "significant")}})
            print(f"  seed {seed}  {name[:44]:44s} effect {r['effect']:+.4f}  p {r['p_value']:.2f}  "
                  f"{'FALSE ALARM' if r['significant'] else 'ok'}   ({(time.time() - t0) / 60:.0f} min)", flush=True)
    n_fp = sum(r["significant"] for r in rows)
    summary = {"n_tests": len(rows), "false_alarms": n_fp, "rate": n_fp / len(rows), "expected_rate": 0.05,
               "n_perm": R_CALIBRATE, "model": "rf (real settings)",
               "null_labels": f"smooth {smooth_km:g} km" if smooth_km else "independent noise",
               "tests": only or "all", "runs": rows}
    OUT.mkdir(parents=True, exist_ok=True)
    tag = (f"_smooth{smooth_km:g}km" if smooth_km else "") + ("_" + "_".join(only) if only else "")
    (OUT / f"permutation_test_calibration{tag}.json").write_text(json.dumps(summary, indent=2, default=float))
    print(f"False alarms on noise labels: {n_fp} of {len(rows)} ({100 * n_fp / len(rows):.0f}%; expected ~5%)")


# ============================================================================ the real run
def run(smoke=False):
    sha = check_inputs(smoke)
    tab = pd.read_csv(TABLE)
    if smoke:
        tab = noise_labels(tab, 0)
    out = OUT / "smoke" if smoke else OUT
    (out / "figures").mkdir(parents=True, exist_ok=True)
    n_primary, n_robust = (3, 2) if smoke else (R_PRIMARY, R_ROBUST)
    corridor = tab.in_corridor.to_numpy(bool)
    res = {"input_sha256": sha, "smoke": smoke, "descriptive": {}, "primary": {}, "robustness": {}, "ablation": {}}
    oof_cols = {}
    t0 = time.time()

    # ---- 1. primary hypotheses (the only significance claims)
    print("PRIMARY HYPOTHESES (group permutation tests, Random Forest)")
    for name, h in HYPOTHESES.items():
        r, _ = perm_test(tab, h, n_primary, smoke=smoke)
        res["primary"][name] = r
        print(f"  {name:58s} effect {r['effect']:+.4f}  p {r['p_value']:.3f}  "
              f"{'SIGNIFICANT' if r['significant'] else 'no detectable effect'}  ({(time.time() - t0) / 60:.0f} min)", flush=True)

    # ---- 2. robustness of each primary: same sign of the effect with ridge, XGBoost, 10/20 km blocks, without fold 3
    print("ROBUSTNESS (sign of the effect)")
    for name, h in HYPOTHESES.items():
        variants = [("ridge", None, None), ("xgb", None, None)]
        if h["scheme"] == "blocks15":
            variants += [("rf", "blocks10", None), ("rf", "blocks20", None)]
            if h["rows"] == "all":
                variants += [("rf", None, "without_fold3")]
        for kind, scheme, rows in variants:
            r, _ = perm_test(tab, h, n_robust, kind=kind, smoke=smoke, scheme=scheme, rows=rows)
            key = f"{name} | {kind}{' ' + scheme if scheme else ''}{' ' + rows if rows else ''}"
            res["robustness"][key] = r
            same = np.sign(r["effect"]) == np.sign(res["primary"][name]["effect"])
            print(f"  {key[:75]:75s} effect {r['effect']:+.4f}  {'same sign' if same else 'SIGN FLIPS'}", flush=True)

    # ---- 3. descriptive: every experiment and control on every split (point estimates, no significance)
    print("DESCRIPTIVE RUNS (Random Forest)")
    sets_for = {"label_fd": ["N0", "N1", "A", "B", "C", "D"], "label_co": ["N0", "N1", "A", "C", "D"]}
    for label, names in sets_for.items():
        schemes = ["blocks15", "corridor", "pcmc"] + (["loso"] if label == "label_fd" else [])
        for scheme in schemes:
            for s in names:
                feats = feature_set(s, label)
                p, y = oof(tab, label, feats, scheme, "rf", smoke,
                           shuffle_cols=list(range(len(feats))) if s == "N1" else None, perm_seed=SEED)
                ok = np.isfinite(p)
                entry = {"all": scores(tab.cell_id.to_numpy(), y, p),
                         "corridor": scores(tab.cell_id.to_numpy()[corridor], y[corridor], p[corridor])}
                for dom in ("all", "corridor"):
                    entry[dom]["ceiling_normalised_r2"] = entry[dom]["r2"] / CEILING[(label, dom)]
                if scheme == "blocks15":
                    entry["per_fold"] = {f"fold{f}": scores(tab.cell_id.to_numpy()[(tab.fold_block == f).to_numpy()],
                                                            y[(tab.fold_block == f).to_numpy()], p[(tab.fold_block == f).to_numpy()])
                                         for f in range(5)}
                    oof_cols[f"{label}|{s}"] = p
                res["descriptive"][f"{label}|{scheme}|{s}"] = entry
                print(f"  {label}|{scheme}|{s:3s}  R2 {entry['all']['r2']:.3f}  spatial {entry['all']['spatial_r2']:.3f}  "
                      f"temporal {entry['all']['temporal_r2']:.3f}  corridor R2 {entry['corridor']['r2']:.3f}  ({ok.sum()} rows)", flush=True)
    for s in ("N0", "A", "B", "C", "D"):  # residual ("beyond geography") target, descriptive
        for scheme in ("blocks15", "pcmc"):
            p, y = oof(tab, "label_fd", feature_set(s, "label_fd"), scheme, "rf", smoke, residual=True)
            res["descriptive"][f"label_fd|{scheme}|{s}|residual"] = {"all": scores(tab.cell_id.to_numpy(), y, p)}

    # ---- 4. feature-group ablation of D (descriptive)
    print("ABLATION (D minus one group; 15 km blocks)")
    for label in ("label_fd", "label_co"):
        full = res["descriptive"][f"{label}|blocks15|D"]["all"]["r2"]
        for g, cols in GROUPS.items():
            if label == "label_co" and g == "CO":
                continue
            feats = [f for f in feature_set("D", label) if f not in cols]
            p, y = oof(tab, label, feats, "blocks15", "rf", smoke)
            res["ablation"][f"{label}|minus {g}"] = {"r2": r2(y, p), "drop_vs_D": full - r2(y, p)}
        print("  " + label + ": " + ", ".join(f"{k.split('minus ')[1]} {v['drop_vs_D']:+.3f}"
                                              for k, v in res["ablation"].items() if k.startswith(label)), flush=True)

    res["runtime_min"] = (time.time() - t0) / 60
    (out / "results.json").write_text(json.dumps(res, indent=2, default=float))
    pd.DataFrame({"cell_id": tab.cell_id, "season": tab.season, **oof_cols}).to_csv(out / "oof_predictions.csv", index=False)
    figures(res, out)
    print(f"Saved {out / 'results.json'} ({res['runtime_min']:.0f} min)")
    return res


def figures(res, out):
    plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "font.size": 9})
    for label, names in (("label_fd", ["N0", "N1", "A", "B", "C", "D"]), ("label_co", ["N0", "N1", "A", "C", "D"])):
        fig, ax = plt.subplots(figsize=(7, 3.2))
        x = np.arange(len(names))
        for j, (dom, col) in enumerate((("all", BLUE), ("corridor", ORANGE))):
            vals = [res["descriptive"][f"{label}|blocks15|{n}"][dom]["spatial_r2"] for n in names]
            ax.bar(x + (j - 0.5) * 0.36, vals, 0.34, color=col, label="all held-out cells" if dom == "all" else "corridor cells")
        ax.set_xticks(x, names); ax.set_ylabel("Spatial skill (R² of cell means)")
        ax.axhline(0, color=INK2, lw=0.8); ax.grid(axis="y", color=GRID); ax.spines[["top", "right"]].set_visible(False)
        ax.legend(frameon=False, fontsize=8)
        ax.set_title(f"{'L-fd (NO₂ label)' if label == 'label_fd' else 'L-co (CO label)'}: 15 km block cross-validation, Random Forest",
                     fontsize=10, loc="left", color=INK)
        fig.tight_layout(); fig.savefig(out / "figures" / f"skill_{label}.png", dpi=200); plt.close(fig)


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--smoke", action="store_true")
    a.add_argument("--calibrate", type=int, default=0, help="noise-label seeds for the false-positive check")
    a.add_argument("--smooth-km", type=float, default=0.0, help="calibrate with smooth random null maps")
    a.add_argument("--only", nargs="*", help="calibrate only these tests, e.g. H2b, or H1 H2a H3 H4")
    args = a.parse_args()
    if args.calibrate:
        calibrate(args.calibrate, args.smooth_km, args.only)
    else:
        run(smoke=args.smoke)
