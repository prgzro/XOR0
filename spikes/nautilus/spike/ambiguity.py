"""Same-bar SL/TP ambiguity: on an H1 bar backtest, a bar that touches both the
stop and the target cannot say which came first. Nautilus picks one by its
O-H-L-C path; this report gives the P&L both ways so the edge test can count it.

Long exits are sells, so the BID bar decides; short exits are buys, so the ASK bar.
P&L is gross, in quote currency.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class BarRange:
    high: Decimal
    low: Decimal


@dataclass(frozen=True)
class Trade:
    side: str  # "LONG" or "SHORT"
    qty: Decimal
    entry_px: Decimal
    sl: Decimal
    tp: Decimal
    exit_ts: int  # ts of the bar that closed the trade


@dataclass(frozen=True)
class SameBarHit:
    trade: Trade
    bar_ts: int
    pnl_sl_first: Decimal
    pnl_tp_first: Decimal


def same_bar_hits(
    trades: Iterable[Trade],
    bid: Mapping[int, BarRange],
    ask: Mapping[int, BarRange],
) -> list[SameBarHit]:
    hits = []
    for t in trades:
        if t.side == "LONG":
            bar = bid[t.exit_ts]
            both = bar.low <= t.sl and bar.high >= t.tp
            sign = 1
        else:
            bar = ask[t.exit_ts]
            both = bar.high >= t.sl and bar.low <= t.tp
            sign = -1
        if both:
            hits.append(
                SameBarHit(
                    trade=t,
                    bar_ts=t.exit_ts,
                    pnl_sl_first=sign * (t.sl - t.entry_px) * t.qty,
                    pnl_tp_first=sign * (t.tp - t.entry_px) * t.qty,
                )
            )
    return hits
