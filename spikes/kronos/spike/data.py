"""Load IBKR H1 MIDPOINT/BID/ASK for one symbol into aligned Bars, applying the
pre-registered cleaning rules (docs/research/kronos-edge-test.md, Data). Every dropped or
flagged bar is returned in a log so it can be recorded."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from spike.strategy import Bars, wilder_atr

DATA = Path(__file__).resolve().parents[1] / "data" / "ibkr"
TICKS = {"USDJPY": 0.005, "EURJPY": 0.005, "GBPJPY": 0.005, "XAUUSD": 0.01}
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD",
           "EURGBP", "EURJPY", "GBPJPY", "EURCHF", "XAUUSD"]
MAJORS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD"]  # the Edge test universe
OOS_START = pd.Timestamp("2025-07-01", tz="UTC")


def session(symbol: str) -> str:
    return "gold" if symbol == "XAUUSD" else "fx"


def tick(symbol: str) -> float:
    return TICKS.get(symbol, 0.00005)


def _bad(df):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    return (h < l) | (c > h) | (c < l) | (o > h) | (o < l) | ~np.isfinite(o + h + l + c)


BAD_TICK_ATR = 3.0  # D5: a BID/ASK value this many ATR outside the mid bar's range is a bad tick
SPREAD_WINDOW = 400


def clean_quotes(mid: np.ndarray, bid: np.ndarray, ask: np.ndarray) -> tuple[np.ndarray, np.ndarray, int]:
    """D5 (docs/research/kronos-edge-test.md). A bar is a bad quote bar if any BID or ASK value
    lies more than BAD_TICK_ATR x ATR outside [mid low, mid high], or BID > ASK in any of OHLC.
    Its BID/ASK OHLC are replaced by mid OHLC -/+ the median close half-spread of the previous
    SPREAD_WINDOW bars. ATR is the previous bar's (causal). MIDPOINT is never changed."""
    atr = np.r_[np.nan, wilder_atr(mid)[:-1]]
    lo = mid[:, 2:3] - BAD_TICK_ATR * atr[:, None]
    hi = mid[:, 1:2] + BAD_TICK_ATR * atr[:, None]
    outside = ((bid < lo) | (bid > hi) | (ask < lo) | (ask > hi)).any(axis=1) & np.isfinite(atr)
    bad = outside | (bid > ask + 1e-12).any(axis=1)
    half = pd.Series((ask[:, 3] - bid[:, 3]) / 2).where(~bad)
    h = half.rolling(SPREAD_WINDOW, min_periods=1).median().shift(1).bfill().to_numpy()
    bid, ask = bid.copy(), ask.copy()
    bid[bad] = mid[bad] - h[bad, None]
    ask[bad] = mid[bad] + h[bad, None]
    return bid, ask, int(bad.sum())


def load(symbol: str, data_dir: Path = DATA) -> tuple[Bars, list[str]]:
    log = []
    frames = {}
    for s in ("MIDPOINT", "BID", "ASK"):
        df = pd.read_parquet(data_dir / f"{symbol}_{s}.parquet")
        bad = _bad(df)
        if bad.any():
            log.append(f"{symbol} {s}: dropped {int(bad.sum())} malformed bars")
        frames[s] = df[~bad].set_index("ts")
    idx = frames["MIDPOINT"].index.intersection(frames["BID"].index).intersection(frames["ASK"].index)
    for s, df in frames.items():
        missing = len(df.index.difference(idx))
        if missing:
            log.append(f"{symbol} {s}: {missing} bars without a matching bar in the other series")
    cols = ["open", "high", "low", "close"]
    mid, bid, ask = (frames[s].loc[idx, cols].to_numpy(float) for s in ("MIDPOINT", "BID", "ASK"))
    crossed = (ask[:, 3] < bid[:, 3]).sum()
    if crossed:
        log.append(f"{symbol}: {int(crossed)} bars with ask close < bid close (replaced by D5)")
    bid, ask, n_fixed = clean_quotes(mid, bid, ask)
    if n_fixed:
        log.append(f"{symbol}: {n_fixed} bars with bad BID/ASK ticks replaced by mid ± median half-spread (D5)")
    bars = Bars(pd.DatetimeIndex(idx), mid, bid, ask, tick(symbol))
    atr = wilder_atr(mid)
    ret = np.abs(np.diff(mid[:, 3], prepend=np.nan))
    spikes = np.where(ret > 10 * np.r_[np.nan, atr[:-1]])[0]
    if len(spikes):
        log.append(f"{symbol}: {len(spikes)} bars with |mid return| > 10 ATR, flagged for spot-check: "
                   + ", ".join(str(bars.ts[i]) for i in spikes[:10]))
    return bars, log
