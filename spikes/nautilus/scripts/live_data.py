"""Step 2: data-only LiveNode on the read-only paper Gateway (127.0.0.1:4002).

No execution client. Subscribes to H1 bars and logs, for every bar, its
ts_event / ts_init against wall-clock receipt time, to data/live/bars.jsonl.
Also requests 400 bars of warmup (the Kronos lookback) on start.

    uv run python scripts/live_data.py <run_seconds>
"""

import datetime as dt
import json
import sys
import threading
import time
from pathlib import Path

from nautilus_trader.adapters.interactive_brokers import (
    InteractiveBrokersDataClientConfig,
    InteractiveBrokersDataClientFactory,
    InteractiveBrokersInstrumentProviderConfig,
    MarketDataType,
)
from nautilus_trader.common import DataActor, Environment
from nautilus_trader.live import LiveNode
from nautilus_trader.model import BarType, ClientId, InstrumentId, TraderId

OUT = Path(__file__).resolve().parent.parent / "data" / "live"
INSTRUMENTS = ["EUR/USD.IDEALPRO", "USD/JPY.IDEALPRO", "XAUUSD.IBCMDTY"]
BAR_TYPES = [
    "EUR/USD.IDEALPRO-1-HOUR-MID-EXTERNAL",
    "EUR/USD.IDEALPRO-1-HOUR-BID-EXTERNAL",
    "EUR/USD.IDEALPRO-1-HOUR-ASK-EXTERNAL",
    "USD/JPY.IDEALPRO-1-HOUR-MID-EXTERNAL",
    "XAUUSD.IBCMDTY-1-HOUR-MID-EXTERNAL",
]
WARMUP = "EUR/USD.IDEALPRO-1-HOUR-MID-EXTERNAL"
IB = ClientId.from_str("IB")  # required: the bar types span two venues (IDEALPRO, IBCMDTY)


class BarTimingLogger(DataActor):
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    def __init__(self, log_path: Path) -> None:
        super().__init__()
        self.log_path = log_path

    def _write(self, record: dict) -> None:
        with self.log_path.open("a") as f:
            f.write(json.dumps(record) + "\n")

    def on_start(self) -> None:
        for iid in INSTRUMENTS:
            inst = self.cache.instrument(InstrumentId.from_str(iid))
            self._write({"kind": "instrument", "id": iid, "repr": repr(inst)})
        self.subscribe_bars([BarType.from_str(b) for b in BAR_TYPES], client_id=IB)
        # limit alone returns ~1 day; give a start that covers 400 H1 bars (~24 trading days)
        start = self.clock.utc_now() - dt.timedelta(days=35)
        self.request_bars(BarType.from_str(WARMUP), start=start, limit=400, client_id=IB)

    def on_bar(self, bar) -> None:
        self._write(
            {
                "kind": "bar",
                "bar_type": str(bar.bar_type),
                "ts_event": bar.ts_event,
                "ts_init": bar.ts_init,
                "recv_wall_ns": time.time_ns(),
                "o": str(bar.open),
                "h": str(bar.high),
                "l": str(bar.low),
                "c": str(bar.close),
            }
        )

    def on_historical_bars(self, bars) -> None:
        self._write(
            {
                "kind": "warmup",
                "count": len(bars),
                "first_ts_init": bars[0].ts_init if bars else None,
                "last_ts_init": bars[-1].ts_init if bars else None,
                "last_bar": repr(bars[-1]) if bars else None,
                "recv_wall_ns": time.time_ns(),
            }
        )

    def on_data(self, data) -> None:  # e.g. InteractiveBrokersSubscriptionIdle
        self._write({"kind": "data", "type": type(data).__name__, "repr": repr(data)})


def main(run_seconds: int) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    provider = InteractiveBrokersInstrumentProviderConfig(
        load_ids={InstrumentId.from_str(i) for i in INSTRUMENTS}
    )
    node = (
        LiveNode.builder("JEV-DATA-001", TraderId.from_str("JEV-001"), Environment.LIVE)
        .add_data_client(
            None,
            InteractiveBrokersDataClientFactory(),
            InteractiveBrokersDataClientConfig(
                host="127.0.0.1",
                port=4002,
                client_id=32,
                use_regular_trading_hours=False,
                market_data_type=MarketDataType.REALTIME,
                subscription_idle_timeout_secs=4000,
                instrument_provider=provider,
            ),
        )
        .build()
    )
    node.add_actor(BarTimingLogger(OUT / "bars.jsonl"))
    handle = node.handle()
    threading.Timer(run_seconds, handle.stop).start()
    node.run()
    node.dispose()


if __name__ == "__main__":
    main(int(sys.argv[1]))
