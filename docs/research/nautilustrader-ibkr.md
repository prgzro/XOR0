# NautilusTrader as the backtest + live engine (IBKR FX and gold)

Can NautilusTrader run Jev Quant's backtest, PAPER and (later) LIVE on IBKR? Researched 2026-11-26 from primary sources only: PyPI metadata, the `nautechsystems/nautilus_trader` repo (tag `v1.231.0`, branches `develop`/`master`/`develop_v1`), the `v1.231.0` wheel source (read, not run), nautilustrader.io docs and GitHub issues. Nothing touched the IB Gateway. **[UNVERIFIED]** marks claims no primary source confirmed. **[INFERRED]** marks my reading of source code that a paper test should confirm.

## TL;DR

- **Two products share one name.** `pip install nautilus_trader` gives **1.231.0** (2026-08-02), the last Cython v1 release. It supports Python 3.12 and its IB adapter runs on `nautilus-ibapi` 10.45.1. The project has already moved to **v2** (a Rust core with PyO3): `2.0.0rc9` (2026-11-10) is on PyPI as a pre-release and needs **Python ≥3.13**. Its IB adapter is rewritten in Rust on the `ibapi` crate. **nautilustrader.io "latest" already documents v2**, so v1 users are reading the wrong docs. v1 gets only critical security backports for about 3 months after the cutover.
- **No conflict with ib_async.** A dry-run resolve of `nautilus_trader[ib]==1.231.0` together with `ib_async==2.0.1` on Python 3.12 succeeds. v2 has no IB Python dependency at all. Keep them in separate processes with distinct client IDs.
- **v2 is blocked on our Python 3.12.3.** It needs a separate 3.13+ venv. uv already has cpython 3.13.0 installed. It also needs Gateway server protocol ≥213. Gateway 10.50 paper is reported working in issues #5350 and #5752, so our 10.50.1h is *probably* fine **[INFERRED]**.
- **FX/gold mapping.** IDEALPRO `CASH` becomes `CurrencyPair` with ID `EUR/USD.IDEALPRO`. `XAUUSD` CMDTY/SMART becomes `Commodity` with ID `XAUUSD.IBCMDTY`, a pseudo-venue. `price_increment` = minTick (0.00005 / 0.005 / 0.01) and `size_increment` = sizeIncrement. **The 25k IDEALPRO minimum, fees and margin are not populated** (`min_quantity=None`, fees 0, margin 0).
- **H1 bars.** `EUR/USD.IDEALPRO-1-HOUR-MID-EXTERNAL` (also BID or ASK) maps to `reqHistoricalData(keepUpToDate=True)` with a backfill of about 300 bars, not `reqRealTimeBars`, which is only used for 5 s bars. The completed bar is published just after the hour. `ts_init` is the bar close.
- **Brackets.** These are supported as native IB parent/child orders through `OrderList`. There are traps. In v1, `OrderFactory.bracket()` defaults `tp_post_only=True` and the IB adapter raises on post-only. In v2 the exits default to reduce-only and the IB adapter denies reduce-only, so you must pass `tp_reduce_only=False, sl_reduce_only=False`. OCA between TP and SL is set explicitly with `IBOrderTags`.
- **Reconciliation exists but is the weakest area.** Startup mass status runs over open orders, executions and positions, plus periodic in-flight/open/position checks. Several **open** v2 IB issues can abort startup reconciliation (#5598, #5428, #5350, #5619), and #5752 leaves rejected orders stuck `ACCEPTED`. Treat restart safety as unproven until tested on paper.
- **Backtest realism is adequate for H1 if configured deliberately.**
  - Spread: feed BID **and** ASK bars. MID bars give a zero spread.
  - Slippage: one-tick `prob_slippage` with `random_seed`.
  - Commission: write a custom `FeeModel`, `max(0.2 bp × notional, USD 2)`. There is no IBKR built-in.
  - Intrabar order: SL/TP touched in the same bar follow a fixed O-H-L-C path, or the adaptive variant.
  - Fills: an order from `on_bar` fills against that bar's close book. There is no next-bar-open mode.
  - Leverage: set margin and leverage explicitly. v1 `default_leverage` is 1.0.
- **Integration.**
  - Kronos, Jev and the Risk Gate fit in one `Strategy`, offloaded with `run_in_executor`. That call runs synchronously in backtest, which makes Jev mocks deterministic.
  - The built-in RiskEngine has **no plugin hook for custom checks**. It offers only rate limits, `max_notional_per_order` and `TradingState` (ACTIVE/REDUCING/HALTED). Our Risk Gate stays our code, and the RiskEngine is a backstop.
- **Verdict.** It is worth a spike for the backtest side, and possibly execution. Don't commit PAPER execution to it until restart/reconciliation, brackets and IDEALPRO rejects have been exercised on the paper account. Spike on v2 (rc9 or 2.0.0 final) in a Python 3.13 venv, not on the end-of-life v1.

## Versions

| Item | Value | Source |
|---|---|---|
| Latest stable (PyPI) | **1.231.0**, 2026-08-02. Requires Python `>=3.12,<3.15`. Wheels cp312-cp314, manylinux_2_35 | [PyPI JSON](https://pypi.org/pypi/nautilus_trader/json), [release v1.231.0](https://github.com/nautechsystems/nautilus_trader/releases/tag/v1.231.0) |
| Latest pre-release (PyPI) | **2.0.0rc9**, 2026-11-10. Requires Python `>=3.13,<3.16`. Wheels cp313-cp315, manylinux_2_34. No extras except `visualization` | [PyPI 2.0.0rc9](https://pypi.org/pypi/nautilus_trader/2.0.0rc9/json), [releases](https://github.com/nautechsystems/nautilus_trader/releases) |
| Branches | `develop` = 2.0.0rc10, `master` = 2.0.0rc9, `nightly` = 2.0.0, `develop_v1` = 1.231.0 | `version.json` on each branch ([develop](https://raw.githubusercontent.com/nautechsystems/nautilus_trader/develop/version.json), [nightly](https://raw.githubusercontent.com/nautechsystems/nautilus_trader/nightly/version.json), [develop_v1](https://raw.githubusercontent.com/nautechsystems/nautilus_trader/develop_v1/version.json)) |
| Cadence | v1: 10 releases from 1.222.0 (2026-01-02) to 1.231.0 (2026-08-02), every 2-6 weeks. v2 RCs: rc3 (08-21) to rc9 (11-10), about every 2 weeks. 2.0.0 final is not on PyPI as of 2026-11-26 | PyPI upload times |
| v1 IB extra | `nautilus_trader[ib]` pulls `nautilus-ibapi==10.45.1` (IB's `ibapi` repackaged; the import name is `ibapi`), `protobuf==5.29.6` and `defusedxml`. `[docker]` adds `docker` | PyPI `requires_dist`; [v1 IB docs § Installation](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/docs/integrations/ib.md#installation) |
| v2 IB client | Rust `ibapi` crate. The docs say "pinned `ibapi 4.0.1`" and require **server protocol ≥213** | [crate README](https://github.com/nautechsystems/nautilus_trader/blob/develop/crates/adapters/interactive_brokers/README.md), [v2 IB docs](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/integrations/interactive_brokers.md#connect-to-tws-or-ib-gateway), [#4796](https://github.com/nautechsystems/nautilus_trader/issues/4796) |
| Our env | Python 3.12.3, ib_async 2.0.1, Gateway 10.50.1h / IBC 3.24.2, glibc 2.39 (meets both wheels' floors), uv with cpython 3.13.0 available | [ibkr-paper-connection.md](ibkr-paper-connection.md), local `ldd`/`uv` |
| Co-install check | `pip install --dry-run "nautilus_trader[ib]==1.231.0" "ib_async==2.0.1"` on Python 3.12 resolves cleanly (pandas 3.1.1, pyarrow 26.0.1, numpy 2.5.5, aeventkit 2.1.0) | Local dry run on 2026-11-26; nothing installed or run |

## 1. Which version to use

- 1.231.0 is "intended to be the final NautilusTrader 1.x release with support for the legacy Cython v1 core". The v2 runtime is at release-candidate stage for strategy authoring, backtest, live, risk and execution, portfolio, catalog and the current adapters. ([RELEASES.md § 1.231.0](https://github.com/nautechsystems/nautilus_trader/blob/develop/RELEASES.md))
- "Legacy v1 lives on `develop_v1` and receives only critical security backports for approximately three months after the v2 cutover." Both versions import as `nautilus_trader`, so they need separate venvs. ([MIGRATION_V2.md](https://github.com/nautechsystems/nautilus_trader/blob/develop/MIGRATION_V2.md#migrate-from-v1-to-v2))
- The v2 install command is `uv pip install --pre nautilus_trader`. ([MIGRATION_V2.md § Install v2](https://github.com/nautechsystems/nautilus_trader/blob/develop/MIGRATION_V2.md#install-v2)) The v2 docs list Python 3.13-3.15 and glibc ≥2.35. ([installation.md](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/getting_started/installation.md))
- **Docs trap.** [nautilustrader.io/docs/latest/integrations/interactive_brokers](https://nautilustrader.io/docs/latest/integrations/interactive_brokers) already shows the v2 adapter: `host`/`port`, `dockerized_gateway` "Reserved and rejected", protocol 213. For v1 use the tag copy, [`docs/integrations/ib.md@v1.231.0`](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/docs/integrations/ib.md), which uses `ibg_host`, `ibg_port` and `HistoricInteractiveBrokersClient`.
- **ib_async coexistence.** ib_async 2.0.1 depends only on `aeventkit` and `nest_asyncio` ([PyPI](https://pypi.org/pypi/ib_async/2.0.1/json)). There is no package clash. Run the existing ib_async probe and download scripts in their own process. `nest_asyncio` patching the loop inside a Nautilus process is untested **[UNVERIFIED]**. IB allows up to 32 API clients per session, so give each process a distinct `clientId` ([ibkr-api-and-products.md](ibkr-api-and-products.md)).
- **v2 adds no IB Python dependency.** Any conflict risk moves to Python 3.13 itself. Whether Kronos's torch stack is fine on 3.13 is **[UNVERIFIED]**.

## 2. IB adapter: FX and XAUUSD instruments, symbology, bars

**Symbology** (`IB_SIMPLIFIED` is the default):
- Forex is `{symbol}/{currency}.{exchange}`, for example `EUR/USD.IDEALPRO`. ([v1 docs § Symbology](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/docs/integrations/ib.md#symbology))
- Commodities use the self-named pseudo-venue `IBCMDTY`, which maps to SMART. Spot gold is therefore `XAUUSD.IBCMDTY` (simplified) or `XAUUSD=CMDTY.IBCMDTY` (raw). ([instruments.py L235-L239](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/adapters/interactive_brokers/parsing/instruments.py#L235-L239), [L1383-L1397](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/adapters/interactive_brokers/parsing/instruments.py#L1383-L1397), [L1536-L1547](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/adapters/interactive_brokers/parsing/instruments.py#L1536-L1547))
- v2 documents the same `XAUUSD.IBCMDTY`. ([v2 docs § Symbology](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/integrations/interactive_brokers.md#symbology-and-instruments))

**Contracts:** `IBContract(secType="CASH", exchange="IDEALPRO", symbol="EUR", currency="USD")` and `IBContract(secType="CMDTY", symbol="XAUUSD", exchange="SMART")`. ([v1 docs § IBContract examples](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/docs/integrations/ib.md#ibcontract-examples-by-asset-class))

**Provider:** `InteractiveBrokersInstrumentProviderConfig(load_ids=frozenset({"EUR/USD.IDEALPRO", ...}), symbology_method=..., cache_validity_days=...)`. ([v1 docs § InstrumentProvider configuration](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/docs/integrations/ib.md#instrumentprovider-configuration)) v2 renames the field to `load_ids`, which takes `InstrumentId`s, and has `cache_path`. ([MIGRATION_V2 § Interactive Brokers](https://github.com/nautechsystems/nautilus_trader/blob/develop/MIGRATION_V2.md#interactive-brokers))

**Increments:**

| Field | CurrencyPair (`parse_forex_contract`) | Commodity |
|---|---|---|
| Price precision and increment | from `minTick`, so 0.00005 or 0.005 for our pairs | `minTick` (0.01) |
| Size | precision from `minSize`, `size_increment` = `sizeIncrement` | `size_increment` = `sizeIncrement` (1 oz) |
| `min_quantity` | `None` | `None` |
| `margin_init`, `maker_fee`, `taker_fee` | 0 | 0 |
| Source | [L524-L556](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/adapters/interactive_brokers/parsing/instruments.py#L524-L556) | [L654-L686](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/adapters/interactive_brokers/parsing/instruments.py#L654-L686) |

The **IDEALPRO 25k minimum (odd lots) and all costs are therefore the Risk Gate's job**. The live instrument doesn't carry them.

**v2 FX price rounding:** IB sends IDEALPRO prices finer than minTick. v2 rounds bid down and ask up to the increment, and rounds mid/last to nearest (ties to even). It applies this to quotes, historical ticks and bid/ask bars. MID bars that feed Kronos are therefore quantized to half-pips. ([v2 docs § Data capabilities](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/integrations/interactive_brokers.md#data-capabilities), fixed in [#5298](https://github.com/nautechsystems/nautilus_trader/issues/5298)) v1 has no such rounding **[INFERRED]**.

**Bar types:**
- Price types MID → `MIDPOINT`, BID → `BID`, ASK → `ASK`, LAST → `TRADES`. FX has no TRADES. ([parsing/data.py L44-L57](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/adapters/interactive_brokers/parsing/data.py#L44-L57))
- Bar type string: `EUR/USD.IDEALPRO-1-HOUR-MID-EXTERNAL`.

**Live H1 subscription (v1):**
- A 5-second bar uses `reqRealTimeBars`. Anything else uses `reqHistoricalData(..., keepUpToDate=True)` with a duration of about 300 bars. ([data.py L265-L290](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/adapters/interactive_brokers/data.py#L265-L290), [market_data.py L473-L571](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/adapters/interactive_brokers/client/market_data.py#L473-L571))
- After a disconnect or data-farm outage, the filter cutoff moves back, so missed bars are backfilled on resubscribe. (same lines)
- With `handle_revised_bars=False`, the previous bar is published when the next bar's first update arrives, with a fallback timeout of the bar duration + 1 s. ([L1292-L1330](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/adapters/interactive_brokers/client/market_data.py#L1292-L1330), [L1355-L1431](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/adapters/interactive_brokers/client/market_data.py#L1355-L1431))
- `ts_init` = IB bar start + interval, i.e. the bar close. ([L1640-L1660](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/adapters/interactive_brokers/client/market_data.py#L1640-L1660))

**Live H1 subscription (v2):** the bar is published when IB's final update arrives, about 0.5 s after the close, or 2 s after the close. The optional `subscription_idle_timeout_secs` emits `InteractiveBrokersSubscriptionIdle` events, which are usable as a stale-data signal. ([v2 docs § Configuration reference](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/integrations/interactive_brokers.md#configuration-reference))

**IDEALPRO session bar [INFERRED, verify]:** IB's H1 grid has a **:15 session-open bar** (22:15/21:15 UTC; see [ibkr-paper-connection.md](ibkr-paper-connection.md)). Its start + 1 h gives a `ts_init` 15 min *after* the next bar's start, so expect one misaligned bar per day and check how the adapter orders them.

**Warmup:** `request_bars` from the strategy is supported, so the 400 Kronos lookback bars can be loaded on start. ([data.py L612](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/adapters/interactive_brokers/data.py#L612))

**Data client settings:**
- `market_data_type` defaults to `REALTIME`. FX and XAUUSD stream real-time on our paper account.
- `use_regular_trading_hours` **defaults to True**. Set it to False for 24h FX/gold. What it does for CASH is **[UNVERIFIED]**. ([config.py L244-L252](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/adapters/interactive_brokers/config.py#L244-L252))
- The adapter expects TWS/Gateway to return **market data timestamps in UTC** ("must be enabled by the user"). ([v1 docs § Getting started](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/docs/integrations/ib.md#getting-started)) Our compose sets `TZ`/`TIME_ZONE=Etc/UTC`, but whether that equals the Gateway API's UTC setting is **[UNVERIFIED]**.

## 3. Bracket orders (entry + SL + TP)

**Order types:** MKT, LMT, STP, STP LMT, MIT, LIT, trailing stop and trailing stop-limit, plus MOC/LOC through `AT_THE_CLOSE`. TIFs are DAY, GTC, IOC, FOK, GTD and OPG. v2 adds market-to-limit. ([v1 docs § Supported order types](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/docs/integrations/ib.md#supported-order-types), [v2 docs § Order types](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/integrations/interactive_brokers.md#order-types))

**v1 mechanics:**
- `SubmitOrderList` maps each order. Nautilus `parent_order_id` maps to IB `parentId`. Every leg gets `transmit=False` except the last, which is IB's native bracket pattern.
- If any leg fails translation, all legs are rejected. ([execution.py L1035-L1095](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/adapters/interactive_brokers/execution.py#L1035-L1095), [parsing/execution.py L73-L88](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/adapters/interactive_brokers/parsing/execution.py#L73-L88))
- **OCA is opt-in:** the docs say to add `IBOrderTags(ocaGroup=..., ocaType=1)` to `tp_tags` and `sl_tags`. ([v1 docs § OCA](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/docs/integrations/ib.md#oca-one-cancels-all-orders), [execution.py L1306-L1358](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/adapters/interactive_brokers/execution.py#L1306-L1358))

**v1 trap:**
- `OrderFactory.bracket()` defaults `tp_post_only=True`. ([factories.pyx L1193-L1225](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/common/factories.pyx#L1193-L1225))
- The IB adapter raises "`post_only` not supported". ([execution.py L1209-L1210](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/adapters/interactive_brokers/execution.py#L1209-L1210), [#4437](https://github.com/nautechsystems/nautilus_trader/issues/4437))
- **Always pass `tp_post_only=False`.**

**v2 trap:**
- Factory brackets make TP and SL **reduce-only**. The adapter "rejects post-only and reduce-only orders" and denies the whole list.
- Pass `tp_reduce_only=False, sl_reduce_only=False`.
- Warning from the docs: "IB does not cancel bracket exits when another order closes the position, so a later exit fill opens a position in the opposite direction." ([v2 docs § Commands and order attributes](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/integrations/interactive_brokers.md#commands-and-order-attributes), [#5464](https://github.com/nautechsystems/nautilus_trader/issues/5464))

**IDEALPRO specifics:**
- Whether IB simulates stops on IDEALPRO is still **[UNVERIFIED]** ([ibkr-api-and-products.md § 5](ibkr-api-and-products.md)). The Risk Gate should budget stop slippage.
- Open v2 bug [#5752](https://github.com/nautechsystems/nautilus_trader/issues/5752) (2026-11-23): on a paper account, an `EUR/USD.IDEALPRO` 1,000-unit market order that IB accepted and then rejected ("[201] ... currency leverage") stays `ACCEPTED`, and the cancel fails. That bites exactly our odd-lot paper tests.

## 4. Reconciliation on restart

**Engine (`LiveExecEngineConfig`):**

| Option | Default |
|---|---|
| `reconciliation` | True |
| `reconciliation_lookback_mins` | None (max available) |
| `reconciliation_instrument_ids` | None |
| `filter_unclaimed_external_orders`, `filter_position_reports` | False |
| `generate_missing_orders` | True |
| `inflight_check_*` | interval 2 s / threshold 5 s / 5 retries |
| `open_check_interval_secs` | off by default |
| `position_check_interval_secs` | off by default |
| `reconciliation_startup_delay_secs` | 10 |

Source: [live/config.py L84-L215](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/live/config.py#L84-L215).

**Procedure:**
- The engine requests order, fill and position reports, then reconciles in that order.
- Venue orders unknown to the cache become strategy `EXTERNAL`. Position gaps get generated LIMIT orders tagged `RECONCILIATION`.
- A strategy re-adopts orders and positions with `external_order_claims=[instrument_ids]`.
- "If reconciliation fails, the system logs an error and does not start", which is the fail-closed behaviour we want.
- Tip from the docs: persist all execution events to the cache database. ([reconciliation.md@v1.231.0](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/docs/concepts/reconciliation.md), [trading/config.py L51-L58](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/trading/config.py#L51-L58))

**IB v1:**
- Open orders come from `reqOpenOrders`, which covers only this clientId, or from `reqAllOpenOrders` with `fetch_all_open_orders=True`. Fills come from `reqExecutions` and positions from `reqPositions`.
- On startup, positions also become synthetic filled order reports.
- A disconnect mid-request raises instead of reporting a false discrepancy. ([execution.py L532-L600](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/adapters/interactive_brokers/execution.py#L532-L600), [L660-L710](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/adapters/interactive_brokers/execution.py#L660-L710), [L909-L960](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/adapters/interactive_brokers/execution.py#L909-L960), [client/order.py L114-L141](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/adapters/interactive_brokers/client/order.py#L114-L141))
- How far back IB's `reqExecutions` reaches (commonly "current day") is **[UNVERIFIED]**. Brackets older than that rely on position reports plus the persisted cache.

**IB v2:**
- Fills are executions paired with commission reports.
- The engine adopts a position from the position report alone. IB `avgCost` includes commission, so the adapter replays fills to match it.
- Orders left working by a previous session come back as external open orders, resolved through `PERM-` venue order IDs. ([v2 docs § Reconciliation](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/integrations/interactive_brokers.md#reconciliation))

**Known gaps (open on 2026-11-26):**
- [#5598](https://github.com/nautechsystems/nautilus_trader/issues/5598): a filled IOC still listed `PendingCancel`, or a negative avgCost, aborts startup.
- [#5428](https://github.com/nautechsystems/nautilus_trader/issues/5428): avg-entry-price mismatch refuses startup.
- [#5350](https://github.com/nautechsystems/nautilus_trader/issues/5350): an execution without a commission report aborts startup. This was seen on **Gateway 10.50 paper**.
- [#5619](https://github.com/nautechsystems/nautilus_trader/issues/5619): an uncached BAG order report aborts startup.
- Recently closed: [#5512](https://github.com/nautechsystems/nautilus_trader/issues/5512) (with a lookback set, filled orders returned `ACCEPTED`), [#5060](https://github.com/nautechsystems/nautilus_trader/issues/5060), [#4970](https://github.com/nautechsystems/nautilus_trader/issues/4970) (duplicate reconciliation order), and v1 [#3176](https://github.com/nautechsystems/nautilus_trader/issues/3176) (duplicate orders on restart with a Redis cache plus claims).

**Implication:** keep our own journal as the source of truth for Candidate → order mapping. Configure `external_order_claims`, persist the cache, and test kill/restart with an open bracket on paper.

## 5. Connecting to our gnzsnz Gateway

**v1 `DockerizedIBGateway`:**
- It starts its **own** container from `ghcr.io/gnzsnz/ib-gateway:stable`, a floating tag, with `restart_policy=always` and `EXISTING_SESSION_DETECTED_ACTION=primary`. It maps internal 4004/4003. ([config.py L60-L68](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/adapters/interactive_brokers/config.py#L60-L68), [gateway.py L165-L190](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/adapters/interactive_brokers/gateway.py#L165-L190))
- That contradicts our pinned 10.50.1h, `restart: "no"` lockout guard and manual session handling. `primary` logs out other sessions.
- **Don't use it.**

**v2:** client configs reject a non-None `dockerized_gateway` ("start the gateway outside v2, then pass its host and port"). ([MIGRATION_V2 § Interactive Brokers](https://github.com/nautechsystems/nautilus_trader/blob/develop/MIGRATION_V2.md#interactive-brokers))

**Use our existing Gateway:**
- v1: `ibg_host="127.0.0.1", ibg_port=4002`. `ibg_port` defaults to None, so set it explicitly.
- v2: `host`/`port`, which default to 127.0.0.1:4002. ([exec config L297-L305](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/adapters/interactive_brokers/config.py#L297-L305), [crate README § Default ports](https://github.com/nautechsystems/nautilus_trader/blob/develop/crates/adapters/interactive_brokers/README.md#default-ports))
- Paper vs live is decided only by the Gateway's `TRADING_MODE` and port, plus `account_id` (a `DU…` account, from env `TWS_ACCOUNT` in v1). Keep the account ID in `.env`.

**Client IDs:**
- Use separate IDs for the data client, the exec client, the historical client and the ib_async scripts. Our probes used 17 and 18.
- v1: on error 326 the adapter retries the same ID, then falls back within a band. Reserve contiguous bands per client. Open-order visibility is per clientId. ([v1 docs § Client ID allocation](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/docs/integrations/ib.md#client-id-allocation))
- v2: an exec `client_id` must not be a multiple of 1000, because order IDs are partitioned by `client_id % 1000`. IB error 103 forbids reusing order IDs across sessions. ([v2 docs § Dockerized IB Gateway](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/integrations/interactive_brokers.md#dockerized-ib-gateway))

**Read-only API:**
- Our Gateway runs `READ_ONLY_API=yes`, and IBKR says order information is unavailable to the API in that mode ([ibkr-api-and-products.md](ibkr-api-and-products.md)).
- v2's exec client reads open and completed orders on connect, so an exec client against a read-only Gateway may fail to start **[UNVERIFIED]**.
- For SIGNAL_ONLY, run a **data-client-only** node. Flip read-only off only for the PAPER phase.

## 6. Historical data → Parquet catalog

**IB → catalog (v1):**
- `HistoricInteractiveBrokersClient(host, port, client_id)`, then `request_instruments`, `request_bars(bar_specifications=["1-HOUR-MID", ...], start_date_time/end_date_time or duration, contracts=..., use_rth=False)`, then `ParquetDataCatalog(path).write_data(...)`. ([v1 docs § Historical data](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/docs/integrations/ib.md#historical-data-and-backtesting))
- The v1 historical client has **no pacing logic** of its own ([historical/client.py L185-L300](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/adapters/interactive_brokers/historical/client.py#L185-L300)). Respect IB's 60 requests per 10 min ourselves.

**IB → catalog (v2):** `HistoricalInteractiveBrokersClient(provider, data_config)` connects on construction. Then `request_bars(...)` and `catalog.write_bars(...)` / `write_instruments(...)`. ([v2 example historical_download.py](https://github.com/nautechsystems/nautilus_trader/blob/develop/examples/live/interactive_brokers/historical_download.py), [v2 catalog § Writing data](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/concepts/data/catalog.md#writing-data))
- Recently fixed: [#5384](https://github.com/nautechsystems/nautilus_trader/issues/5384), where requests with a start time missed bars between duration segments (closed 2026-11-14).
- Still open: [#5472](https://github.com/nautechsystems/nautilus_trader/issues/5472) (`update_catalog` does not persist historical requests).
- **Alternative:** keep our working ib_async downloader ([ibkr-paper-connection.md](ibkr-paper-connection.md)) and only convert its output with the steps below.

**Our XM H1 CSV → catalog (v1 API):**
1. Convert XM server time (EET/EEST, EU DST) to UTC.
2. Build a DataFrame with a UTC `timestamp` index and `open, high, low, close, volume` columns.
3. Run `BarDataWrangler(bar_type, instrument).process(df, ts_init_delta=3_600_000_000_000)`. XM bars are stamped at the **open**, and `ts_init` must be the **close**.
4. Run `catalog.write_data([instrument])` and `catalog.write_data(bars)`.

Sources: [wranglers.pyx L704-L731](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/persistence/wranglers.pyx#L704-L731), [bar-execution.md § Bar timestamp convention](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/docs/concepts/backtesting/bar-execution.md#bar-timestamp-convention). v2's `BarDataWrangler` takes explicit `ts_event`/`ts_init` instead of `ts_init_delta` (same doc).

Caveats for XM data:
- **XM data is bid-only**, about 1.1 pip below IBKR mid.
- Use a separate instrument and venue (e.g. `EUR/USD.XM`) with `price_increment=0.00001`. XM prices are not on IB's 0.00005 grid, and bar precision must equal instrument precision or the matching engine raises. ([engine.pyx L4760-L4780](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/backtest/engine.pyx#L4760-L4780))
- Optionally synthesize ASK bars = bid + a spread estimate.

## 7. Backtest realism for FX

**Spread with bars (v1 source):**
- A `MID` or `LAST` bar is processed as trade ticks, so there is **no spread**.
- `BID` and `ASK` bars with equal `ts_init` are combined into quote ticks, which gives a real bid/ask spread. ([engine.pyx L4803-L4815](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/backtest/engine.pyx#L4803-L4815), [L4950-L4955](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/backtest/engine.pyx#L4950-L4955))
- The execution bar type per instrument switches to any bar type with a timedelta ≤ the current one. **Feeding H1 MID + BID + ASK to one venue therefore interleaves zero-spread MID processing** **[INFERRED]** ([L4783-L4798](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/backtest/engine.pyx#L4783-L4798)).
- Recommendation: give the venue BID+ASK, and compute mid in the strategy or feed MID as non-execution data.
- An alternative is `QuoteTickDataWrangler.process_bar_data(bid_data, ask_data, ...)`. ([wranglers.pyx L357](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/persistence/wranglers.pyx#L357))

**Bar execution:**
- Execution needs `bar_execution=True`, `L1_MBP` and `EXTERNAL` bars.
- Each bar is split into an O→H→L→C path, or the adaptive path that visits the extreme nearer the open first (`bar_adaptive_high_low_ordering`).
- Orders placed in `on_bar(N)` settle against bar N's close book. There is **no native next-bar-open fill**. A latency model pushes fills later. ([bar-execution.md](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/docs/concepts/backtesting/bar-execution.md))
- Same-bar SL/TP ambiguity is therefore resolved by a heuristic. Count it in the pre-registration.

**Fill models and slippage:**
- The default is `prob_fill_on_limit=1.0, prob_slippage=0.0`. `prob_slippage` moves an L1 fill by one tick, which is 0.5 pip on IB's increment.
- `random_seed` makes runs reproducible.
- Built-ins include `OneTickSlippageFillModel`, `ProbabilisticFillModel` and `MarketHoursFillModel`, among others. ([fill-models.md](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/docs/concepts/backtesting/fill-models.md), [fill.pyx](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/backtest/models/fill.pyx))
- The odd-lot penalty (1-3 ticks) can be modelled with `prob_slippage=1.0` or a custom `FillModel`.

**Fees:**
- Built-ins are `MakerTakerFeeModel` (uses the instrument's maker/taker rates, which are 0 for IB instruments), `FixedFeeModel` and `PerContractFeeModel`.
- **There is no IBKR FX model.** Subclass `FeeModel.get_commission(order, fill_qty, fill_px, instrument)` to return `max(0.20 bp × USD notional, USD 2.00)`. For gold, use 1.5 bp with the same USD 2 minimum. Convert JPY/CHF/CAD/GBP-quoted notionals to USD. ([fee.pyx L33-L65](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/backtest/models/fee.pyx#L33-L65); rates from [ibkr-api-and-products.md](ibkr-api-and-products.md))
- v2 accepts custom Python `FeeModel` subclasses and requires an explicit `fee_model` per venue. ([RELEASES.md #4806](https://github.com/nautechsystems/nautilus_trader/blob/develop/RELEASES.md), [apis-and-runs.md](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/concepts/backtesting/apis-and-runs.md))

**Venue:**
- Use `oms_type=NETTING`, which matches IB's account-level net position and our "one position per symbol" rule.
- Use `account_type=MARGIN` with `base_currency="USD"`.
- Set `default_leverage` and `leverages` explicitly. v1's default is 1.0 and v2's margin-account default is 10x.
- Keep `support_contingent_orders=True` and `use_reduce_only`. ([backtest/config.py L149-L189](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/backtest/config.py#L149-L189), [MIGRATION_V2 § Backtest models](https://github.com/nautechsystems/nautilus_trader/blob/develop/MIGRATION_V2.md#backtest-models-and-settlement))
- Overnight swap can be modelled with `FXRolloverInterestModule`, which needs a rate series. ([modules.pyx L92](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/backtest/modules.pyx#L92))
- Realistic IBKR spot-FX margin is still **[UNVERIFIED]**.

**Determinism:** the engine is event-driven and single-threaded. With a fixed `random_seed`, the same data and seed give the same run **[INFERRED from the fill-model docs; verify with a double run]**.

## 8. Integration points: Kronos, Jev, Risk Gate

**Where code goes:**
- One `Strategy` subscribes to H1 bars for all 12 instruments. `on_bar` assembles the closed-bar window from the cache.
- Callbacks run **synchronously** on the event thread and "must return promptly". Blocking I/O or model inference must be offloaded. ([v2 python.md](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/concepts/python.md#user-components), [configure_live_trading.md](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/how_to/configure_live_trading.md))
- An `Actor` (v2 `DataActor`) can host Kronos and publish forecasts as custom data or signals. Splitting them is optional.

**Offloading:**
- v1 `Actor.run_in_executor` / `queue_for_executor` run the callable in a thread pool when live. **In backtests they run it immediately and synchronously.** ([actor.pyx L992-L1100](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/common/actor.pyx#L992-L1100))
- So the same pipeline code runs in both modes: Kronos, then Jev with a hard HTTP timeout (e.g. `httpx` with `timeout=`), then the Risk Gate.
- In backtest, inject a mock/replay Jev client by config. Its outcome is deterministic and costs zero latency, which is optimistic, so add a modelled delay if that matters.
- The executor "is not fully thread-safe": only `queue_for_executor` is safe off-thread, and other methods must be called from the loop thread. ([common/executor.py L83-L86](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/common/executor.py#L83-L86))
- **Don't call `submit_order` from the worker thread.** Return the verdict to a thread-safe queue that a strategy timer drains on the event thread. Re-check bar age, connection and trading state there before submitting. This is the fail-closed choke point. *(This is my design; the docs do not prescribe it.)*

**RiskEngine as backstop:**
- `RiskEngineConfig` has only `bypass`, `max_order_submit_rate`, `max_order_modify_rate`, `max_notional_per_order` and `debug`. **There is no hook for custom checks.** ([risk/config.py](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/risk/config.py))
- Built-in checks cover price and quantity precision, GTD, reduce-only, max notional per order and instrument min/max notional, free balance for non-margin accounts, rate limits and trading state. ([engine.pyx L584-L680](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/risk/engine.pyx#L584-L680), [L905-L975](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/risk/engine.pyx#L905-L975), [v2 execution § Risk engine](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/concepts/execution/index.md#risk-engine))
- **Our Risk Gate stays a pure module called from the Strategy before `submit_order_list`.** Nautilus's RiskEngine is the second line, with `max_notional_per_order` set per instrument.
- Our Risk Gate could also be wrapped as an `ExecutionAlgorithm`, which sits before the RiskEngine, but that adds complexity for no gain **[my assessment]**.

**Trading state:**
- `HALTED` allows cancels and queries only. `REDUCING` allows only eligible individual reduce-only submits. ([v2 execution § Trading state](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/concepts/execution/index.md#trading-state), [v1 engine.pyx L228-L258, L550-L580](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/risk/engine.pyx#L228-L258))
- **Conflict [INFERRED]:** the v2 IB adapter denies reduce-only orders. `REDUCING` therefore cannot pass exits to IB, so use `HALTED` as the kill switch and handle exits through existing bracket legs.
- In v1, `set_trading_state` lives on the kernel's RiskEngine and has no `Strategy` method. The equivalent public v2 API is **[UNVERIFIED]**.

**Disconnects:** v1 rejects order requests when the client isn't ready (`_ensure_client_ready_for_order_request`, [execution.py L1035-L1047](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/adapters/interactive_brokers/execution.py#L1035-L1047)). Data-farm flaps (2103/2105) degrade feeds without dropping the order channel ([v1 docs § Connection management](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/docs/integrations/ib.md#connection-management)). Our own stale-bar check stays mandatory.

**Same code in backtest and live:**
- The strategy, the Risk Gate and the Jev client interface are shared.
- Only the node differs: `BacktestEngine` (v1/v2) or `BacktestNode`, versus `TradingNode` (v1) or `LiveNode` (v2).
- The Jev implementation is chosen by config.

## 9. Known issues and stability notes (IB + FX/gold)

| Issue | State | Relevance |
|---|---|---|
| [#5752](https://github.com/nautechsystems/nautilus_trader/issues/5752) IB rejects after accepting, so the order stays ACCEPTED and cannot be canceled | open (11-23) | EUR/USD paper, error 201 "currency leverage" |
| [#5598](https://github.com/nautechsystems/nautilus_trader/issues/5598), [#5428](https://github.com/nautechsystems/nautilus_trader/issues/5428), [#5350](https://github.com/nautechsystems/nautilus_trader/issues/5350), [#5619](https://github.com/nautechsystems/nautilus_trader/issues/5619) startup reconciliation aborts | open | Restart safety (§4). #5350 was on Gateway 10.50 paper |
| [#5472](https://github.com/nautechsystems/nautilus_trader/issues/5472) historical requests not persisted by `update_catalog` | open | Catalog workflow |
| [#5464](https://github.com/nautechsystems/nautilus_trader/issues/5464) / [#5459](https://github.com/nautechsystems/nautilus_trader/issues/5459) factory brackets denied (reduce-only) | closed 11-07 (documented workaround) | Brackets (§3) |
| [#5298](https://github.com/nautechsystems/nautilus_trader/issues/5298) FX prices off the 0.00005 increment, so the sandbox skipped fills | closed 10-18 | FX tick grid |
| [#5384](https://github.com/nautechsystems/nautilus_trader/issues/5384) historical bars missing between segments | closed 11-14 | History pulls |
| [#5281](https://github.com/nautechsystems/nautilus_trader/issues/5281) Gateway 10.51+ protobuf `lastTradeDate` error 10372 | closed 10-16 | Gateway upgrades |
| [#4796](https://github.com/nautechsystems/nautilus_trader/issues/4796) v2 needs server protocol ≥213; Gateway 10.41 (187) fails | closed (docs) | Our 10.50.1h likely OK (#5350, #5752 ran on 10.50) |
| [#4437](https://github.com/nautechsystems/nautilus_trader/issues/4437) `tp_post_only` default breaks IB brackets | closed 07-16 | v1 brackets |
| [#3176](https://github.com/nautechsystems/nautilus_trader/issues/3176) duplicate orders on restart (Redis + claims) | closed 2025-12 | v1 restart |

**Stability:**
- The IB adapter is under heavy churn: v2 IB was refactored in [#5041](https://github.com/nautechsystems/nautilus_trader/pull/5041), and rc9 and rc10 notes carry many IB fixes and breaking changes ([RELEASES.md](https://github.com/nautechsystems/nautilus_trader/blob/develop/RELEASES.md)).
- Pin exact versions and re-read the notes on each bump.
- Spot gold (`CMDTY`) has no dedicated issues. Its support dates from [#1605](https://github.com/nautechsystems/nautilus_trader/issues/1605) (2024) and is otherwise untested by us.

## 10. Verdict

**Risks:**
1. The v1/v2 transition. v1 is frozen and v2 is still RC, needs Python ≥3.13 and is the target of the docs site.
2. Restart reconciliation, with open abort bugs.
3. Bracket semantics: no reduce-only, explicit OCA, and IB not cancelling exits when the position is closed elsewhere.
4. IDEALPRO odd-lot and leverage rejects (#5752).
5. Bar-backtest optimism: same-bar SL/TP order and close-of-bar fills.
6. The `:15` session bar alignment.

**Unknowns to verify on paper:**
- The Gateway server protocol version is ≥213. Check it with the v2 client's explicit error.
- The data client works on the **read-only** Gateway. Whether the exec client tolerates read-only is a separate check.
- The `XAUUSD.IBCMDTY` ID resolves, and H1 MID/BID/ASK bars stream for all 12 instruments with `use_regular_trading_hours=False`. Measure bar publish latency after the hour, and check how the 22:15 bar is timestamped.
- UTC timestamp setting: compare against the ib_async bars already saved.
- (PAPER phase, read-only off) Test brackets:
  - a 25k EURUSD bracket with OCA tags, and that TP fill cancels SL;
  - a sub-25k odd-lot order;
  - kill and restart with the bracket open, then reconciliation with `external_order_claims`;
  - a rejected order's terminal state.
- How far back `reqExecutions` reaches, and the cache-persistence choice (Redis/PostgreSQL).

**Minimal spike, about 1-2 days, scratchpad only, no orders until the PAPER ticket:**
1. `uv venv --python 3.13` and `uv pip install --pre "nautilus_trader==2.0.0rc9"`, or 2.0.0 final if it has shipped. Pin it.
2. **Backtest leg.**
   - Load the existing IBKR EURUSD H1 BID+ASK history, or pull it, into a catalog. Set `ts_init` = close.
   - Run a dummy strategy that places one bracket per signal with a mock Jev through `run_in_executor`.
   - Use the custom IBKR `FeeModel`, `prob_slippage` with a seed, and a NETTING/MARGIN venue.
   - Run it twice and diff the results for determinism. Compare MID-only and BID+ASK spread costs.
3. **Live data leg.** Run a data-only `LiveNode` against `127.0.0.1:4002` with a new client ID band (e.g. 30-39). Subscribe to 12 × `1-HOUR-MID-EXTERNAL` plus `request_bars(400)` and log `ts_event`/`ts_init`/receipt time over a few H1 closes. Leave the exec client out.
4. Go/no-go: if steps 2 and 3 are clean, schedule the PAPER bracket and restart tests above. If v2 looks too unstable, the fallback is **Nautilus for backtest only**, with execution on our own thin ib_async layer (`bracketOrder()` plus our journal reconciliation).

## Sources

- PyPI: [nautilus_trader](https://pypi.org/project/nautilus_trader/) ([JSON](https://pypi.org/pypi/nautilus_trader/json), [2.0.0rc9 JSON](https://pypi.org/pypi/nautilus_trader/2.0.0rc9/json)), [nautilus-ibapi](https://pypi.org/project/nautilus-ibapi/), [ib_async 2.0.1](https://pypi.org/project/ib_async/2.0.1/)
- Releases and changelog: [GitHub releases](https://github.com/nautechsystems/nautilus_trader/releases), [RELEASES.md](https://github.com/nautechsystems/nautilus_trader/blob/develop/RELEASES.md), [MIGRATION_V2.md](https://github.com/nautechsystems/nautilus_trader/blob/develop/MIGRATION_V2.md), [ROADMAP.md](https://github.com/nautechsystems/nautilus_trader/blob/develop/ROADMAP.md)
- Docs: [latest IB integration (v2)](https://nautilustrader.io/docs/latest/integrations/interactive_brokers), [nightly IB integration](https://nautilustrader.io/docs/nightly/integrations/interactive_brokers), [v1 IB guide @v1.231.0](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/docs/integrations/ib.md), [v2 IB guide @develop](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/integrations/interactive_brokers.md), [reconciliation @v1.231.0](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/docs/concepts/reconciliation.md), [bar execution](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/docs/concepts/backtesting/bar-execution.md), [fill models](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/docs/concepts/backtesting/fill-models.md), [data and venues](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/docs/concepts/backtesting/data-and-venues.md), [v2 execution/risk](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/concepts/execution/index.md), [v2 python](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/concepts/python.md), [v2 catalog](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/concepts/data/catalog.md), [v2 installation](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/getting_started/installation.md), [v2 backtest APIs](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/concepts/backtesting/apis-and-runs.md), [configure live trading](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/how_to/configure_live_trading.md)
- v1 source @v1.231.0 (read from the wheel; byte-identical to the tag for the files checked): [adapters/interactive_brokers/](https://github.com/nautechsystems/nautilus_trader/tree/v1.231.0/nautilus_trader/adapters/interactive_brokers) (`execution.py`, `data.py`, `config.py`, `gateway.py`, `client/market_data.py`, `client/order.py`, `parsing/instruments.py`, `parsing/execution.py`, `parsing/data.py`, `historical/client.py`), [risk/](https://github.com/nautechsystems/nautilus_trader/tree/v1.231.0/nautilus_trader/risk), [live/config.py](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/live/config.py), [backtest/](https://github.com/nautechsystems/nautilus_trader/tree/v1.231.0/nautilus_trader/backtest) (`config.py`, `engine.pyx`, `modules.pyx`, `models/fee.pyx`, `models/fill.pyx`), [persistence/wranglers.pyx](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/persistence/wranglers.pyx), [common/actor.pyx](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/common/actor.pyx), [common/executor.py](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/common/executor.py), [common/factories.pyx](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/common/factories.pyx), [trading/config.py](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/nautilus_trader/trading/config.py)
- v2 source and examples @develop: [crates/adapters/interactive_brokers](https://github.com/nautechsystems/nautilus_trader/tree/develop/crates/adapters/interactive_brokers), [examples/live/interactive_brokers](https://github.com/nautechsystems/nautilus_trader/tree/develop/examples/live/interactive_brokers)
- GitHub issues: #3176, #4437, #4796, #5060, #5298, #5350, #5384, #5428, #5459, #5464, #5472, #5512, #5598, #5619, #5752, #1605 (links inline above)
- Project context: [ibkr-api-and-products.md](ibkr-api-and-products.md), [ibkr-paper-connection.md](ibkr-paper-connection.md), `JEV_QUANT_MASTER_PLAN.md`, `GLOSSARY.md`
