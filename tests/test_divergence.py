"""
Synthetic-plume recovery test for the flux-divergence emission map.

Same simulated point source as tests/test_emg.py (E = 0.5 mol/s NO2, tau = 3 h, background
3e-5 mol/m2, retrieval-like noise). With the true lifetime and background, integrating the
emission map around the source must recover E, stable with radius; the box corners must hold
no spurious source (|total| < 10% of E).
"""

import numpy as np
import pytest

from ecotrack.inversion.divergence import emission_map, integrate_kg_s
from ecotrack.inversion.emg import M_NO2, offsets_km
from test_emg import BACKGROUND, LAT0, LON0, TRUE_E_NO2, TRUE_TAU_H, simulate


@pytest.fixture(scope="module")
def maps():
    no2, u, v, ws, dx, dy = simulate(n_days=300, seed=3)
    lat = np.arange(19.045, 18.15, -0.01)
    lon = np.arange(73.355, 74.30, 0.01)
    e, *_ = emission_map(no2, u, v, lat, lon, TRUE_TAU_H * 3600, BACKGROUND, nox_no2_ratio=1.0)
    ox, oy = offsets_km(lat, lon, LAT0, LON0)
    return e, np.hypot(ox, oy), lat, lon


@pytest.mark.parametrize("radius_km", [15, 25, 35])
def test_recovers_source_total(maps, radius_km):
    e, r, lat, lon = maps
    total = integrate_kg_s(e, r <= radius_km, lat, lon) / M_NO2  # mol/s
    assert total == pytest.approx(TRUE_E_NO2, rel=0.15)


def test_background_area_near_zero(maps):
    e, r, lat, lon = maps
    ring = (r > 60) & (r < 70)  # box corners, beyond most of the simulated plume
    ring_total = integrate_kg_s(e, ring, lat, lon) / M_NO2
    assert abs(ring_total) < 0.10 * TRUE_E_NO2  # noise only: no spurious source
