"""
Wind-rotation line-density inversion with an Exponentially Modified Gaussian (EMG) fit.

Method (Beirle et al. 2011; as adapted by Xie et al. 2026 for Shandong):
1. Every overpass is rotated about the source so its wind blows along +x ("along").
2. Rotated overpasses are averaged; integrating across the wind gives the line density L(x).
3. L(x) is fit with  L(x) = a * f(x; x0, mu, sigma) + B, where f is a unit-area EMG:
   an exponential decay (e-folding distance x0) downwind of a source at mu, smoothed by a
   Gaussian of width sigma. a is the NO2 burden attributable to the source (mol).
4. Lifetime tau = x0 / w (w = mean wind speed); emission E_NO2 = a / tau; E_NOx = ratio * E_NO2.

Units: distances in km, columns in mol/m2, line densities in mol/m, a in mol, E in mol/s.
"""

from dataclasses import asdict, dataclass

import numpy as np
from scipy.optimize import differential_evolution
from scipy.special import erfc, erfcx

M_NO2 = 46.0055e-3  # kg/mol; NOx emissions are conventionally reported as NO2 mass
SECONDS_PER_YEAR = 365.25 * 86400
KM_PER_DEG_LAT = 110.574
KM_PER_DEG_LON_EQ = 111.320


# ----------------------------------------------------------------------------- rotation
def offsets_km(lat, lon, lat0, lon0):
    """East/north offsets (km) of a lat/lon grid from the source (equirectangular; fine at ~50 km)."""
    lon2d, lat2d = np.meshgrid(lon, lat)
    dx = (lon2d - lon0) * KM_PER_DEG_LON_EQ * np.cos(np.radians(lat0))
    dy = (lat2d - lat0) * KM_PER_DEG_LAT
    return dx, dy


def rotate(dx, dy, u, v):
    """Coordinates in the wind frame: 'along' points where the wind blows TO, 'across' 90 deg left of it."""
    theta = np.arctan2(v, u)
    along = dx * np.cos(theta) + dy * np.sin(theta)
    across = -dx * np.sin(theta) + dy * np.cos(theta)
    return along, across


@dataclass
class RotatedGrid:
    along_edges: np.ndarray
    across_edges: np.ndarray

    @classmethod
    def from_config(cls, inv: dict):
        r, (a0, a1), w = inv["rot_res_km"], inv["along_km"], inv["across_halfwidth_km"]
        return cls(np.arange(a0, a1 + r / 2, r), np.arange(-w, w + r / 2, r))

    @property
    def along(self):
        return (self.along_edges[:-1] + self.along_edges[1:]) / 2

    @property
    def shape(self):
        return len(self.along_edges) - 1, len(self.across_edges) - 1


def bin_days(no2, u, v, dx, dy, grid: RotatedGrid):
    """
    Per-overpass rotated sums and counts, shape (n_days, n_along, n_across).
    Keeping them per day makes bootstrap resampling a cheap weighted sum.
    """
    na, nc = grid.shape
    sums = np.zeros((len(no2), na, nc))
    cnts = np.zeros((len(no2), na, nc))
    for k in range(len(no2)):
        along, across = rotate(dx, dy, u[k], v[k])
        ia = np.digitize(along, grid.along_edges) - 1
        ic = np.digitize(across, grid.across_edges) - 1
        ok = (ia >= 0) & (ia < na) & (ic >= 0) & (ic < nc) & np.isfinite(no2[k])
        flat = ia[ok] * nc + ic[ok]
        sums[k] = np.bincount(flat, weights=no2[k][ok], minlength=na * nc).reshape(na, nc)
        cnts[k] = np.bincount(flat, minlength=na * nc).reshape(na, nc)
    return sums, cnts


def line_density(sums, cnts, grid: RotatedGrid, weights=None):
    """Mean rotated field -> line density L(x) in mol/m (NaN-tolerant across the wind)."""
    w = np.ones(len(sums)) if weights is None else weights
    s = np.tensordot(w, sums, axes=1)
    c = np.tensordot(w, cnts, axes=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        field = s / c
    width_m = (grid.across_edges[-1] - grid.across_edges[0]) * 1000
    return np.nanmean(field, axis=1) * width_m, field


# ----------------------------------------------------------------------------- EMG model
def emg_unit(x, x0, mu, sigma):
    """Unit-area EMG (1/km). Uses erfcx where the direct form would overflow."""
    z = (sigma / x0 - (x - mu) / sigma) / np.sqrt(2)
    expo = sigma**2 / (2 * x0**2) - (x - mu) / x0
    with np.errstate(over="ignore", invalid="ignore"):  # the unused branch may overflow
        direct = np.exp(np.minimum(expo, 700)) * erfc(z)
        stable = np.exp(np.minimum(expo - z**2, 700)) * erfcx(z)
    return np.where(z > 0, stable, direct) / (2 * x0)


def emg_model(x, a, x0, mu, sigma, b):
    return a * emg_unit(x, x0, mu, sigma) / 1000 + b  # a [mol] * f [1/km] / 1000 -> mol/m


PARAMS = ("a", "x0", "mu", "sigma", "b")


def default_bounds(x, L):
    lo, hi = np.nanmin(L), np.nanmax(L)
    span = max(hi - lo, 1e-12)
    return [(0, span * 1000 * 300), (2, 150), (-15, 15), (1, 30), (lo - span, lo + span)]


def fit_emg(x, L, de: dict, bounds=None):
    ok = np.isfinite(L)
    x, L = x[ok], L[ok]
    bounds = bounds or default_bounds(x, L)
    scale = np.nanmax(np.abs(L))

    def cost(p):
        return np.sum(((emg_model(x, *p) - L) / scale) ** 2)

    res = differential_evolution(
        cost, bounds, popsize=de["popsize"], mutation=tuple(de["mutation"]),
        recombination=de["recombination"], maxiter=de["maxiter"], seed=de.get("seed"),
        tol=1e-10, polish=True,
    )
    p = dict(zip(PARAMS, res.x))
    resid = L - emg_model(x, *res.x)
    p["r2"] = 1 - np.sum(resid**2) / np.sum((L - L.mean()) ** 2)
    p["at_bound"] = [n for n, v, (lo, hi) in zip(PARAMS, res.x, bounds) if min(v - lo, hi - v) < 1e-3 * (hi - lo)]
    return p


# ----------------------------------------------------------------------------- emissions
@dataclass
class Emission:
    burden_mol: float
    x0_km: float
    wind_ms: float
    tau_h: float
    e_no2_mol_s: float
    e_nox_mol_s: float
    e_nox_kg_s: float
    e_nox_kt_yr: float  # midday rate expressed per year; not an annual total


def emissions(a, x0, wind_ms, nox_no2_ratio) -> Emission:
    tau_s = x0 * 1000 / wind_ms
    e_no2 = a / tau_s
    e_nox = nox_no2_ratio * e_no2
    kg_s = e_nox * M_NO2
    return Emission(a, x0, wind_ms, tau_s / 3600, e_no2, e_nox, kg_s, kg_s * SECONDS_PER_YEAR / 1e6)


def as_dict(e: Emission) -> dict:
    return {k: float(v) for k, v in asdict(e).items()}
