"""
Flux-divergence emission mapping (Beirle et al. 2019, Sci. Adv. 5, eaax9800).

    E_NOx = L * ( div(V * w) + (V - V_bg) / tau )

V      tropospheric NO2 column (mol/m2), per overpass
w      wind vector at overpass time (m/s)
tau    NOx lifetime (s), taken from the EMG fit
V_bg   regional background column: the sink is applied to the enhancement only, otherwise the
       free-tropospheric background would appear as a spurious uniform "emission" everywhere
L      NOx/NO2 ratio

The divergence is linear, so the temporal mean of daily divergences equals the divergence of the
mean flux; we take the mean flux components (NaN-tolerant) and differentiate once. That keeps
pixels that are cloudy on some days.
"""

import numpy as np

from ecotrack.inversion.emg import KM_PER_DEG_LAT, KM_PER_DEG_LON_EQ, M_NO2


def grid_metres(lat, lon):
    """Pixel-centre coordinates in metres (x east, y north) and pixel areas (m2)."""
    lat0 = float(np.mean(lat))
    x = (lon - lon[0]) * KM_PER_DEG_LON_EQ * np.cos(np.radians(lat0)) * 1000
    y = (lat - lat[0]) * KM_PER_DEG_LAT * 1000  # rows run north -> south, so y decreases
    dx = abs(x[1] - x[0])
    dy = abs(y[1] - y[0])
    return x, y, dx * dy


def mean_flux(no2, u, v, weights=None):
    """Weighted temporal mean of the flux components V*u and V*v (mol m-1 s-1)."""
    w = np.ones(len(no2)) if weights is None else weights
    valid = np.isfinite(no2)
    wv = w[:, None, None] * valid
    V = np.where(valid, no2, 0.0)
    den = wv.sum(0)
    with np.errstate(invalid="ignore", divide="ignore"):
        fx = (wv * V * u[:, None, None]).sum(0) / den
        fy = (wv * V * v[:, None, None]).sum(0) / den
        vbar = (wv * V).sum(0) / den
    return fx, fy, vbar


def divergence(fx, fy, x, y):
    """Central-difference divergence of a flux field on a (lat, lon) grid (mol m-2 s-1)."""
    return np.gradient(fx, x, axis=1) + np.gradient(fy, y, axis=0)


def emission_map(no2, u, v, lat, lon, tau_s, v_bg, nox_no2_ratio, weights=None):
    """Mean NOx emission map (mol NOx m-2 s-1) plus its two terms, for inspection."""
    x, y, _ = grid_metres(lat, lon)
    fx, fy, vbar = mean_flux(no2, u, v, weights)
    div = divergence(fx, fy, x, y)
    sink = (vbar - v_bg) / tau_s
    return nox_no2_ratio * (div + sink), div, sink, vbar


def integrate_kg_s(e_map, mask, lat, lon):
    """Sum an emission map (mol m-2 s-1) over a boolean pixel mask -> kg/s (NOx as NO2)."""
    _, _, area = grid_metres(lat, lon)
    return float(np.nansum(e_map[mask]) * area * M_NO2)
