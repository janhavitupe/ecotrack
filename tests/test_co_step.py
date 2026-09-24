"""
Synthetic test for the D4 CO step estimator (run_co_ratio).

An inert tracer is emitted at a known rate from a point source on the real cube grid, carried by
random winds, with retrieval-like noise, random day-to-day regional offsets, and a strong static
"terrain" pattern (larger than the plume). The estimator must recover the emission, and must
return ~0 when there is terrain but no source.
"""

import numpy as np
import pytest

from ecotrack.inversion.emg import RotatedGrid, bin_days, offsets_km, rotate
from ecotrack.inversion.run_co_ratio import anomalies, step_from

LAT0, LON0 = 18.60, 73.80
E_TRUE = 100.0      # mol/s CO
BG = 0.035          # mol/m2
INV = {"rot_res_km": 2.0, "along_km": [-40, 60], "across_halfwidth_km": 20}


def simulate(e_mol_s, n_days=300, seed=0):
    rng = np.random.default_rng(seed)
    lat = np.arange(19.045, 18.15, -0.01)
    lon = np.arange(73.355, 74.30, 0.01)
    dx, dy = offsets_km(lat, lon, LAT0, LON0)
    terrain = 0.002 * np.tanh((dx + 25) / 8) + 0.001 * np.exp(-((dx - 10) ** 2 + (dy + 15) ** 2) / 200)
    ws = rng.uniform(2.5, 6.5, n_days)
    wd = rng.uniform(0, 2 * np.pi, n_days)
    u, v = ws * np.cos(wd), ws * np.sin(wd)
    co = np.empty((n_days, len(lat), len(lon)))
    for k in range(n_days):
        along, across = rotate(dx, dy, u[k], v[k])
        sig = (3 + 0.15 * np.clip(along, 0, None)) * 1000
        L = e_mol_s / ws[k]  # inert: constant line density downwind
        plume = np.where(along >= 0, L * np.exp(-0.5 * (across * 1000 / sig) ** 2) / (np.sqrt(2 * np.pi) * sig), 0)
        co[k] = BG + terrain + plume + rng.normal(0, 0.0015, dx.shape) + rng.normal(0, 0.001)
    return co, u, v, ws, dx, dy


def estimate(co, u, v, ws, dx, dy):
    an = anomalies(co, np.zeros(co.shape[1:]), H_km=1e9)
    grid = RotatedGrid.from_config(INV)
    sums, cnts = bin_days(an, u, v, dx, dy, grid)
    step, _, _ = step_from(sums, cnts, grid)
    return step / np.mean(1 / ws)


def test_recovers_inert_emission_despite_terrain():
    e = estimate(*simulate(E_TRUE, seed=4))
    assert e == pytest.approx(E_TRUE, rel=0.20)


def test_terrain_alone_gives_no_source():
    e = estimate(*simulate(0.0, seed=5))
    assert abs(e) < 0.15 * E_TRUE
