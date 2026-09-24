"""
Why the "temporal", k = 3 IQR filter was chosen (proposal Phase 1 step 1, IQR outlier removal).

On the synthetic plume with injected retrieval spikes, the chosen filter must (1) catch most of the
spikes and (2) leave the plume, and hence the line density, essentially unchanged. A filter that
clips the plume would pass (1) and fail (2).

Note: "local" also passes these synthetic tests but was rejected on REAL data (it removes 29% of
pixels, because GEE's 1 km L3 grid copies each TROPOMI footprint into several cells). This
synthetic noise model, which is independent per cell, can't reproduce that, which is why the
real-data removal rate was checked too (research_log, 2026-09-24).
"""

import numpy as np
import pytest

from ecotrack.inversion.emg import RotatedGrid, bin_days, line_density
from ecotrack.qc import iqr_filter
from test_emg import INV, simulate


@pytest.fixture(scope="module")
def data():
    no2, u, v, ws, dx, dy = simulate(n_days=120, seed=0)
    rng = np.random.default_rng(9)
    spikes = rng.random(no2.shape) < 0.005
    spiked = no2 + spikes * rng.choice([-1, 1], no2.shape) * rng.uniform(3e-5, 6e-5, no2.shape)
    grid = RotatedGrid.from_config(INV)
    L_clean = line_density(*bin_days(no2, u, v, dx, dy, grid), grid)[0]
    return spiked, spikes, u, v, dx, dy, grid, L_clean


def _line_density_change(filtered, u, v, dx, dy, grid, L_clean):
    L = line_density(*bin_days(filtered, u, v, dx, dy, grid), grid)[0]
    return np.nansum(np.abs(L - L_clean)) / np.nansum(L_clean - np.nanmin(L_clean))


def test_temporal_filter_catches_spikes(data):
    spiked, spikes, *_ = data
    filtered, _ = iqr_filter(spiked, "temporal", 3.0)
    assert (np.isnan(filtered) & spikes).sum() / spikes.sum() > 0.8


def test_temporal_filter_preserves_plume(data):
    spiked, _, u, v, dx, dy, grid, L_clean = data
    assert _line_density_change(iqr_filter(spiked, "temporal", 3.0)[0], u, v, dx, dy, grid, L_clean) < 0.03


def test_domain_filter_would_clip_plume(data):
    """Documents why 'domain' was rejected: it changes the line density far more than 'temporal'."""
    spiked, _, u, v, dx, dy, grid, L_clean = data
    temporal = _line_density_change(iqr_filter(spiked, "temporal", 3.0)[0], u, v, dx, dy, grid, L_clean)
    domain = _line_density_change(iqr_filter(spiked, "domain", 1.5)[0], u, v, dx, dy, grid, L_clean)
    assert domain > 3 * temporal
