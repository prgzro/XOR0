"""Step 3 (PAPER only): bracket, kill/restart reconciliation, and IB reject.

Needs a READ-WRITE *paper* Gateway on 127.0.0.1:4002 (ibgw/docker-compose.paper-rw.yml).
Refuses to run unless the Gateway's only managed account is a paper DU... account and
ENABLE_LIVE_TRADING is not true (spike/paper.py). Every order event and every state
snapshot goes to data/paper/events.jsonl; each mode ends with a PASS/FAIL line.

    uv run python scripts/paper_bracket.py bracket   # Jev (mock, threaded) -> 25k EUR/USD + SL + TP (OCA)
    kill -9 <pid>                                   # once "bracket live" is printed
    uv run python scripts/paper_bracket.py restart  # reconcile; PASS only if position, SL and TP are tracked
    uv run python scripts/paper_bracket.py flatten  # cancel exits, close position
    uv run python scripts/paper_bracket.py reject   # 1,000 EUR/USD market (odd lot, #5752)
"""

import datetime as dt
import json
import os
import sys
import threading
import time
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from nautilus_trader.adapters.interactive_brokers import (
    IbOcaType,
    InteractiveBrokersDataClientConfig,
    InteractiveBrokersDataClientFactory,
    InteractiveBrokersExecutionClientConfig,
    InteractiveBrokersExecutionClientFactory,
    InteractiveBrokersInstrumentProviderConfig,
)
from nautilus_trader.common import Environment
from nautilus_trader.live import LiveNode
from nautilus_trader.model import Currency, InstrumentId, OrderSide, Quantity, TraderId
from nautilus_trader.trading import Strategy

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from spike.jev import JevDispatcher, Verdict
from spike.paper import HOST, PORT, paper_account_or_exit
from spike.strategy import snap_to_tick

OUT = ROOT / "data" / "paper"
EURUSD = InstrumentId.from_str("EUR/USD.IDEALPRO")
DATA_CLIENT_ID, EXEC_CLIENT_ID, GUARD_CLIENT_ID = 36, 37, 38  # exec id must not be a multiple of 1000
PIP = Decimal("0.0001")
BRACKET_QTY = 25_000  # IDEALPRO minimum
ODD_LOT_QTY = 1_000  # below IDEALPRO minimum, the #5752 repro
RUN_SECS = 45


class ApproveMockJev:
    def decide(self, request):
        time.sleep(1.0)  # stand-in for the ~1.2 s Jev round trip, off the event thread
        return Verdict(True, "mock: approved")


def tags(**values) -> str:
    return "IBOrderTags:" + json.dumps(values, separators=(",", ":"), sort_keys=True)


class PaperProbe(Strategy):
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    def __init__(self, mode: str) -> None:
        super().__init__()
        self.mode = mode
        self.log_path = OUT / "events.jsonl"
        self.dispatcher = JevDispatcher(ApproveMockJev(), mode="threaded")
        self.sent = False
        self.event_thread = threading.get_ident()
        self.verdict_threads: list[bool] = []  # True when the verdict ran on the event thread
        self.odd_lot_id = None
        self.outcome: tuple[bool, str] | None = None

    # --- journal -------------------------------------------------------------------
    def record(self, kind: str, **fields) -> None:
        with self.log_path.open("a") as f:
            f.write(json.dumps({"t": time.time_ns(), "mode": self.mode, "kind": kind, **fields}) + "\n")

    def venue_state(self) -> dict:
        open_orders = [
            {
                "id": str(o.client_order_id),
                "type": str(o.order_type),
                "side": str(o.side),
                "status": str(o.status),
                "qty": str(o.quantity),
                "strategy": str(o.strategy_id),
                "tags": [str(t) for t in (o.tags or [])],
            }
            for o in self.cache.orders_open(instrument_id=EURUSD)
        ]
        return {
            "net_position": str(self.portfolio.net_position(EURUSD)),
            "positions_open": len(self.cache.positions_open(instrument_id=EURUSD)),
            "open_orders": open_orders,
        }

    def snapshot(self, label: str) -> dict:
        state = self.venue_state()
        self.record("snapshot", label=label, **state)
        return state

    # --- lifecycle -----------------------------------------------------------------
    def on_start(self) -> None:
        instrument = self.cache.instrument(EURUSD)
        if instrument is None:  # raising in on_start aborts startup (fail closed)
            raise RuntimeError(f"instrument {EURUSD} not in cache")
        self.instrument = instrument
        self.event_thread = threading.get_ident()
        self.clock.set_timer("jev-drain", dt.timedelta(milliseconds=250), callback=self._drain)
        self.subscribe_quotes(EURUSD)
        self.snapshot("on_start")
        if self.mode == "flatten":
            for o in self.cache.orders_open(instrument_id=EURUSD):
                self.cancel_order(o.client_order_id)
            self.clock.set_time_alert_ns("close", self.clock.timestamp_ns() + 5_000_000_000, self._close)

    def _drain(self, _event) -> None:
        self.dispatcher.drain()

    def _close(self, _event) -> None:
        self.close_all_positions(EURUSD, reduce_only=False)

    def on_quote(self, quote) -> None:
        if self.sent:
            return
        if self.mode == "bracket":
            self.sent = True
            mid = (quote.bid_price.as_decimal() + quote.ask_price.as_decimal()) / 2
            # same path as the service: Candidate -> threaded Jev -> verdict drained on the event thread
            self.dispatcher.submit({"mid": str(mid)}, lambda v, m=mid: self._on_verdict(m, v))
        elif self.mode == "reject":
            self.sent = True
            order = self.order_factory.market(EURUSD, OrderSide.BUY, Quantity.from_int(ODD_LOT_QTY))
            self.odd_lot_id = order.client_order_id
            self.submit_order(order)

    def _on_verdict(self, mid: Decimal, verdict: Verdict) -> None:
        self.verdict_threads.append(threading.get_ident() == self.event_thread)
        if not verdict.approved:
            return
        tick = self.instrument.price_increment.as_decimal()
        oca = tags(ocaGroup=f"JEV-{uuid4().hex[:10]}", ocaType=IbOcaType.CANCEL_WITH_BLOCK.as_i32())
        orders = self.order_factory.bracket(
            instrument_id=EURUSD,
            order_side=OrderSide.BUY,
            quantity=Quantity.from_int(BRACKET_QTY),
            sl_trigger_price=self.instrument.make_price(snap_to_tick(mid - 30 * PIP, tick)),
            tp_price=self.instrument.make_price(snap_to_tick(mid + 45 * PIP, tick)),
            tp_post_only=False,
            tp_reduce_only=False,
            sl_reduce_only=False,
            tp_tags=[oca],
            sl_tags=[oca],
        )
        self.record("bracket_sent", mid=str(mid), orders=[repr(o) for o in orders])
        self.submit_order_list(orders)

    def on_order_event(self, event) -> None:
        self.record("order_event", type=type(event).__name__, repr=repr(event))

    def on_order_filled(self, event) -> None:
        # the pre-kill reference state that `restart` must reproduce
        state = self.snapshot("after_fill")
        if self.mode == "bracket" and bracket_tracked(state):
            print(f"bracket live: {json.dumps(state)}\nkill -9 {os.getpid()} now", flush=True)

    def on_position_event(self, event) -> None:
        self.record("position_event", type=type(event).__name__, repr=repr(event))

    def on_stop(self) -> None:
        state = self.snapshot("on_stop")
        self.outcome = judge(self, state)
        self.dispatcher.close()


# --- pass criteria ---------------------------------------------------------------
def bracket_tracked(state: dict) -> bool:
    exits = {(o["type"], o["side"], o["qty"]) for o in state["open_orders"]}
    qty = f"{BRACKET_QTY}.00"
    return (
        Decimal(state["net_position"]) == BRACKET_QTY
        and ("STOP_MARKET", "SELL", qty) in exits
        and ("LIMIT", "SELL", qty) in exits
    )


def judge(probe: PaperProbe, state: dict) -> tuple[bool, str]:
    if probe.mode == "bracket":
        ok = all(probe.verdict_threads) and bool(probe.verdict_threads)
        return ok, f"verdict on event thread: {probe.verdict_threads}"
    if probe.mode == "restart":
        exits = [o for o in state["open_orders"] if o["type"] in ("STOP_MARKET", "LIMIT")]
        return bracket_tracked(state), f"after reconciliation: {json.dumps(state)} exits={len(exits)}"
    if probe.mode == "flatten":
        flat = Decimal(state["net_position"]) == 0 and not state["open_orders"]
        return flat, json.dumps(state)
    if probe.mode == "reject":
        order = probe.cache.order(probe.odd_lot_id) if probe.odd_lot_id else None
        status = str(order.status) if order else "NOT SENT"
        if status == "REJECTED":
            return True, "odd lot REJECTED (no #5752)"
        if status == "FILLED":
            return False, "INCONCLUSIVE: IB filled the odd lot; run `flatten`"
        return False, f"odd lot left {status} (#5752 if ACCEPTED)"
    return False, "unknown mode"


def main(mode: str) -> None:
    if mode not in ("bracket", "restart", "flatten", "reject"):
        sys.exit(__doc__)
    account = paper_account_or_exit(GUARD_CLIENT_ID)
    OUT.mkdir(parents=True, exist_ok=True)
    provider = InteractiveBrokersInstrumentProviderConfig(load_ids={EURUSD})
    node = (
        LiveNode.builder(f"JEV-PAPER-{mode.upper()}", TraderId.from_str("JEV-003"), Environment.LIVE)
        .with_reconciliation(True)  # a failed reconciliation must abort startup
        .with_timeout_connection(30)
        .with_timeout_reconciliation(30)
        .add_data_client(
            None,
            InteractiveBrokersDataClientFactory(),
            InteractiveBrokersDataClientConfig(
                host=HOST,
                port=PORT,
                client_id=DATA_CLIENT_ID,
                use_regular_trading_hours=False,
                instrument_provider=provider,
            ),
        )
        .add_exec_client(
            None,
            InteractiveBrokersExecutionClientFactory(),
            InteractiveBrokersExecutionClientConfig(
                host=HOST,
                port=PORT,
                client_id=EXEC_CLIENT_ID,
                account_id=account,
                base_currency=Currency.from_str("USD"),
                instrument_provider=provider,
            ),
        )
        .build()
    )
    probe = PaperProbe(mode)
    node.add_strategy(probe)
    # re-adopt orders and positions left by a previous session on this instrument
    probe.set_external_order_instrument_ids([EURUSD])
    threading.Timer(RUN_SECS if mode != "bracket" else 600, node.handle().stop).start()
    print(f"pid {os.getpid()} mode {mode}", flush=True)
    node.run()  # a reconciliation failure raises here: nothing traded
    node.dispose()
    ok, detail = probe.outcome or (False, "strategy never stopped cleanly")
    print(f"{'PASS' if ok else 'FAIL'} {mode}: {detail}", flush=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
