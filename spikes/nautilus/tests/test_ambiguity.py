"""Trades whose exit bar touched both SL and TP: report P&L both ways."""

from decimal import Decimal as D

from spike.ambiguity import BarRange, Trade, same_bar_hits

T = 1_000


def bars(ts, high, low):
    return {ts: BarRange(D(high), D(low))}


def long_trade(exit_ts=T):
    return Trade("LONG", D(100_000), D("1.10000"), sl=D("1.09800"), tp=D("1.10300"), exit_ts=exit_ts)


def test_long_exit_bar_touching_both_levels_is_reported_both_ways():
    bid = bars(T, "1.10350", "1.09750")
    ask = bars(T, "1.10360", "1.09760")
    [hit] = same_bar_hits([long_trade()], bid, ask)
    assert hit.bar_ts == T
    assert hit.pnl_sl_first == D(-200)  # 20 pips x 100k
    assert hit.pnl_tp_first == D(300)  # 30 pips x 100k


def test_exit_bar_touching_only_one_level_is_not_reported():
    bid = bars(T, "1.10350", "1.09900")
    ask = bars(T, "1.10360", "1.09910")
    assert same_bar_hits([long_trade()], bid, ask) == []


def test_short_exits_are_buys_so_the_ask_bar_decides():
    short = Trade("SHORT", D(100_000), D("1.10000"), sl=D("1.10200"), tp=D("1.09700"), exit_ts=T)
    bid = bars(T, "1.10150", "1.09640")  # bid alone never reaches the SL
    ask = bars(T, "1.10250", "1.09650")
    [hit] = same_bar_hits([short], bid, ask)
    assert (hit.pnl_sl_first, hit.pnl_tp_first) == (D(-200), D(300))
