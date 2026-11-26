"""Step 1: deterministic H1 bar backtest on a Nautilus v2 BacktestNode.

Venue: IDEALPRO as NETTING / MARGIN / USD, leverage set explicitly, IBKR FX fee
model, 1-tick probabilistic slippage with a fixed seed, BID+ASK bars only (MID
bars would model a zero spread).
"""

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from nautilus_trader.backtest import (
    BacktestDataConfig,
    BacktestEngineConfig,
    BacktestNode,
    BacktestRunConfig,
    BacktestVenueConfig,
)
from nautilus_trader.common import LoggerConfig, LogLevel
from nautilus_trader.execution import ProbabilisticFillModel
from nautilus_trader.model import (
    Currency,
    InstrumentId,
    LeveragedMarginModel,
    NautilusDataType,
    Venue,
)
from nautilus_trader.persistence import DataCatalogConfig

from spike.ambiguity import SameBarHit, Trade, same_bar_hits
from spike.fees import IbkrFxFeeModel
from spike.jev import JevDispatcher, Verdict
from spike.strategy import Fill, HourModThreeMockJev, SpikeStrategy

EURUSD = InstrumentId.from_str("EUR/USD.IDEALPRO")
VENUE = Venue("IDEALPRO")
USD = Currency.from_str("USD")
LEVERAGE = Decimal(20)  # placeholder; real IBKR FX margin is unverified
SLIPPAGE_PROB = 0.5  # half the market fills slip one tick (0.5 pip), seeded


@dataclass(frozen=True)
class RunResult:
    fills: list[Fill]
    verdicts: list[tuple[int, Verdict]]
    trades: list[Trade]
    same_bar: list[SameBarHit]
    final_balance: str
    total_commission_usd: Decimal


def run_backtest(
    catalog_path: Path, seed: int, sl_pips: int = 30, tp_pips: int = 45, log_level: str = "ERROR"
) -> RunResult:
    catalog = DataCatalogConfig(path=str(catalog_path))
    bar_types = [f"{EURUSD}-1-HOUR-BID-EXTERNAL", f"{EURUSD}-1-HOUR-ASK-EXTERNAL"]
    venue = BacktestVenueConfig(
        name=str(VENUE),
        oms_type="NETTING",
        account_type="MARGIN",
        starting_balances=["1000000 USD"],
        base_currency=USD,
        default_leverage=LEVERAGE,
        # explicit: IB-loaded instruments carry margin 0, so margin = notional / leverage
        margin_model=LeveragedMarginModel(),
        bar_execution=True,
        fill_model=ProbabilisticFillModel(
            prob_fill_on_limit=1.0, prob_slippage=SLIPPAGE_PROB, random_seed=seed
        ),
        fee_model=IbkrFxFeeModel(),
    )
    data = BacktestDataConfig(
        data_type=NautilusDataType.Bar,
        catalog=catalog,
        instrument_id=EURUSD,
        bar_types=bar_types,
    )
    run = BacktestRunConfig(
        venues=[venue],
        data=[data],
        engine=BacktestEngineConfig(logging=LoggerConfig(stdout_level=getattr(LogLevel, log_level))),
        dispose_on_completion=False,
    )
    node = BacktestNode([run])
    node.build()
    strategy = SpikeStrategy(
        EURUSD,
        JevDispatcher(HourModThreeMockJev(), mode="inline"),
        sl_pips=sl_pips,
        tp_pips=tp_pips,
    )
    node.add_strategy(run.id, strategy)
    node.run()

    cache = node.get_engine_cache(run.id)
    account = cache.account_for_venue(VENUE)
    assert account is not None, "backtest venue has no account"
    balance = str(account.balance_total(USD))
    node.dispose()

    commission = sum((f.commission for f in strategy.fills), Decimal(0))
    return RunResult(
        fills=strategy.fills,
        verdicts=strategy.verdicts,
        trades=strategy.trades,
        same_bar=same_bar_hits(strategy.trades, strategy.bid_ranges, strategy.ask_ranges),
        final_balance=balance,
        total_commission_usd=commission,
    )
