"""Trivial spike strategy: mid-close vs SMA picks a side, a (mocked) Jev approves or
rejects, an approved Candidate becomes a market entry with SL and TP.

Not a trading idea; it only exercises the code path the real service will use:
bar close -> Candidate -> JevDispatcher -> verdict on the event thread -> bracket.

Bracket flags follow the v2 IB adapter's constraints even in backtest, so the same
order list is valid on IBKR: no post-only TP, no reduce-only exits.
"""

from collections import deque
from decimal import Decimal
from typing import NamedTuple

from nautilus_trader.model import (
    BarType,
    InstrumentId,
    OrderSide,
    Quantity,
)
from nautilus_trader.trading import Strategy

from spike.ambiguity import BarRange, Trade
from spike.jev import JevDispatcher, Verdict


class Fill(NamedTuple):
    client_order_id: str
    side: str
    qty: str
    px: str
    commission: Decimal
    ts_event: int


def snap_to_tick(px: Decimal, tick: Decimal) -> Decimal:
    """make_price only rounds to precision; IB FX needs the increment grid (0.00005)."""
    return (px / tick).quantize(Decimal(1)) * tick


class HourModThreeMockJev:
    """Deterministic stand-in for Jev: rejects Candidates whose bar hour is divisible by 3."""

    def decide(self, request: dict) -> Verdict:
        hour = request["bar_ts"] // 3_600_000_000_000
        if hour % 3 == 0:
            return Verdict(False, "mock: hour % 3 == 0")
        return Verdict(True, "mock: approved")


class SpikeStrategy(Strategy):
    # The PyO3 base's __new__ accepts only an optional config; keep our args out of it.
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    def __init__(
        self,
        instrument_id: InstrumentId,
        dispatcher: JevDispatcher,
        qty: int = 100_000,
        sma_bars: int = 24,
        sl_pips: int = 30,
        tp_pips: int = 45,
    ) -> None:
        super().__init__()
        self.instrument_id = instrument_id
        self.bid_type = BarType.from_str(f"{instrument_id}-1-HOUR-BID-EXTERNAL")
        self.ask_type = BarType.from_str(f"{instrument_id}-1-HOUR-ASK-EXTERNAL")
        self.dispatcher = dispatcher
        self.qty = qty
        pip = Decimal("0.0001")  # EUR/USD only in this spike
        self.sl_dist = sl_pips * pip
        self.tp_dist = tp_pips * pip
        self.sma_bars = sma_bars
        self.mids: deque[Decimal] = deque(maxlen=sma_bars)
        # half of a BID/ASK pair, by ts: the engine does not promise which side comes first
        self.pending_close: dict[int, tuple[str, Decimal]] = {}
        self.awaiting_verdict = False
        # journals (read by the runner)
        self.fills: list[Fill] = []
        self.verdicts: list[tuple[int, Verdict]] = []
        self.trades: list[Trade] = []
        self.bid_ranges: dict[int, BarRange] = {}
        self.ask_ranges: dict[int, BarRange] = {}
        self._open: dict | None = None

    def on_start(self) -> None:
        instrument = self.cache.instrument(self.instrument_id)
        if instrument is None:  # raising in on_start aborts startup (fail closed)
            raise RuntimeError(f"instrument {self.instrument_id} not in cache")
        self.instrument = instrument
        self.subscribe_bars([self.bid_type, self.ask_type])
        if self.dispatcher.mode == "threaded":
            import datetime as dt

            self.clock.set_timer("jev-drain", dt.timedelta(milliseconds=250), callback=self._drain)

    def _drain(self, _event) -> None:
        self.dispatcher.drain()

    # --- bar close -> Candidate -------------------------------------------------
    def on_bar(self, bar) -> None:
        side_name = "BID" if str(bar.bar_type) == str(self.bid_type) else "ASK"
        rng = BarRange(bar.high.as_decimal(), bar.low.as_decimal())
        (self.bid_ranges if side_name == "BID" else self.ask_ranges)[bar.ts_init] = rng
        twin = self.pending_close.pop(bar.ts_init, None)
        if twin is None:
            self.pending_close[bar.ts_init] = (side_name, bar.close.as_decimal())
            return
        if twin[0] == side_name:
            return  # duplicate bar for one side: skip, never guess
        self.pending_close.clear()  # anything older lost its twin
        mid = (twin[1] + bar.close.as_decimal()) / 2
        self.mids.append(mid)
        if len(self.mids) < self.sma_bars or self.awaiting_verdict:
            return
        if not self.portfolio.is_net_flat(self.instrument_id) or self.cache.orders_open(
            instrument_id=self.instrument_id
        ):
            return
        sma = sum(self.mids) / len(self.mids)
        side = "BUY" if mid > sma else "SELL"
        request = {"bar_ts": bar.ts_init, "side": side, "mid": str(mid)}
        self.awaiting_verdict = True
        self.dispatcher.submit(request, lambda v, r=request: self._on_verdict(r, v))

    # --- verdict (always on the event thread) -> bracket ---------------------------
    def _on_verdict(self, request: dict, verdict: Verdict) -> None:
        self.awaiting_verdict = False
        self.verdicts.append((request["bar_ts"], verdict))
        if not verdict.approved:
            return
        mid = Decimal(request["mid"])
        buy = request["side"] == "BUY"
        tick = self.instrument.price_increment.as_decimal()
        sl = self.instrument.make_price(snap_to_tick(mid - self.sl_dist if buy else mid + self.sl_dist, tick))
        tp = self.instrument.make_price(snap_to_tick(mid + self.tp_dist if buy else mid - self.tp_dist, tick))
        order_list = self.order_factory.bracket(
            instrument_id=self.instrument_id,
            order_side=OrderSide.BUY if buy else OrderSide.SELL,
            quantity=Quantity.from_int(self.qty),
            sl_trigger_price=sl,
            tp_price=tp,
            tp_post_only=False,
            tp_reduce_only=False,
            sl_reduce_only=False,
        )
        # v2 returns a plain list; find each leg by type, not position
        by_type = {str(o.order_type): o for o in order_list}
        entry, sl_order, tp_order = by_type["MARKET"], by_type["STOP_MARKET"], by_type["LIMIT"]
        self._open = {
            "entry_id": entry.client_order_id,
            "exit_ids": {sl_order.client_order_id, tp_order.client_order_id},
            "side": "LONG" if buy else "SHORT",
            "sl": sl.as_decimal(),
            "tp": tp.as_decimal(),
        }
        self.submit_order_list(order_list)

    # --- journal --------------------------------------------------------------------
    def on_order_filled(self, event) -> None:
        self.fills.append(
            Fill(
                str(event.client_order_id),
                str(event.order_side),
                str(event.last_qty),
                str(event.last_px),
                event.commission.as_decimal() if event.commission else Decimal(0),
                event.ts_event,
            )
        )
        o = self._open
        if o is None:
            return
        if event.client_order_id == o["entry_id"]:
            o["entry_px"] = event.last_px.as_decimal()
        elif event.client_order_id in o["exit_ids"] and "entry_px" in o:
            self.trades.append(
                Trade(o["side"], Decimal(self.qty), o["entry_px"], o["sl"], o["tp"], event.ts_event)
            )
            self._open = None
