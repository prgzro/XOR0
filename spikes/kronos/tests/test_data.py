import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from spike.data import clean_quotes  # noqa: E402


def _bars(n=60, seed=0):
    rng = np.random.default_rng(seed)
    c = 1.10 + np.cumsum(rng.normal(0, 0.001, n))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) + 0.0005
    l = np.minimum(o, c) - 0.0005
    mid = np.stack([o, h, l, c], axis=1)
    return mid, mid - 0.00005, mid + 0.00005


def test_clean_bars_are_untouched():
    mid, bid, ask = _bars()
    b2, a2, n = clean_quotes(mid, bid, ask)
    assert n == 0 and np.array_equal(b2, bid) and np.array_equal(a2, ask)


def test_bad_tick_is_replaced_by_mid_plus_minus_median_half_spread():
    mid, bid, ask = _bars()
    bid[40, 0] = 79.95  # the AUDUSD 2012-02-23 22:15 kind of print
    ask[45, 2] = mid[45, 2] - 0.05  # far below the mid low
    b2, a2, n = clean_quotes(mid, bid, ask)
    assert n == 2
    for i in (40, 45):
        np.testing.assert_allclose(b2[i], mid[i] - 0.00005)
        np.testing.assert_allclose(a2[i], mid[i] + 0.00005)
    assert np.array_equal(b2[:40], bid[:40]) and bid[40, 0] == 79.95  # inputs not mutated


def test_crossed_bar_is_replaced_and_moderate_spread_blowout_is_kept():
    mid, bid, ask = _bars()
    bid[30, 3], ask[30, 3] = ask[30, 3], bid[30, 3]  # BID > ASK
    bid[50] = mid[50] - 0.0015  # a ~1-2 ATR rollover widening: real cost, kept
    b2, a2, n = clean_quotes(mid, bid, ask)
    assert n == 1
    assert (b2[30] < a2[30]).all()
    np.testing.assert_array_equal(b2[50], bid[50])
