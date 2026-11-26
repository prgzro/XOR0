"""Step 2 side check: does the v2 IB execution client start against a READ-ONLY
Gateway? Builds a node with data + exec clients and reconciliation on, places no
orders, and stops after a few seconds. The account id comes from the Gateway
(spike.paper guard), never from code.

    uv run python scripts/probe_exec_readonly.py
"""

import sys
import threading
from pathlib import Path

from nautilus_trader.adapters.interactive_brokers import (
    InteractiveBrokersDataClientConfig,
    InteractiveBrokersDataClientFactory,
    InteractiveBrokersExecutionClientConfig,
    InteractiveBrokersExecutionClientFactory,
    InteractiveBrokersInstrumentProviderConfig,
)
from nautilus_trader.common import Environment
from nautilus_trader.live import LiveNode
from nautilus_trader.model import InstrumentId, TraderId

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from spike.paper import paper_account_or_exit


def main() -> None:
    account = paper_account_or_exit(probe_client_id=34)
    provider = InteractiveBrokersInstrumentProviderConfig(
        load_ids={InstrumentId.from_str("EUR/USD.IDEALPRO")}
    )
    node = (
        LiveNode.builder("JEV-EXEC-PROBE", TraderId.from_str("JEV-002"), Environment.LIVE)
        .with_reconciliation(True)
        .with_timeout_connection(20)
        .add_data_client(
            None,
            InteractiveBrokersDataClientFactory(),
            InteractiveBrokersDataClientConfig(
                host="127.0.0.1", port=4002, client_id=35, instrument_provider=provider
            ),
        )
        .add_exec_client(
            None,
            InteractiveBrokersExecutionClientFactory(),
            InteractiveBrokersExecutionClientConfig(
                host="127.0.0.1",
                port=4002,
                client_id=33,
                account_id=account,
                instrument_provider=provider,
            ),
        )
        .build()
    )
    threading.Timer(20, node.handle().stop).start()
    node.run()
    node.dispose()


if __name__ == "__main__":
    main()
