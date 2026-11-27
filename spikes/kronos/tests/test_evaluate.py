import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate import feature_tests, median_split  # noqa: E402


def test_median_split_falls_back_to_ge_when_ties_sit_at_the_max():
    x = np.array([0.4, 0.45, 0.5, 0.5, 0.5])  # median == max: "> median" is empty
    np.testing.assert_array_equal(median_split(x), [False, False, True, True, True])


def test_median_split_keeps_strict_split_without_ties():
    np.testing.assert_array_equal(median_split(np.array([1.0, 2.0, 3.0, 4.0])), [False, False, True, True])


def test_constant_feature_is_not_testable_and_never_significant():
    rng = np.random.default_rng(0)
    n = 200
    df = pd.DataFrame({"r": rng.normal(size=n), "p_edge": np.full(n, 0.5), "move_abs": rng.random(n),
                       "dispersion_atr": rng.random(n), "sl_atr": rng.random(n),
                       "atr_pctile": rng.random(n), "hour": rng.integers(0, 24, n)})
    res = {f: (d, p, a) for f, d, p, a in feature_tests(df)}
    d, p, a = res["p_edge"]
    assert np.isnan(d) and p == 1.0 and a == 1.0
