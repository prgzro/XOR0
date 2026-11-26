import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from spike.strategy import (Bars, ForecastStats, candidate_direction, rollovers_between,  # noqa: E402
                            simulate, wilder_atr)

TICK = 0.00005
SPREAD = 0.0001


def make_bars(mid_ohlc, start="2025-07-01 12:00"):
    mid = np.array(mid_ohlc, dtype=float)
    ts = pd.date_range(start, periods=len(mid), freq="h", tz="UTC")
    half = SPREAD / 2
    return Bars(ts, mid, mid - half, mid + half, TICK)


def flat(n, px=1.1000):
    return [[px, px + 0.0002, px - 0.0002, px]] * n


def fs(tp, sl_long=1.0950, sl_short=1.1050, p_up=0.7, move=1.0):
    return ForecastStats(p_up, move, sl_long, sl_short, tp, 1.0)


ATR = 0.0020


def test_long_entry_is_next_open_at_ask_plus_slippage():
    b = make_bars(flat(30))
    tr = simulate(b, 0, 1, fs(tp=1.1100), ATR)
    assert tr.entry_i == 1
    assert tr.entry == pytest.approx(1.1000 + SPREAD / 2 + TICK)


def test_sl_is_clamped_between_half_and_three_atr():
    b = make_bars(flat(30))
    tight = simulate(b, 0, 1, fs(tp=1.1100, sl_long=1.0999), ATR)
    assert tight.entry - tight.sl == pytest.approx(0.5 * ATR)
    wide = simulate(b, 0, 1, fs(tp=1.1100, sl_long=1.0500), ATR)
    assert wide.entry - wide.sl == pytest.approx(3.0 * ATR)


def test_time_exit_after_24_bars_at_bid_close():
    b = make_bars(flat(40))
    tr = simulate(b, 0, 1, fs(tp=1.1100), ATR)
    assert tr.reason == "time"
    assert tr.exit_i == 24  # entry bar 1 is bar 1 of 24
    assert tr.exit == pytest.approx(1.1000 - SPREAD / 2 - TICK)
    assert tr.r_gross < 0  # paid spread and two ticks


def test_same_bar_sl_and_tp_assumes_sl_first():
    rows = flat(30)
    rows[3] = [1.1000, 1.1200, 1.0800, 1.1000]
    b = make_bars(rows)
    sl_first = simulate(b, 0, 1, fs(tp=1.1100), ATR)
    tp_first = simulate(b, 0, 1, fs(tp=1.1100), ATR, tp_first=True)
    assert (sl_first.reason, sl_first.exit_i) == ("sl", 3)
    assert tp_first.reason == "tp"


def test_gap_through_sl_fills_at_open_not_at_sl():
    rows = flat(30)
    rows[4] = [1.0900, 1.0910, 1.0890, 1.0900]
    b = make_bars(rows)
    tr = simulate(b, 0, 1, fs(tp=1.1100, sl_long=1.0980), ATR)
    assert tr.reason == "sl"
    assert tr.exit == pytest.approx(1.0900 - SPREAD / 2 - TICK)
    assert tr.r_gross < -1  # worse than the SL


def test_short_mirrors_long():
    rows = flat(30)
    rows[2] = [1.1000, 1.1002, 1.0880, 1.0900]
    b = make_bars(rows)
    tr = simulate(b, 0, -1, fs(tp=1.0900), ATR)
    assert tr.entry == pytest.approx(1.1000 - SPREAD / 2 - TICK)
    assert tr.reason == "tp"
    assert tr.r_gross > 0


def test_degenerate_tp_on_wrong_side_of_entry_is_no_trade():
    b = make_bars(flat(30))
    assert simulate(b, 0, 1, fs(tp=1.1000), ATR) is None


def test_no_next_bar_is_no_trade():
    b = make_bars(flat(5))
    assert simulate(b, 4, 1, fs(tp=1.1100), ATR) is None


def test_net_r_subtracts_commission_and_financing():
    b = make_bars(flat(40), start="2025-07-01 12:00")  # crosses 17:00 NY = 21:00 UTC
    tr = simulate(b, 0, 1, fs(tp=1.1100), ATR)
    assert tr.rollovers == 1
    risk = tr.entry - tr.sl
    comm = 0.2e-4 * (tr.entry + tr.exit) / risk
    fin = 0.5e-4 * tr.entry / risk
    assert tr.r_net == pytest.approx(tr.r_gross - comm - fin)


def test_rollovers_counts_17_ny():
    t0 = pd.Timestamp("2025-07-01 20:00", tz="UTC")  # 16:00 NY (EDT)
    assert rollovers_between(t0, t0 + pd.Timedelta(hours=1)) == 1
    assert rollovers_between(t0, t0 + pd.Timedelta(minutes=30)) == 0
    assert rollovers_between(t0, t0 + pd.Timedelta(days=2)) == 2


def test_candidate_rule_both_directions_and_costs():
    up = fs(tp=1.11, p_up=0.70, move=0.80)
    assert candidate_direction(up, cost=0.2, p_min=0.65, move_min=0.5) == 1
    assert candidate_direction(up, cost=0.4, p_min=0.65, move_min=0.5) == 0
    down = fs(tp=1.09, p_up=0.25, move=-0.9)
    assert candidate_direction(down, cost=0.2, p_min=0.65, move_min=0.5) == -1


def test_atr_uses_only_past_bars():
    rng = np.random.default_rng(1)
    c = 1 + np.cumsum(rng.normal(0, 0.001, 200))
    mid = np.stack([c, c + 0.001, c - 0.001, c], 1)
    full = wilder_atr(mid)
    cut = wilder_atr(mid[:120])
    np.testing.assert_array_equal(full[:120], cut)
