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
        log.append(f"{symbol}: {int(crossed)} bars with ask close < bid close (kept)")
    bars = Bars(pd.DatetimeIndex(idx), mid, bid, ask, tick(symbol))
    atr = wilder_atr(mid)
    ret = np.abs(np.diff(mid[:, 3], prepend=np.nan))
    spikes = np.where(ret > 10 * np.r_[np.nan, atr[:-1]])[0]
    if len(spikes):
        log.append(f"{symbol}: {len(spikes)} bars with |mid return| > 10 ATR, flagged for spot-check: "
                   + ", ".join(str(bars.ts[i]) for i in spikes[:10]))
    return bars, log
