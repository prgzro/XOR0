"""Step 1 data: EURUSD H1 BID and ASK bars from IBKR via Nautilus v2's historical client,
written to a Parquet catalog (with synthetic volume; see spike/data.py). Read-only Gateway on 127.0.0.1:4002, client id 31.

    uv run python scripts/pull_history.py [duration, default "1 Y"]
"""

import asyncio
import datetime as dt
import sys
from pathlib import Path

from nautilus_trader.adapters import interactive_brokers as ib
from nautilus_trader.model import InstrumentId
from nautilus_trader.persistence import ParquetDataCatalog

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from spike.data import with_synthetic_volume

CATALOG = Path(__file__).resolve().parent.parent / "data" / "catalog"
EURUSD = InstrumentId.from_str("EUR/USD.IDEALPRO")


async def main(duration: str) -> None:
    provider_config = ib.InteractiveBrokersInstrumentProviderConfig(load_ids={EURUSD})
    provider = ib.InteractiveBrokersInstrumentProvider(provider_config)
    config = ib.InteractiveBrokersDataClientConfig(
        host="127.0.0.1",
        port=4002,
        client_id=31,
        use_regular_trading_hours=False,
        request_timeout=120,
        instrument_provider=provider_config,
    )
    client = ib.HistoricalInteractiveBrokersClient(provider, config)
    instruments = await client.request_instruments(instrument_ids=[EURUSD])
    print("instrument:", instruments[0])
    end = dt.datetime.now(dt.UTC).replace(minute=0, second=0, microsecond=0)
    bars = await client.request_bars(
        bar_specifications=["1-HOUR-BID", "1-HOUR-ASK"],
        end_date_time=end,
        duration=duration,
        instrument_ids=[EURUSD],
        use_rth=False,
        timeout=300,
    )
    print(f"bars: {len(bars)}")
    for bar in bars[:2] + bars[-2:]:
        print(" ", bar, "ts_event", bar.ts_event, "ts_init", bar.ts_init)
    CATALOG.mkdir(parents=True, exist_ok=True)
    catalog = ParquetDataCatalog(str(CATALOG))
    catalog.write_instruments(instruments)
    bars = with_synthetic_volume(bars, instruments[0].size_precision)
    for bar_type in sorted({str(b.bar_type) for b in bars}):
        catalog.write_bars([b for b in bars if str(b.bar_type) == bar_type])
    print("catalog:", CATALOG)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "1 Y"))
