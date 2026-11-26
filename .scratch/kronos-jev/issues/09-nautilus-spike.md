# Spike: does NautilusTrader v2 earn PAPER execution?

Type: task
Status: ready-for-agent
Blocked by: 05

Decision: `docs/adr/0001-nautilustrader-v2-engine-execution-spike-gated.md`. Evidence: `docs/research/nautilustrader-ibkr.md`.

## Setup

- A separate Python 3.13 venv with `nautilus_trader==2.0.0rc9`, or 2.0.0 final if it has shipped. Pin the exact version.
- Connect to our existing gnzsnz Gateway, not `DockerizedIBGateway`. Give Nautilus its own client ID.
- **Paper only.** Never point anything at a live account or set `ENABLE_LIVE_TRADING`. Credentials come from `.env` only.

## Steps and pass criteria

1. **Deterministic backtest.**
   - EURUSD H1 from IBKR BID and ASK bars, written to a Parquet catalog.
   - A trivial strategy that calls a **mocked Jev** through the same code path the real HTTP call will use (`run_in_executor`; submit orders back on the event thread).
   - A custom IBKR FX fee model, `max(0.2 bp × notional, USD 2)`, and 1-tick slippage with a fixed seed.
   - Set leverage and margin explicitly.
   - Report trades where SL and TP were hit in the same bar both ways (SL first and TP first).
   - **Pass:** two runs give identical fills and P&L.
2. **Data-only live node** on the read-only Gateway (`127.0.0.1:4002`).
   - Set `use_regular_trading_hours=False`.
   - Log each H1 bar's timestamp against wall-clock time over at least 3 H1 closes.
   - Note whether the execution client starts on a read-only Gateway at all.
   - **Pass:** each bar arrives once, stamped at bar close, within a bounded delay, and matches IBKR history.
3. **PAPER bracket and restart.** This needs a **read-write paper** Gateway config, which the user sets up.
   - **Bracket:** place an entry with SL and TP, set one-cancels-other explicitly with `IBOrderTags`, and use the v2 flags `tp_reduce_only=False, sl_reduce_only=False`.
   - **Restart:** kill the node mid-position, then restart it. Startup reconciliation must succeed, and the open position, SL and TP must all be tracked. Any reconciliation failure must stop startup; it must never trade on unreconciled state.
   - **Reject:** trigger an order IB rejects, for example one below the IDEALPRO minimum. Nautilus must mark it rejected. Watch for #5752, where the order is wrongly left "accepted".

## Outcome

- **All three pass:** Nautilus gets PAPER execution. Record the result in the ADR.
- **Step 3 fails:** Nautilus stays for backtests and SIGNAL_ONLY data. Execution moves to a thin `ib_async` layer. Update the ADR's Status and the master plan.

## Comments

**2026-11-26, steps 1–2 run; step 3 waiting on the read-write paper Gateway.** Results: `docs/research/nautilus-spike.md`. Code: `spikes/nautilus/`.
- **Step 1: PASS.** Identical fills and P&L across runs and processes. Same-bar SL/TP is reported both ways.
- **Step 2: PASS for FX** (EUR/USD MID/BID/ASK, USD/JPY): each bar arrived once, at close + 0.35–1.08 s, and matched history. **XAUUSD live bars did not match history** (0 of 3). The build should re-fetch each closed bar from history before Kronos. The exec client fails closed on a read-only Gateway (IB error 321).
- **Step 3:** the scripts are ready (`scripts/paper_bracket.py bracket|restart|flatten|reject`). The ADR is unchanged until step 3 runs.
