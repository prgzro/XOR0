import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from spike.stats import (cluster_bootstrap_mean, deflated_sharpe, holm, max_drawdown,  # noqa: E402
                         monthly_returns, pbo_cscv)


def test_holm_matches_hand_computation():
    np.testing.assert_allclose(holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])


def test_max_drawdown_counts_from_start():
    assert max_drawdown(np.array([-1.0, -1.0, 2.0, -3.0])) == 3.0
    assert max_drawdown(np.array([1.0, -2.0])) == 2.0


def test_cluster_bootstrap_is_wider_when_trades_cluster():
    rng = np.random.default_rng(0)
    day_effect = np.repeat(rng.normal(0, 1, 50), 10)
    r = day_effect + rng.normal(0, 0.1, 500)
    _, lo_c, hi_c, _ = cluster_bootstrap_mean(r, np.repeat(np.arange(50), 10))
    _, lo_i, hi_i, _ = cluster_bootstrap_mean(r, np.arange(500))
    assert (hi_c - lo_c) > 2 * (hi_i - lo_i)


def test_deflated_sharpe_falls_with_more_trials():
    r = np.random.default_rng(1).normal(0.05, 1, 400)
    assert deflated_sharpe(r, 50)["dsr"] < deflated_sharpe(r, 2)["dsr"]


def test_pbo_is_high_for_pure_noise_and_low_for_a_real_winner():
    rng = np.random.default_rng(2)
    noise = rng.normal(0, 1, (10, 12))
    real = noise.copy()
    real[:, 3] += 3
    assert pbo_cscv(real) < 0.1
    assert 0.2 < pbo_cscv(noise) < 0.8


def test_monthly_returns_compound_at_fixed_risk():
    ts = pd.to_datetime(["2025-07-02", "2025-07-20", "2025-08-05"], utc=True)
    m = monthly_returns(np.array([2.0, -1.0, 1.0]), pd.Series(ts))
    assert abs(m.iloc[0] - (1.02 * 0.99 - 1)) < 1e-12
    assert abs(m.iloc[1] - 0.01) < 1e-12
