"""IBKR FX commission model for the Nautilus v2 backtest venue.

IBKR tiered FX: 0.20 bp of USD notional, minimum USD 2.00 per order
(docs/research/ibkr-api-and-products.md). The minimum is applied per fill here,
which overcharges partial fills slightly; acceptable for H1 bar backtests.
"""

from collections.abc import Mapping
from decimal import Decimal

from nautilus_trader.execution import FeeModel
from nautilus_trader.model import Currency, Money

RATE = Decimal("0.00002")  # 0.20 bp
MINIMUM_USD = Decimal("2.00")
USD = Currency.from_str("USD")


class IbkrFxFeeModel(FeeModel):
    """`usd_rates` maps a quote currency code to the USD value of one unit (needed for crosses)."""

    def __init__(self, usd_rates: Mapping[str, Decimal] | None = None) -> None:
        self.usd_rates = dict(usd_rates or {})

    def usd_notional(self, fill_quantity, fill_px, instrument) -> Decimal:
        qty = fill_quantity.as_decimal()
        if instrument.base_currency.code == "USD":
            return qty
        quote_notional = qty * fill_px.as_decimal()
        quote = instrument.quote_currency.code
        if quote == "USD":
            return quote_notional
        return quote_notional * self.usd_rates[quote]

    def get_commission(self, order, fill_quantity, fill_px, instrument) -> Money:
        fee = max(self.usd_notional(fill_quantity, fill_px, instrument) * RATE, MINIMUM_USD)
        return Money(fee, USD)  # pyright: ignore[reportArgumentType]  (Decimal accepted, stub says float)
