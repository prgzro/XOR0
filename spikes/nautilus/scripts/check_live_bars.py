"""Step 2 check: read data/live/bars.jsonl from live_data.py and test each live H1 bar.

- arrives once per (bar_type, ts_init);
- is stamped at the bar close (ts_init on the hour, or :15 for the session-open bar);
- receipt delay (wall clock minus ts_init) is bounded;
- OHLC matches IBKR history pulled afterwards with Nautilus's historical client;
- at least 3 H1 closes per bar type, with no missing hour in between.
Exits non-zero unless every criterion passes.

    uv run python scripts/check_live_bars.py
"""

import asyncio
import datetime as dt
import json
import sys
from collections import Counter
from itertools import pairwise
from pathlib import Path

from nautilus_trader.adapters import interactive_brokers as ib
from nautilus_trader.model import InstrumentId

LOG = Path(__file__).resolve().parent.parent / "data" / "live" / "bars.jsonl"
NS = 1_000_000_000
MAX_DELAY_S = 30  # bar close -> callback; a bar stamped at its open would show ~3600 s
MIN_CLOSES = 3


def utc(ns: int) -> str:
    return dt.datetime.fromtimestamp(ns / NS, dt.UTC).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


async def history(instrument_ids, specs, end, duration):
    provider_config = ib.InteractiveBrokersInstrumentProviderConfig(load_ids=set(instrument_ids))
    provider = ib.InteractiveBrokersInstrumentProvider(provider_config)
    config = ib.InteractiveBrokersDataClientConfig(
        host="127.0.0.1",
        port=4002,
        client_id=31,
        use_regular_trading_hours=False,
        instrument_provider=provider_config,
    )
    client = ib.HistoricalInteractiveBrokersClient(provider, config)
    await client.request_instruments(instrument_ids=list(instrument_ids))
    bars = await client.request_bars(
        bar_specifications=specs,
        end_date_time=end,
        duration=duration,
        instrument_ids=list(instrument_ids),
        use_rth=False,
        timeout=120,
    )
    return {(str(b.bar_type), b.ts_init): (str(b.open), str(b.high), str(b.low), str(b.close)) for b in bars}


def main() -> None:
    rows = [json.loads(line) for line in LOG.read_text().splitlines()]
    bars = [r for r in rows if r["kind"] == "bar"]
    for r in rows:
        if r["kind"] in ("warmup", "data"):
            print(r["kind"], {k: v for k, v in r.items() if k not in ("kind", "last_bar")})
    counts = Counter((b["bar_type"], b["ts_init"]) for b in bars)
    dupes = {k: n for k, n in counts.items() if n > 1}

    ids = sorted({InstrumentId.from_str(b["bar_type"].split("-")[0]) for b in bars}, key=str)
    specs = sorted({"-".join(b["bar_type"].split("-")[1:4]) for b in bars})
    end = dt.datetime.now(dt.UTC).replace(minute=0, second=0, microsecond=0)
    oldest = min(b["ts_init"] for b in bars) / NS
    days = int((end.timestamp() - oldest) // 86400) + 2  # reach back past the live run
    hist = asyncio.run(history(ids, specs, end, f"{days} D"))

    print(
        f"{'bar_type':42} {'ts_init (UTC)':23} {'received (UTC)':23} {'delay s':>8}  on-close  matches-history"
    )
    delays = []
    mismatches = late = 0
    for b in sorted(bars, key=lambda b: (b["ts_init"], b["bar_type"])):
        delay = (b["recv_wall_ns"] - b["ts_init"]) / NS
        delays.append(delay)
        minute = dt.datetime.fromtimestamp(b["ts_init"] / NS, dt.UTC).minute
        ohlc = (b["o"], b["h"], b["l"], b["c"])
        h = hist.get((b["bar_type"], b["ts_init"]))
        match = "missing" if h is None else ("yes" if h == ohlc else f"NO hist={h} live={ohlc}")
        mismatches += match != "yes"
        late += not (0 <= delay <= MAX_DELAY_S)
        print(
            f"{b['bar_type']:42} {utc(b['ts_init']):23} {utc(b['recv_wall_ns']):23} {delay:8.2f}  "
            f"{'yes' if minute in (0, 15) else 'NO':8}  {match}"
        )
    print(f"\nbars: {len(bars)}  duplicates: {len(dupes)}  history mismatches: {mismatches}")
    if delays:
        print(f"delay s: min {min(delays):.2f}  max {max(delays):.2f}")
    for k, n in dupes.items():
        print("  duplicate", k, n)

    by_type: dict[str, list[int]] = {}
    for b in bars:
        by_type.setdefault(b["bar_type"], []).append(b["ts_init"])
    short = {t: len(set(v)) for t, v in by_type.items() if len(set(v)) < MIN_CLOSES}
    gaps = {}
    for t, v in by_type.items():
        ts = sorted(set(v))
        # >1 h between consecutive closes = a missing bar (the :15 session bar shortens a step, never lengthens)
        missing = [utc(b) for a, b in pairwise(ts) if b - a > 3600 * NS]
        if missing:
            gaps[t] = missing
    checks = {
        f"each bar once (duplicates: {len(dupes)})": not dupes,
        f"delay within 0-{MAX_DELAY_S} s, so stamped at close ({late} outside)": late == 0,
        f"matches IBKR history ({mismatches} mismatched/missing)": mismatches == 0,
        f">= {MIN_CLOSES} closes per bar type (short: {short})": not short,
        f"no missing hours (gaps: {gaps})": not gaps,
    }
    for name, ok in checks.items():
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    sys.exit(0 if all(checks.values()) else 1)


if __name__ == "__main__":
    main()
