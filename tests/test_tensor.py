"""Phase 4: circular averaging of wind direction and balanced, reproducible block folds."""

import numpy as np
import pandas as pd

from ecotrack.features import FEATURES
from ecotrack.tensor import block_folds, season_features


def test_wind_direction_mean_is_circular():
    # 350 deg and 10 deg average to north (0 deg), not 180 deg
    rows = []
    for m, wd in (("2020-01", 350.0), ("2020-02", 10.0)):
        r = {f: 1.0 for f in FEATURES}
        r.update(cell_id="c1", season="2019-20", month=m, wd850=wd)
        rows.append(r)
    out = season_features(pd.DataFrame(rows))
    assert abs(out.wd850_sin.iloc[0]) < 1e-12 and abs(out.wd850_cos.iloc[0] - 1) < 1e-12


def test_block_folds_balanced_and_reproducible():
    rng = np.random.default_rng(0)
    n = 3000
    tab = pd.DataFrame({"cell_id": [f"c{i}" for i in range(n)],
                        "x_utm": rng.uniform(0, 60_000, n), "y_utm": rng.uniform(0, 60_000, n)})
    b1, f1 = block_folds(tab, 15, 5, 42)
    b2, f2 = block_folds(tab, 15, 5, 42)
    assert (f1 == f2).all() and (b1 == b2).all()
    sizes = f1.value_counts()
    assert sizes.max() - sizes.min() <= 0.25 * sizes.mean()
    # every block sits in exactly one fold
    assert pd.DataFrame({"b": b1, "f": f1}).groupby("b").f.nunique().max() == 1
