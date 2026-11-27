"""Edge test rules: Forecast -> Candidate -> simulated trade in R.

Every rule here is from the pre-registration in docs/research/kronos-edge-test.md.
Bars are aligned arrays per symbol: ts (bar-open UTC), mid/bid/ask OHLC.
Index t is the bar whose close the Forecast was made on; entry is at bar t+1's open.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

COMMISSION_BP = 0.2
FINANCING_BP_PER_NIGHT = 0.5
SL_MIN_ATR, SL_MAX_ATR = 0.5, 3.0
NY = "America/New_York"


@dataclass(frozen=True)
class Bars:
    ts: pd.DatetimeIndex
    mid: np.ndarray  # (n, 4) open, high, low, close
    bid: np.ndarray
    ask: np.ndarray
    tick: float


@dataclass(frozen=True)
class ForecastStats:
    p_up: float
    move_atr: float  # median path close at H minus current close, in ATR
    sl_long: float  # 10th percentile over paths of each path's lowest low over H
    sl_short: float  # 90th percentile over paths of each path's highest high over H
    tp: float  # median over paths of the close at H
    dispersion_atr: float  # (p90 - p10 of close at H) / ATR


@dataclass(frozen=True)
class Trade:
    direction: int  # +1 long, -1 short
    t: int  # forecast bar
    entry_i: int
    exit_i: int
    entry: float
    exit: float
    sl: float
    tp: float
    reason: str  # "sl", "tp", "time"
    r_gross: float  # price move in R, after spread and slippage (they are in the fills)
    r_net: float  # after commission and financing
    rollovers: int


def wilder_atr(mid: np.ndarray, n: int = 14) -> np.ndarray:
    """ATR at each bar using bars <= that bar only. NaN until n bars of true range exist."""
    h, l, c = mid[:, 1], mid[:, 2], mid[:, 3]
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.stack([h - l, np.abs(h - pc), np.abs(l - pc)]), axis=0)
    atr = np.full(len(c), np.nan)
    if len(c) <= n:
        return atr
    atr[n] = tr[1 : n + 1].mean()
    for i in range(n + 1, len(c)):
        atr[i] = (atr[i - 1] * (n - 1) + tr[i]) / n
    return atr


def forecast_stats(paths: np.ndarray, last_close: float, atr: float) -> ForecastStats:
    """paths: (n_paths, H, 4) OHLC."""
    close_h = paths[:, -1, 3]
    return ForecastStats(
        p_up=float((close_h > last_close).mean()),
        move_atr=float((np.median(close_h) - last_close) / atr),
        sl_long=float(np.quantile(paths[:, :, 2].min(axis=1), 0.10)),
        sl_short=float(np.quantile(paths[:, :, 1].max(axis=1), 0.90)),
        tp=float(np.median(close_h)),
        dispersion_atr=float((np.quantile(close_h, 0.9) - np.quantile(close_h, 0.1)) / atr),
    )


def cost_atr(bars: Bars, t: int, atr: float) -> float:
    """Expected round-trip cost at bar t's close, in ATR: spread + 2 ticks + 2 commissions."""
    spread = bars.ask[t, 3] - bars.bid[t, 3]
    comm = 2 * COMMISSION_BP * 1e-4 * bars.mid[t, 3]
    return float((spread + 2 * bars.tick + comm) / atr)


def candidate_direction(fs: ForecastStats, cost: float, p_min: float, move_min: float) -> int:
    if fs.p_up >= p_min and fs.move_atr - cost >= move_min:
        return 1
    if (1 - fs.p_up) >= p_min and -fs.move_atr - cost >= move_min:
        return -1
    return 0


def rollovers_between(t0: pd.Timestamp, t1: pd.Timestamp) -> int:
    """Number of 17:00 New York rollovers in (t0, t1]."""
    a, b = t0.tz_convert(NY), t1.tz_convert(NY)
    d = pd.date_range(a.normalize(), b.normalize() + pd.Timedelta(days=1), freq="D")
    roll = d + pd.Timedelta(hours=17)
    return int(((roll > a) & (roll <= b)).sum())


def simulate(bars: Bars, t: int, direction: int, fs: ForecastStats, atr: float,
             horizon: int = 24, tp_first: bool = False, slip_ticks: int = 1) -> Trade | None:
    """Simulate one trade opened at bar t+1's open. None if no bar t+1 or degenerate TP."""
    e = t + 1
    n = len(bars.ts)
    if e >= n:
        return None
    slip = slip_ticks * bars.tick
    if direction == 1:
        entry = bars.ask[e, 0] + slip
        sl = np.clip(fs.sl_long, entry - SL_MAX_ATR * atr, entry - SL_MIN_ATR * atr)
        tp = fs.tp
        if tp <= entry:
            return None
        side = bars.bid  # a long exits by selling at the bid
    else:
        entry = bars.bid[e, 0] - slip
        sl = np.clip(fs.sl_short, entry + SL_MIN_ATR * atr, entry + SL_MAX_ATR * atr)
        tp = fs.tp
        if tp >= entry:
            return None
        side = bars.ask
    risk = abs(entry - sl)

    last = min(e + horizon - 1, n - 1)
    exit_px, exit_i, reason = None, last, "time"
    for i in range(e, last + 1):
        o, h, l = side[i, 0], side[i, 1], side[i, 2]
        if direction == 1:
            gap_sl, gap_tp = (i > e and o <= sl), (i > e and o >= tp)
            hit_sl, hit_tp = l <= sl, h >= tp
        else:
            gap_sl, gap_tp = (i > e and o >= sl), (i > e and o <= tp)
            hit_sl, hit_tp = h >= sl, l <= tp
        if gap_sl or gap_tp:
            exit_px, exit_i, reason = o, i, "sl" if gap_sl else "tp"
            break
        if hit_sl and hit_tp:
            reason = "tp" if tp_first else "sl"
            exit_px, exit_i = (tp if tp_first else sl), i
            break
        if hit_sl or hit_tp:
            reason = "sl" if hit_sl else "tp"
            exit_px, exit_i = (sl if hit_sl else tp), i
            break
    if exit_px is None:
        exit_px = side[last, 3]
    exit_px = exit_px - direction * slip

    r_gross = direction * (exit_px - entry) / risk
    exit_time = bars.ts[exit_i] + pd.Timedelta(hours=1)  # a bar's close
    rolls = rollovers_between(bars.ts[e], exit_time)
    comm_r = COMMISSION_BP * 1e-4 * (entry + exit_px) / risk
    fin_r = FINANCING_BP_PER_NIGHT * 1e-4 * entry * rolls / risk
    return Trade(direction, t, e, exit_i, float(entry), float(exit_px), float(sl), float(tp),
                 reason, float(r_gross), float(r_gross - comm_r - fin_r), rolls)
