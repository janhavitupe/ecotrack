"""Phase 3 label construction: unit conversion and conservation of the city total."""

import numpy as np
import pandas as pd

from ecotrack.inversion.emg import M_NO2
from ecotrack.labels import TO_T_KM2_YR, density_from_map


def test_uniform_map_conserves_total():
    # A uniform emission map on a 0.01 deg grid; cells at pixel centres inside the 25 km disc.
    lat = np.round(np.arange(18.80, 18.40, -0.01), 3)
    lon = np.round(np.arange(73.60, 74.00, 0.01), 3)
    e = np.full((len(lat), len(lon)), 2e-8)  # mol m-2 s-1
    total_kg_s = 5.0                        # pretend 25 km total
    cells = pd.DataFrame({"lat": [18.6, 18.65], "lon": [73.8, 73.85]})
    dens = density_from_map(e, total_kg_s, 5, lat, lon, cells, M_NO2)
    # density per m2 = e * M / total; times the total gives back e * M (kg m-2 s-1)
    np.testing.assert_allclose(dens * total_kg_s, 2e-8 * M_NO2, rtol=1e-12)


def test_unit_factor():
    # 1 kg m-2 s-1 = 1e6 kg km-2 s-1 = 31,557.6e6 t km-2 yr-1
    assert TO_T_KM2_YR == 1e6 * 31_557_600 / 1000
