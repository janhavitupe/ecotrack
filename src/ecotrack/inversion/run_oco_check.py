"""
D8 (exploratory, pending guide approval) — independent check of the NO2-derived CO2 with OCO-3/OCO-2.

Plume-model scaling (cf. Nassar et al. 2017 for OCO-2 power-plant plumes):
1. Emission prior: the flux-divergence NOx map (positive part, within 25 km of the source) scaled
   to CO2 so it sums to the Phase 1 satellite estimate E_pred (NO2 x EDGAR ratio).
2. Forward model: each 1 km emitting cell gives a steady-state Gaussian column plume carried by
   that day's ERA5 850 hPa wind (no loss: CO2 is inert on these scales):
       dM(d, y) = E_c / (w * sqrt(2 pi) * s(d)) * exp(-y^2 / (2 s(d)^2)),   d > 0 downwind
       s(d) = sqrt(s0^2 + (k d)^2)
   converted to a column-average mole fraction with the ERA5 surface pressure.
3. Per date, weighted regression  XCO2_i = b0 + bx*x_i + by*y_i + beta * pred_i  (weights 1/unc^2).
   beta = 1 means OCO sees exactly the predicted plume; beta * E_pred is OCO's emission estimate,
   INDEPENDENT of EDGAR's CO2:NOx ratio. Dates are combined by inverse-variance weighting.

Outputs: outputs/phase1/oco_check.json, figures/oco_*.png

Usage:
    python -m ecotrack.inversion.run_oco_check
"""

import json

import ee
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.ndimage import uniform_filter

from ecotrack.acquire.ee_utils import init_ee
from ecotrack.config import DATA_INTERIM
from ecotrack.inversion.emg import KM_PER_DEG_LAT, KM_PER_DEG_LON_EQ, rotate
from ecotrack.inversion.run_city import BLUE, FIG, GRID, INK, INK2, ORANGE, OUT, SEQ, SURFACE

DATES = {"oco3": ["2019-10-14", "2020-04-21", "2020-12-20", "2020-12-24", "2021-01-01", "2022-01-27", "2022-11-21"],
         "oco2": ["2024-01-23"]}
PRIOR_RADIUS_KM = 25
FIT_RADIUS_KM = 45          # soundings used in the regression
SIGMA0_KM, K_SPREAD = 2.0, 0.15
G, M_AIR, M_CO2 = 9.80665, 0.0289644, 0.0440095


def era5_at(times_utc, lat, lon):
    """ERA5 850 hPa + 100 m wind and surface pressure at the nearest hour, at one point."""
    pt = ee.Geometry.Point([lon, lat])
    out = []
    for t in times_utc:
        idx = t.round("h").strftime("%Y%m%dT%H")
        img = ee.ImageCollection("ECMWF/ERA5/HOURLY").filter(ee.Filter.eq("system:index", idx)).first()
        vals = img.select(["u_component_of_wind_850hPa", "v_component_of_wind_850hPa",
                           "u_component_of_wind_100m", "v_component_of_wind_100m", "surface_pressure",
                           "boundary_layer_height"]).reduceRegion(ee.Reducer.first(), pt, 27830).getInfo()
        out.append(vals)
    return out


def emission_prior(src, e_pred_kg_s, radius_km=PRIOR_RADIUS_KM):
    """Positive, smoothed flux-divergence map within PRIOR_RADIUS_KM, scaled to e_pred (kg CO2/s)."""
    d = np.load(OUT / "divergence_map.npz")
    lat, lon = d["lat"], d["lon"]
    e = np.clip(uniform_filter(np.nan_to_num(d["e_nox_mol_m2_s"]), size=3), 0, None)
    lon2d, lat2d = np.meshgrid(lon, lat)
    dx = (lon2d - src[1]) * KM_PER_DEG_LON_EQ * np.cos(np.radians(src[0]))
    dy = (lat2d - src[0]) * KM_PER_DEG_LAT
    e[np.hypot(dx, dy) > radius_km] = 0
    keep = e > 0
    w = e[keep] / e[keep].sum()
    return dx[keep], dy[keep], w * e_pred_kg_s


def predict_ppm(sx, sy, cx, cy, ce, u, v, psurf):
    """Predicted XCO2 enhancement (ppm) at soundings (sx, sy km) from cells (cx, cy km, ce kg/s)."""
    w = np.hypot(u, v)
    along, across = rotate(sx[:, None] - cx[None, :], sy[:, None] - cy[None, :], u, v)
    d_m = np.clip(along, 0, None) * 1000
    s_m = np.sqrt(SIGMA0_KM**2 + (K_SPREAD * np.clip(along, 0, None)) ** 2) * 1000
    dm = np.where(along > 0, ce[None, :] / (w * np.sqrt(2 * np.pi) * s_m) * np.exp(-0.5 * (across * 1000 / s_m) ** 2), 0)
    col_kg_m2 = dm.sum(axis=1)
    air_mol_m2 = psurf / (G * M_AIR)
    return col_kg_m2 / M_CO2 / air_mol_m2 * 1e6, d_m


def fit_date(g, pred):
    X = np.column_stack([np.ones(len(g)), g.x, g.y, pred])
    wts = 1 / g.xco2_uncertainty.to_numpy() ** 2
    Xw = X * np.sqrt(wts)[:, None]
    yw = g.xco2.to_numpy() * np.sqrt(wts)
    coef, *_ = np.linalg.lstsq(Xw, yw, rcond=None)
    resid = g.xco2.to_numpy() - X @ coef
    # Scale the covariance by the reduced chi-square so over-dispersed scatter widens the error bar
    chi2 = np.sum(wts * resid**2) / max(len(g) - X.shape[1], 1)
    cov = np.linalg.inv(Xw.T @ Xw) * max(chi2, 1.0)
    return coef, np.sqrt(np.diag(cov)), float(np.sqrt(np.mean(resid**2))), float(chi2)


def run(prior_radius_km=PRIOR_RADIUS_KM, tag=""):
    init_ee()
    co2 = json.loads((OUT / "co2_summary.json").read_text())
    city = json.loads((OUT / "city_fit.json").read_text())
    src = (city["source_lat"], city["source_lon"])
    e_pred_kg_s = co2["satellite_co2_mt_yr_midday"] * 1e9 / (365.25 * 86400)
    cx, cy, ce = emission_prior(src, e_pred_kg_s, prior_radius_km)
    print(f"Prior: {len(ce)} emitting cells within {prior_radius_km} km, total {ce.sum():.1f} kg CO2/s "
          f"({co2['satellite_co2_mt_yr_midday']:.2f} Mt/yr)")

    rows, per_date = [], {}
    for prod, days in DATES.items():
        d = pd.read_csv(DATA_INTERIM / "oco" / f"{prod}_soundings.csv").drop_duplicates("sounding_id")
        d["t"] = pd.to_datetime(d.time, unit="s")
        d["date"] = d.t.dt.strftime("%Y-%m-%d")
        for day in days:
            g = d[(d.date == day) & (d.xco2_quality_flag == 0)].copy()
            g["x"] = (g.longitude - src[1]) * KM_PER_DEG_LON_EQ * np.cos(np.radians(src[0]))
            g["y"] = (g.latitude - src[0]) * KM_PER_DEG_LAT
            g = g[np.hypot(g.x, g.y) <= FIT_RADIUS_KM]
            t_mid = g.t.min() + (g.t.max() - g.t.min()) / 2
            met = era5_at([t_mid], *src)[0]
            u, v, ps = met["u_component_of_wind_850hPa"], met["v_component_of_wind_850hPa"], met["surface_pressure"]
            pred, _ = predict_ppm(g.x.to_numpy(), g.y.to_numpy(), cx, cy, ce, u, v, ps)
            coef, se, rms, chi2 = fit_date(g, pred)
            beta, beta_se = coef[3], se[3]
            ws = float(np.hypot(u, v))
            wd = float((270 - np.degrees(np.arctan2(v, u))) % 360)
            per_date[f"{prod} {day}"] = {
                "time_utc": str(t_mid), "local_time": str(t_mid + pd.Timedelta("5h30min"))[11:16],
                "n": int(len(g)), "wind_ms": ws, "wind_from_deg": wd, "blh_m": met["boundary_layer_height"],
                "pred_max_ppm": float(pred.max()), "pred_mean_downwind_ppm": float(pred[pred > 0.01].mean()) if (pred > 0.01).any() else 0.0,
                "n_in_plume": int((pred > 0.05).sum()), "beta": float(beta), "beta_se": float(beta_se),
                "snr": float(beta / beta_se), "resid_rms_ppm": rms, "reduced_chi2": chi2,
                "e_obs_mt_yr": float(beta * co2["satellite_co2_mt_yr_midday"]),
                "e_obs_mt_yr_se": float(beta_se * co2["satellite_co2_mt_yr_midday"]),
            }
            g = g.assign(pred=pred, date=f"{prod} {day}", fitted_bg=coef[0] + coef[1] * g.x + coef[2] * g.y)
            rows.append(g)
            r = per_date[f"{prod} {day}"]
            print(f"{prod} {day} {r['local_time']} IST  n={r['n']:4d}  wind {ws:.1f} m/s from {wd:3.0f}°  "
                  f"pred max {r['pred_max_ppm']:.2f} ppm, {r['n_in_plume']:3d} soundings >0.05 ppm  "
                  f"beta = {beta:5.2f} ± {beta_se:.2f}  (SNR {beta / beta_se:4.1f})  resid {rms:.2f} ppm")

    b = np.array([r["beta"] for r in per_date.values()])
    s = np.array([r["beta_se"] for r in per_date.values()])
    wts = 1 / s**2
    beta_c = float(np.sum(wts * b) / wts.sum())
    beta_c_se = float(1 / np.sqrt(wts.sum()))
    chi2_between = float(np.sum(wts * (b - beta_c) ** 2) / (len(b) - 1))
    beta_c_se_infl = beta_c_se * max(1.0, np.sqrt(chi2_between))
    e_c = beta_c * co2["satellite_co2_mt_yr_midday"]
    summary = {
        "status": "EXPLORATORY (D8 pending guide approval)",
        "e_pred_mt_yr": co2["satellite_co2_mt_yr_midday"], "prior_cells": int(len(ce)),
        "forward_model": {"sigma0_km": SIGMA0_KM, "k_spread": K_SPREAD, "wind": "ERA5 850 hPa at source, nearest hour",
                          "fit_radius_km": FIT_RADIUS_KM, "prior_radius_km": prior_radius_km},
        "per_date": per_date,
        "combined": {"beta": beta_c, "beta_se": beta_c_se, "beta_se_inflated": beta_c_se_infl,
                     "between_date_reduced_chi2": chi2_between, "snr": beta_c / beta_c_se_infl,
                     "e_obs_mt_yr": e_c, "e_obs_mt_yr_se": beta_c_se_infl * co2["satellite_co2_mt_yr_midday"]},
    }
    (OUT / f"oco_check{tag}.json").write_text(json.dumps(summary, indent=2, default=float))
    print(f"\nCOMBINED (8 dates, inverse-variance): beta = {beta_c:.2f} ± {beta_c_se_infl:.2f} "
          f"(between-date chi2 {chi2_between:.1f})  ->  OCO-based emission {e_c:.2f} ± "
          f"{beta_c_se_infl * co2['satellite_co2_mt_yr_midday']:.2f} Mt/yr vs NO2-based {co2['satellite_co2_mt_yr_midday']:.2f}")
    figures(pd.concat(rows), per_date, summary, tag)


def figures(allrows, per_date, summary, tag=""):
    # Per-date map: observed XCO2 anomaly (minus fitted gradient) with predicted-plume contours
    keys = list(per_date)
    fig, axes = plt.subplots(2, 4, figsize=(13, 6.6), sharex=True, sharey=True)
    for ax, k in zip(axes.flat, keys):
        g = allrows[allrows.date == k]
        anom = g.xco2 - g.fitted_bg
        sc = ax.scatter(g.x, g.y, c=anom, s=7, cmap="RdBu_r", vmin=-1.5, vmax=1.5, linewidths=0)
        ax.tricontour(g.x, g.y, g.pred, levels=[0.05, 0.15, 0.3], colors=[INK], linewidths=[0.6, 0.9, 1.2])
        r = per_date[k]
        ax.plot(0, 0, marker="o", ms=6, mfc=ORANGE, mec=SURFACE, mew=1.5)
        ax.set_title(f"{k}\nβ = {r['beta']:.2f} ± {r['beta_se']:.2f}", fontsize=9, loc="left")
        ax.set_aspect("equal"); ax.grid(False)
    for ax in axes[-1]:
        ax.set_xlabel("km east of source")
    for ax in axes[:, 0]:
        ax.set_ylabel("km north of source")
    cb = fig.colorbar(sc, ax=axes, shrink=0.8); cb.set_label("XCO₂ minus fitted background (ppm)", color=INK2)
    cb.outline.set_edgecolor(GRID)
    fig.suptitle("OCO soundings (colour) and predicted Pune plume (contours 0.05 / 0.15 / 0.3 ppm)", fontsize=11, x=0.01, ha="left")
    fig.savefig(FIG / f"oco_dates{tag}.png", bbox_inches="tight"); plt.close(fig)

    # Beta per date + combined
    fig, ax = plt.subplots(figsize=(6.8, 3.9))
    for i, k in enumerate(keys):
        r = per_date[k]
        ax.errorbar(r["beta"], i, xerr=r["beta_se"], fmt="o", color=BLUE, ms=6, mec=SURFACE, mew=1.5, elinewidth=1.5, capsize=0)
    c = summary["combined"]
    i = len(keys) + 0.6
    ax.errorbar(c["beta"], i, xerr=c["beta_se_inflated"], fmt="D", color=ORANGE, ms=8, mec=SURFACE, mew=1.5, elinewidth=2, capsize=0)
    ax.axvline(1, color=INK, lw=1, ls="--"); ax.axvline(0, color=INK2, lw=1)
    ax.set_yticks(list(range(len(keys))) + [i], keys + ["Combined"])
    ax.invert_yaxis(); ax.grid(axis="y", visible=False)
    ax.set_xlabel("β = observed / predicted plume (1 = agrees with the NO₂-based estimate)")
    fig.suptitle("OCO-3 / OCO-2 check of the NO₂-derived CO₂ (±1σ)", fontsize=11, x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(FIG / f"oco_beta{tag}.png"); plt.close(fig)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--prior-radius", type=float, default=PRIOR_RADIUS_KM, help="km; emission prior confined within this radius")
    ap.add_argument("--tag", default="", help="suffix for output files, e.g. _r10")
    a = ap.parse_args()
    run(a.prior_radius, a.tag)
