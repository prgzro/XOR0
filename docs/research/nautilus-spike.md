# NautilusTrader v2 spike: results

For `.scratch/kronos-jev/issues/09-nautilus-spike.md`. Decision under test: `docs/adr/0001-nautilustrader-v2-engine-execution-spike-gated.md`. Earlier desk research: [nautilustrader-ibkr.md](nautilustrader-ibkr.md). Code and how to rerun: `spikes/nautilus/README.md`. Run 2026-11-26 on the IBKR **paper** account; no live account was touched.

## TL;DR

| Step | Result |
|---|---|
| 1. Deterministic backtest | **PASS.** Two runs gave identical fills and P&L, both in one process and across separate processes. |
| 2. Data-only live node | **PASS for FX, FAIL for gold.** EUR/USD (MID, BID, ASK) and USD/JPY: each bar arrived once, at close + 0.35–1.08 s, and matched IBKR history exactly. XAUUSD bars were on time but **did not match history** (3 of 3 bars differ). |
| 3. PAPER bracket and restart | **NOT RUN.** It needs the read-write paper Gateway. The scripts are ready, and each mode prints PASS/FAIL. |

**Verdict so far:** Nautilus v2 is fine for backtests and SIGNAL_ONLY FX data. Gold's live bars differ from history, so the service should re-fetch each closed bar from history rather than trust the stream. PAPER execution is still not earned: step 3 decides it, so the ADR is unchanged.

## Versions

| Item | Value |
|---|---|
| Engine | `nautilus_trader==2.0.0rc9`, pinned. 2.0.0 final is not on PyPI as of 2026-11-26. |
| Python | 3.13.0 (uv), in a separate venv at `spikes/nautilus/.venv` |
| Gateway | `ghcr.io/gnzsnz/ib-gateway:10.50.1h`, paper, read-only API, `127.0.0.1:4002` |
| Also | `ib_async==2.0.1`, used only for the paper-account guard |

**The v2 Rust IB client connects to Gateway 10.50.1h**, so its "server protocol ≥213" requirement is met.

## Step 1: deterministic backtest

**Setup:**
- **Data:** EURUSD H1 BID and ASK, 6,198 bars per side (2025-11-26 23:15 to 2026-11-26 11:00 UTC). Pulled with v2's own `HistoricalInteractiveBrokersClient` into a `ParquetDataCatalog`.
- **Venue:** `BacktestNode`, `IDEALPRO` venue, NETTING / MARGIN / USD.
- **Leverage and margin:** `default_leverage=20` (a placeholder; real IBKR FX margin is unverified) with `LeveragedMarginModel`, both set explicitly.
- **Fees:** `IbkrFxFeeModel`, `max(0.2 bp × USD notional, USD 2)`, with crosses converted to USD.
- **Slippage:** `ProbabilisticFillModel(prob_slippage=0.5, random_seed=…)`, so half of market fills slip 1 tick (0.5 pip).
- **Strategy:** trivial (mid vs SMA24 picks the side) with a 100k entry and SL 30 / TP 45 pips. The mocked Jev rejects Candidates whose bar hour is divisible by 3.

| Run | Verdicts (approved / rejected) | Fills | Trades | Commission | Final balance | Identical? |
|---|---|---|---|---|---|---|
| seed 42, SL 30 / TP 45 | 311 / 95 | 621 | 310 | USD 1,433.93 | USD 986,151.07 | yes: same fills (sha `b18598c6…`) in-process and in 3 separate processes |
| seed 7, SL 30 / TP 45 | — | — | — | — | USD 987,184.94 | yes |
| seed 42, SL 8 / TP 12 | 2,053 / 786 | 4,105 | 2,052 | USD 9,483.12 | USD 937,261.88 | yes |

Tests (`uv run pytest`, 13 passing) also prove that a different seed changes the fills, so the determinism check is not trivially true.

**Same-bar SL/TP, reported both ways:**
- With 30/45-pip legs, 0 of 310 trades had both levels touched in the exit bar.
- With 8/12-pip legs, **71 of 2,052** did. Their gross P&L is **USD −6,180 if SL came first** and **+8,020 if TP came first**, a USD 14,200 swing.
- Nautilus resolves the ambiguity with a fixed O→H→L→C path (`bar_adaptive_high_low_ordering=False`). That path favours longs (TP first) and penalises shorts (SL first).
- The pre-registered edge test must count these trades both ways.

**Fee check:** the first fill was 100k EUR at 1.15970, which is 115,970 USD notional; the commission charged was USD 2.32, as expected.

### v2 behaviour the build must handle

1. **There is no `run_in_executor` in v2.** The v1 offloading API is gone. Its replacement is `spike/jev.py` `JevDispatcher`:
   - `inline` mode is used in backtest. It is synchronous and deterministic.
   - `threaded` mode is used live. Jev runs on a worker thread. A 250 ms clock timer drains the verdicts, so orders are only ever submitted on the event thread.
   - A Jev exception or timeout becomes a reject, never a missing callback.
2. **IBKR FX bars have volume 0, which leaves the backtest venue with no market.**
   - v2 builds the L1 book from bar volume, so every order was rejected with "No market for EUR/USD.IDEALPRO".
   - Fix (`spike/data.py`): give each bar a synthetic volume of 1e9 before writing the catalog.
   - With BID+ASK bars and volume, a market BUY fills at the ask, so the spread is modelled.
3. **`make_price` rounds to the price *precision* (5 dp), not to the *increment* (0.00005).** Off-grid SL/TP prices get rejected. Snap them with `snap_to_tick`.
4. **When the SL/TP legs are rejected, the entry still fills, leaving a naked position.** In the run with off-grid prices, the market entry filled while both exits were rejected. The Risk Gate and journal must check that a bracket's exits are working after the entry fills, and flatten if they are not.
5. **An exception in `on_bar` is logged and swallowed, and the run keeps going.** An exception in `on_start` aborts startup. The pipeline must catch errors itself and fail closed, for example by halting trading on any error in the Candidate-to-order path.
6. **IBKR's BID/ASK bars sit on the 0.00005 grid, so EURUSD's spread is mostly 0 or 0.5 pip.**
   - Over the 6,198 H1 closes: **57.1% have zero spread** and 35.8% have 0.5 pip. Only 7% have 1 pip or more.
   - The mean is 0.40 pip, against a real quoted spread of about 0.3 pip.
   - The live 12:00 bar showed identical BID, ASK and MID open/high/low.
   - Total spread cost is about right on average but lumpy, and more than half of the fills pay no spread.
   - For the edge test, add a floor (for example, half the typical spread per side) through a custom `FillModel`, or charge it as cost.
7. **Within one timestamp, the ASK bar arrived before the BID bar.** Pair BID and ASK by `ts_init`, in either order.
8. **API shape changes from v1:**
   - `OrderFactory.bracket()` returns a plain list.
   - `Strategy`/`DataActor` subclasses with constructor arguments need a `__new__` override (the PyO3 base accepts only an optional config).
   - `Portfolio.is_net_flat`, not `is_flat`.
   - `subscribe_bars` across two venues (IDEALPRO and IBCMDTY) needs an explicit `client_id`.
   - `ParquetDataCatalog.write_bars` takes one bar type per call.
   - `bracket()` defaults to `tp_post_only=True` and reduce-only exits, all of which the IB adapter refuses. Pass `False` for each.

## Step 2: data-only live node

Run 2026-11-26 from 11:19 to 14:05 UTC. Data-only `LiveNode`, client 32, `use_regular_trading_hours=False`. It logged 5 bar streams over 3 H1 closes (12:00, 13:00, 14:00 UTC). The checker is `scripts/check_live_bars.py`: it re-pulled IBKR history afterwards with client 31, twice, with identical results.

| Check | Result |
|---|---|
| Each bar once | **PASS.** 15 bars, 0 duplicates |
| Stamped at close, bounded delay | **PASS.** `ts_init` on the hour; receipt 0.35–2.00 s after close (limit 30 s) |
| 3 closes per stream, no missing hour | **PASS** |
| Matches IBKR history | **PASS for EUR/USD MID/BID/ASK and USD/JPY** (12 of 12 bars exact). **FAIL for XAUUSD** (0 of 3) |

**Delays:**
- Typical: 0.35–0.37 s after the close.
- EUR/USD ASK at 14:00: 1.08 s. Its BID and MID came at 0.37 s, so a BID/ASK pair can arrive up to a second apart.
- XAUUSD at 13:00: 2.00 s.

**Gold mismatch:** `XAUUSD.IBCMDTY` 1-HOUR-MID, live vs history (OHLC):

| Bar | Live | History |
|---|---|---|
| 12:00 | 3555.88 / 3570.57 / 3555.86 / **3567.12** | … / **3567.11** |
| 13:00 | 3567.12 / **3574.27** / 3562.74 / **3567.60** | 3567.11 / **3574.93** / 3562.73 / **3568.86** |
| 14:00 | **3569.94** / 3575.49 / 3562.88 / 3571.80 | **3568.86** / 3575.49 / 3562.87 / 3571.80 |

- **What it looks like:** the live 13:00 bar missed the last part of the hour. Its high is 0.66 lower, its close is 1.26 lower (about 3.5 bp), and it arrived 2 s late. The live 14:00 bar then opened at a later price. The 0.01 differences elsewhere look like midpoint rounding.
- **Cause:** not diagnosed. IB's CMDTY midpoint stream is probably sparser than FX, but that hasn't been checked.
- **Rule for the build:** don't treat a streamed bar as final. After each close, re-request the just-closed bar from IBKR history and give Kronos that version. Log any difference from the streamed bar. This matters most for gold, and costs FX nothing.
- **Gold:** it is unresolved for Kronos input until a longer run shows whether history-refetched bars are stable.

**Also found:**
- **The exec client does not start on a read-only Gateway.** IB answers `[321] … The API interface is currently in Read-Only mode`, and the node logs "Execution client connection failed, aborting startup". That is fail-closed, so SIGNAL_ONLY must be a data-only node, as planned.
- **Warmup `request_bars(limit=400)` with no `start` returned only 14 bars (about one day).** With `start = now − 35 days` it returns 400.
- **The warmup includes the in-progress bar.** Requested at 11:17 UTC, the last bar was stamped 12:00 UTC (its future close) and is incomplete. Warmup must drop bars with `ts_init > now`, or Kronos sees an unfinished bar.
- **The `:15` session-open bar is stamped start + 1 h.** For example, the 22:15 UTC bar (which closes at 23:00) gets ts 23:15. That is 15 minutes after its real close, but still before the next bar's close, so ordering holds. History requests show the same stamp.

## Step 3: PAPER bracket and restart (not run)

This step needs `spikes/nautilus/ibgw/docker-compose.paper-rw.yml`: the same pinned image, paper, with `READ_ONLY_API: "no"`. Then run `scripts/paper_bracket.py` in this order:

1. **`bracket`**
   - The mocked Jev runs on the threaded dispatcher, so the step-1 code path runs in a real node.
   - It places a 25k EUR/USD market entry plus SL (STOP_MARKET) and TP (LIMIT).
   - SL and TP share one `IBOrderTags` OCA group (`ocaType=1`), and both use `tp_reduce_only=False, sl_reduce_only=False`.
   - After the fills it prints a reference snapshot and the `kill -9` command.
2. **`restart`** runs with reconciliation on and `external_order_instrument_ids=[EUR/USD]`. PASS requires net position 25,000 plus an open SELL STOP_MARKET and an open SELL LIMIT of 25,000. A reconciliation failure aborts `node.run()` before any order.
3. **`flatten`** cancels the exits and closes the position. PASS requires the account to be flat with no open orders.
4. **`reject`** places a 1,000-unit market order (#5752's repro).
   - PASS if the order ends REJECTED; FAIL if it is left ACCEPTED (#5752).
   - If IB fills the order instead, the result is INCONCLUSIVE; run `flatten` afterwards.

**Not covered:** a deliberately *failing* reconciliation, because there's no safe way to cause one on demand. The evidence for "never trades on unreconciled state" is limited to `node.run()` aborting on client/trader start failure, as seen in step 2.

## Follow-up: spot crypto demo trading (not part of ticket 09)

The user wants to demo-trade spot crypto before anything real. Crypto is **outside the master plan's universe** (FX majors and crosses plus gold). This section records the venue choice for a demo spike only. Trading crypto for real needs a plan change, an ADR and its own edge test, because Kronos and Jev have no crypto trading result yet (see ticket 01).

### Venue choice: Binance Spot Demo through Nautilus's Binance adapter

| | IBKR crypto (Paxos) | Binance Spot | Kraken Spot |
|---|---|---|---|
| Nautilus adapter | The same IB adapter (secType `CRYPTO`, exchange `PAXOS`) | Rust adapter, "stable" | Rust adapter, "stable" |
| Demo venue | Paper account, crypto support unverified | **Demo** environment (Nautilus recommends it), plus the older Spot testnet | **None** for spot |
| Stop at the exchange | **No.** IBKR lists only limit and market orders for Paxos crypto, and market orders must be IOC | Yes: `STOP_MARKET` (sent as `STOP_LOSS`) and `STOP_LIMIT` | Yes |
| Linked SL and TP | No | Yes: native **OCO** | No (OCO and bracket unsupported) |
| Fee | 18 bp of trade value, minimum USD 1.75 | About 10 bp (from memory, unverified) | — |
| Short | No | No (the adapter doesn't implement margin) | Only with a margin account |

**Why Binance:**
- **The SL and TP sit at the exchange as an OCO**, so they survive a crash or a `kill -9`.
- With IBKR Paxos, the stop would have to be emulated inside our own process. That leaves the position unprotected whenever the process is down, which breaks the fail-closed rule.
- Kraken has no spot demo and no OCO.

### What is in rc9 (checked in `spikes/nautilus/.venv`)

- **Classes:** `BinanceDataClientConfig`, `BinanceExecutionClientConfig` and their factories. `BinanceEnvironment` has `LIVE`, `DEMO` and `TESTNET`; `BinanceProductType.SPOT`.
- **Demo endpoints are built in:** `demo-api.binance.com`, `demo-stream.binance.com` and `demo-ws-api.binance.com`.
- **Key env vars** (strings in the compiled library):
  - `BINANCE_DEMO_API_KEY` and `BINANCE_DEMO_API_SECRET`
  - `BINANCE_TESTNET_API_KEY` and `BINANCE_TESTNET_API_SECRET` (the testnet fallback)
- **`OrderFactory.bracket()` is denied** at submission on Binance ("planned"). Send the entry first, then an OCO with the SL and TP after the fill.

### Setup (user)

1. **Create demo keys:** log in to Binance Demo Trading (`demo.binance.com`) and create API keys with trading enabled and **withdrawals off**. Demo keys work only on the demo venue.
2. **Store them in the repo `.env`** (gitignored) as `BINANCE_DEMO_API_KEY` and `BINANCE_DEMO_API_SECRET`. **Never put live Binance keys in `.env`.**
3. **If binance.com is unavailable** (for example, its API blocks US IPs): use the Spot testnet (`testnet.binance.vision`, GitHub login) with `BinanceEnvironment.TESTNET`. Its prices are less realistic than Demo's.

### Planned demo spike (a new ticket)

Same shape as steps 2 and 3 above, on `BTCUSDT` spot:

1. **Guard.** Refuse to start unless the environment is `DEMO` or `TESTNET`, only the demo or testnet key variables are set, and `ENABLE_LIVE_TRADING` is not true. Never construct a `LIVE` client.
2. **Data.** A data-only node takes BTCUSDT H1 bars, and a checker confirms each bar arrives once, at the close, with bounded delay, and matches history. Crypto trades 24/7, so there's no session gap and no `:15` bar.
3. **Order.**
   - The mocked Jev runs on the threaded dispatcher and approves the trade.
   - A small market BUY goes in. Once it fills, an OCO goes in with the SL (`STOP_LOSS`) and the TP.
   - If the OCO is rejected, the position is closed at once (step-1 finding 4).
4. **Restart.** `kill -9`, then restart with reconciliation. PASS requires the position plus both OCO legs to be tracked.
5. **Flatten.** Cancel the exits and sell the position. PASS requires the account to be flat, with no open orders.

**Limits:**
- Spot is long-only, so SELL signals are skipped.
- Binance is a second broker: it needs its own keys, and the Risk Gate must see both accounts.
- Availability depends on the user's country.

Sources: [Nautilus Binance adapter](https://nautilustrader.io/docs/latest/integrations/binance/), [Nautilus Kraken adapter](https://nautilustrader.io/docs/latest/integrations/kraken/), [Nautilus integrations](https://nautilustrader.io/docs/latest/integrations), [IBKR crypto order types](https://www.interactivebrokers.com/support/faq/content/173866144), [IBKR crypto commissions](https://www.interactivebrokers.com/en/pricing/commissions-cryptocurrencies.php?region=americas).
