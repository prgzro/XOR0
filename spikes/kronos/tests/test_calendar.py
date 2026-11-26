import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from spike.calendar import future_bar_times  # noqa: E402


def utc(s):
    return pd.Timestamp(s, tz="UTC")


def test_fx_session_open_bar_is_17_15_new_york():
    # 2025-07-01 is EDT: 16:00 NY = 20:00 UTC; next bars 21:15 UTC (17:15 NY), 22:00 UTC
    out = future_bar_times(utc("2025-07-01 20:00"), 3)
    assert list(out) == [utc("2025-07-01 21:15"), utc("2025-07-01 22:00"), utc("2025-07-01 23:00")]


def test_from_the_15_bar_the_next_is_on_the_hour():
    out = future_bar_times(utc("2025-07-01 21:15"), 1)
    assert out[0] == utc("2025-07-01 22:00")


def test_fx_skips_the_weekend():
    # Friday 2025-07-04 16:00 NY = 20:00 UTC is the last bar; next is Sunday 17:15 NY = 21:15 UTC
    out = future_bar_times(utc("2025-07-04 20:00"), 1)
    assert out[0] == utc("2025-07-06 21:15")


def test_gold_has_no_17_bar_and_opens_at_18():
    out = future_bar_times(utc("2025-07-01 20:00"), 2, session="gold")
    assert list(out) == [utc("2025-07-01 22:00"), utc("2025-07-01 23:00")]
    out = future_bar_times(utc("2025-07-04 20:00"), 1, session="gold")
    assert out[0] == utc("2025-07-06 22:00")


def test_winter_offset():
    # 2025-12-02 is EST: 16:00 NY = 21:00 UTC; session open 17:15 NY = 22:15 UTC
    out = future_bar_times(utc("2025-12-02 21:00"), 1)
    assert out[0] == utc("2025-12-02 22:15")


def test_horizon_length():
    assert len(future_bar_times(utc("2025-07-04 10:00"), 24)) == 24
