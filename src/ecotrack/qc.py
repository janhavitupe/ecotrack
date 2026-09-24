"""
TROPOMI NO2 outlier removal (proposal Phase 1, step 1: "IQR outlier removal").

The proposal doesn't say *which* IQR, and the choice matters: a plume pixel is high only on days
the wind points at it, so a filter that flags unusual days at a pixel removes the very signal the
inversion measures. Three variants are implemented and tested on synthetic plumes
(tests/test_qc.py); the chosen one is set in configs/study.yaml (tropomi.iqr).

- "temporal":    per pixel, flag days outside [Q1 - k IQR, Q3 + k IQR] of that pixel's time series
- "domain":      per overpass, flag pixels outside the fences of that overpass's whole box
- "local":       per overpass, flag pixels whose deviation from a local median (size ~ footprint)
                 lies outside the fences of all deviations in that overpass

Chosen: "temporal", k = 3 (Tukey far-out). On real data it removes 0.11% of pixels; on synthetic data
it catches 92% of injected spikes and changes the line density by 0.9%.
Rejected: "domain" clips the plume core (line density -7%); "local" looked best on synthetic data
with independent per-cell noise but removes 29% of REAL pixels. GEE's 1 km L3 grid copies each
~3.5 x 5.5 km TROPOMI pixel into several cells, so local deviations are ~0 except at footprint
edges, and the fences flag edges, not glitches.
"""

import numpy as np
from scipy.ndimage import median_filter


def _fences(x, k):
    q1, q3 = np.nanpercentile(x, [25, 75], axis=0)
    iqr = q3 - q1
    return q1 - k * iqr, q3 + k * iqr


def iqr_filter(no2, method="temporal", k=3.0, size=7):
    """Return a copy of no2[t, y, x] with outliers set to NaN, and the fraction removed."""
    out = no2.copy()
    finite = np.isfinite(no2)
    if method == "temporal":
        lo, hi = _fences(no2, k)
        bad = (no2 < lo[None]) | (no2 > hi[None])
    elif method == "domain":
        flat = no2.reshape(len(no2), -1)
        lo, hi = _fences(flat.T, k)
        bad = (no2 < lo[:, None, None]) | (no2 > hi[:, None, None])
    elif method == "local":
        bad = np.zeros_like(finite)
        for t in range(len(no2)):
            f = no2[t]
            if not np.isfinite(f).any():
                continue
            filled = np.where(np.isfinite(f), f, np.nanmedian(f))
            dev = f - median_filter(filled, size=size)
            lo, hi = _fences(dev[np.isfinite(dev)], k)
            bad[t] = (dev < lo) | (dev > hi)
    else:
        raise ValueError(method)
    bad &= finite
    out[bad] = np.nan
    return out, float(bad.sum() / finite.sum())
