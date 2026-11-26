"""Two backtest runs over the same data and seed give identical fills and P&L."""

import random
from decimal import Decimal

from nautilus_trader.model import Bar, BarType, Price, Quantity, Venue
from nautilus_trader.persistence import ParquetDataCatalog
from nautilus_trader.testkit.providers import TestInstrumentProvider

from spike.backtest import run_backtest
from spike.data import with_synthetic_volume

HOUR = 3_600_000_000_000
START = 1_767_225_600 * 1_000_000_000  # 2026-01-01 00:00 UTC


def synthetic_catalog(path, n_bars=600, seed=7):
    """Random-walk EUR/USD H1 with a 1-pip spread, on IB's 0.00005 grid."""
    instrument = TestInstrumentProvider.default_fx_ccy("EUR/USD", Venue("IDEALPRO"))
    rng = random.Random(seed)
    step = Decimal("0.00005")
    mid = Decimal("1.10000")
    bid, ask = [], []
    bid_type = BarType.from_str("EUR/USD.IDEALPRO-1-HOUR-BID-EXTERNAL")
    ask_type = BarType.from_str("EUR/USD.IDEALPRO-1-HOUR-ASK-EXTERNAL")
    for i in range(n_bars):
        o = mid
        c = o + step * rng.randint(-40, 40)
        h = max(o, c) + step * rng.randint(0, 20)
        lo = min(o, c) - step * rng.randint(0, 20)
        ts = START + (i + 1) * HOUR
        for out, bt, off in ((bid, bid_type, -step), (ask, ask_type, step)):
            po, ph, pl, pc = (Price.from_str(f"{x + off:.5f}") for x in (o, h, lo, c))
            out.append(Bar(bt, po, ph, pl, pc, Quantity.from_int(0), ts, ts))
        mid = c
    path.mkdir(parents=True, exist_ok=True)
    catalog = ParquetDataCatalog(str(path))
    catalog.write_instruments([instrument])
    catalog.write_bars(with_synthetic_volume(bid, instrument.size_precision))
    catalog.write_bars(with_synthetic_volume(ask, instrument.size_precision))
    return path


def test_two_runs_with_the_same_seed_give_identical_fills_and_pnl(tmp_path):
    catalog = synthetic_catalog(tmp_path / "catalog")
    first = run_backtest(catalog, seed=42)
    second = run_backtest(catalog, seed=42)

    assert len(first.fills) > 10  # the run actually traded
    assert any(not v.approved for _, v in first.verdicts)  # the mocked Jev rejected some
    assert first.fills == second.fills
    assert first.final_balance == second.final_balance
    assert first.final_balance != "1000000.00 USD"  # fees and P&L moved the balance


def test_a_different_seed_changes_the_slippage(tmp_path):
    catalog = synthetic_catalog(tmp_path / "catalog")
    assert run_backtest(catalog, seed=42).fills != run_backtest(catalog, seed=43).fills
