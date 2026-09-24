"""
Synthetic-plume recovery test for the Phase 1 inversion.

A point source with known emission E and lifetime tau is simulated on the real cube grid
(0.01 deg around Pune) for 200 overpasses with random wind directions and speeds, plus
retrieval-like noise. The full pipeline (rotation -> line density -> EMG fit by Differential
Evolution) must recover E and tau. This is the evidence that the code does what the Methods
chapter says it does.
"""

import numpy as np
import pytest

from ecotrack.inversion.emg import RotatedGrid, bin_days, emissions, fit_emg, line_density, offsets_km, rotate

LAT0, LON0 = 18.60, 73.80
TRUE_E_NO2 = 0.5          # mol/s  (~0.7 kt NO2 per midday-year: a mid-size Indian city)
TRUE_TAU_H = 3.0
BACKGROUND = 3.0e-5       # mol/m2
NOISE = 6.0e-6            # mol/m2, per pixel
INV = {"rot_res_km": 2.0, "along_km": [-40, 60], "across_halfwidth_km": 20}
DE = {"popsize": 30, "mutation": [0.5, 1.0], "recombination": 0.7, "maxiter": 1000, "seed": 1}


def simulate(n_days=200, seed=0):
    rng = np.random.default_rng(seed)
    lat = np.arange(19.045, 18.15, -0.01)
    lon = np.arange(73.355, 74.30, 0.01)
    dx, dy = offsets_km(lat, lon, LAT0, LON0)
    ws = rng.uniform(2.5, 6.5, n_days)
    wd = rng.uniform(0, 2 * np.pi, n_days)
    u, v = ws * np.cos(wd), ws * np.sin(wd)
    no2 = np.empty((n_days, len(lat), len(lon)))
    for k in range(n_days):
        along, across = rotate(dx, dy, u[k], v[k])
        t = np.clip(along, 0, None) * 1000 / ws[k]                        # travel time (s)
        L = TRUE_E_NO2 / ws[k] * np.exp(-t / (TRUE_TAU_H * 3600))         # line density, mol/m
        sig_y = (3 + 0.15 * np.clip(along, 0, None)) * 1000                # plume width grows downwind (m)
        plume = np.where(along >= 0, L * np.exp(-0.5 * (across * 1000 / sig_y) ** 2) / (np.sqrt(2 * np.pi) * sig_y), 0)
        no2[k] = BACKGROUND + plume + rng.normal(0, NOISE, dx.shape)
    return no2, u, v, ws, dx, dy


@pytest.mark.parametrize("seed", [0, 1])
def test_recovers_emission_and_lifetime(seed):
    no2, u, v, ws, dx, dy = simulate(seed=seed)
    grid = RotatedGrid.from_config(INV)
    sums, cnts = bin_days(no2, u, v, dx, dy, grid)
    L, _ = line_density(sums, cnts, grid)
    fit = fit_emg(grid.along, L, DE)
    e = emissions(fit["a"], fit["x0"], ws.mean(), nox_no2_ratio=1.0)
    assert fit["r2"] > 0.95
    assert e.e_no2_mol_s == pytest.approx(TRUE_E_NO2, rel=0.20)
    assert e.tau_h == pytest.approx(TRUE_TAU_H, rel=0.25)
