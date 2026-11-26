"""IBKR FX commission: max(0.20 bp x USD notional, USD 2.00)."""

from decimal import Decimal

import pytest
from nautilus_trader.model import Money, Price, Quantity, Venue
from nautilus_trader.testkit.providers import TestInstrumentProvider

from spike.fees import IbkrFxFeeModel

SIM = Venue("SIM")


def commission(pair: str, qty: int, px: str, usd_rates=None) -> Money:
    instrument = TestInstrumentProvider.default_fx_ccy(pair, SIM)
    model = IbkrFxFeeModel(usd_rates=usd_rates or {})
    return model.get_commission(None, Quantity.from_int(qty), Price.from_str(px), instrument)


def test_usd_quoted_pair_charges_two_tenths_of_a_bp_of_notional():
    # 100k EUR at 1.10000 = 110,000 USD notional -> 2.20 USD
    assert commission("EUR/USD", 100_000, "1.10000") == Money.from_str("2.20 USD")


def test_small_order_pays_the_usd_2_minimum():
    # 25k EUR at 1.1 = 27,500 USD -> 0.55, floored up to 2.00
    assert commission("EUR/USD", 25_000, "1.10000") == Money.from_str("2.00 USD")


def test_usd_base_pair_uses_the_base_quantity_as_usd_notional():
    # 1M USD/JPY -> 1,000,000 USD notional -> 20.00 USD, whatever the yen price
    assert commission("USD/JPY", 1_000_000, "150.000") == Money.from_str("20.00 USD")


def test_cross_converts_quote_notional_to_usd_with_a_given_rate():
    # 500k EUR/GBP at 0.86 = 430,000 GBP; at 1.25 USD/GBP = 537,500 USD -> 10.75 USD
    got = commission("EUR/GBP", 500_000, "0.86000", usd_rates={"GBP": Decimal("1.25")})
    assert got == Money.from_str("10.75 USD")


def test_cross_without_a_usd_rate_refuses_to_guess():
    with pytest.raises(KeyError):
        commission("EUR/GBP", 500_000, "0.86000")
