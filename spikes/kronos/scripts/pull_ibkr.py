"""Pull IBKR H1 MIDPOINT/BID/ASK history for the Edge test (read-only paper Gateway).

    uv run python scripts/pull_ibkr.py [--from 2010-01-01] [--symbols EURUSD,...]

Walks back from now in 1-year requests until --from, one Parquet file per
(symbol, series) in data/ibkr/. Resumable: a finished (symbol, series) is skipped.
Pacing: >= 11 s between requests (IBKR limit 60 per 10 min). Client id 41.
Read-only: it never places orders.
"""

import argparse
import asyncio
import datetime as dt
import time
from pathlib import Path

import pandas as pd
from ib_async import IB, Contract, Forex

SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD",
           "EURGBP", "EURJPY", "GBPJPY", "EURCHF", "XAUUSD"]
SERIES = ["MIDPOINT", "BID", "ASK"]
OUT = Path(__file__).resolve().parents[1] / "data" / "ibkr"
GAP_S = 11.0


def contract(sym):
    if sym == "XAUUSD":
        return Contract(secType="CMDTY", symbol="XAUUSD", exchange="SMART", currency="USD")
    return Forex(sym)


async def pull(ib, sym, series, start, last_req):
    path = OUT / f"{sym}_{series}.parquet"
    if path.exists():
        print(f"skip {path.name}")
        return last_req
    c = contract(sym)
    await ib.qualifyContractsAsync(c)
    frames, end = [], ""
    while True:
        wait = GAP_S - (time.monotonic() - last_req)
        if wait > 0:
            await asyncio.sleep(wait)
        bars = []
        for attempt in range(4):  # an empty reply can be a timeout, not the end of history
            if attempt:
                print(f"{sym} {series}: empty reply, retry {attempt} in 60 s", flush=True)
                await asyncio.sleep(60)
            last_req = time.monotonic()
            bars = await ib.reqHistoricalDataAsync(
                c, endDateTime=end, durationStr="1 Y", barSizeSetting="1 hour",
                whatToShow=series, useRTH=False, formatDate=2, timeout=180)
            if bars:
                break
        if not bars:
            break
        df = pd.DataFrame([(b.date, b.open, b.high, b.low, b.close) for b in bars],
                          columns=["ts", "open", "high", "low", "close"])
        df["ts"] = pd.to_datetime(df["ts"], utc=True)
        frames.append(df)
        first = df["ts"].min()
        print(f"{sym} {series}: {len(df)} bars {first} .. {df['ts'].max()}", flush=True)
        if first <= start:
            break
        end = first.to_pydatetime()
    if frames:
        out = pd.concat(frames).drop_duplicates("ts").sort_values("ts")
        out = out[out["ts"] >= start].reset_index(drop=True)
        if out["ts"].min() > start + pd.Timedelta(days=7):
            # never write a silently truncated history
            raise SystemExit(f"{sym} {series}: history starts {out['ts'].min()}, "
                             f"wanted {start}; not written, rerun to retry")
        OUT.mkdir(parents=True, exist_ok=True)
        out.to_parquet(path, index=False)
        print(f"wrote {path.name}: {len(out)} bars", flush=True)
    return last_req


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", default="2010-01-01")
    ap.add_argument("--symbols", default=",".join(SYMBOLS))
    a = ap.parse_args()
    start = pd.Timestamp(a.start, tz="UTC")
    ib = IB()
    await ib.connectAsync("127.0.0.1", 4002, clientId=41, readonly=True, timeout=30)
    last = 0.0
    try:
        for sym in a.symbols.split(","):
            for s in SERIES:
                last = await pull(ib, sym, s, start, last)
    finally:
        ib.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
