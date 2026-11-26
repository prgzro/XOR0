# Spike: spot crypto demo trading with NautilusTrader on Binance Spot Demo

Type: task
Status: ready-for-agent
Blocked by: 09

Venue choice and evidence: `docs/research/nautilus-spike.md`, section "Follow-up: spot crypto demo trading". Reuse from ticket 09: `spikes/nautilus/` (venv, `nautilus_trader==2.0.0rc9`, `spike/jev.py` `JevDispatcher`, the `bars.jsonl` logging and checker pattern).

**Scope:** this is a demo-venue spike only. Crypto is outside the master plan's universe (FX majors and crosses plus gold). Passing this ticket does **not** add crypto to the plan. That needs a plan change, an ADR and its own edge test.

## Setup (user)

- Create API keys in Binance Demo Trading (`demo.binance.com`) with trading on and **withdrawals off**.
- Put them in the repo `.env` (gitignored) as `BINANCE_DEMO_API_KEY` and `BINANCE_DEMO_API_SECRET`.
- If binance.com is unavailable in the user's country, use the Spot testnet instead (`testnet.binance.vision`, GitHub login, `BINANCE_TESTNET_API_KEY` and `BINANCE_TESTNET_API_SECRET`), and record that its prices are less realistic.

## Safety

- **Demo or testnet only.** Never construct a `BinanceEnvironment.LIVE` client, and never read or set live Binance key variables (`BINANCE_API_KEY` and `BINANCE_API_SECRET`). Never set `ENABLE_LIVE_TRADING`.
- Write a shared guard in `spike/` that every script calls before building a node. It exits unless:
  - the environment is `DEMO` or `TESTNET`;
  - only the matching demo or testnet key variables are present;
  - `ENABLE_LIVE_TRADING` is not true.
  Cover the guard with a test: it refuses LIVE, refuses when live key variables are set, and refuses when `ENABLE_LIVE_TRADING=true`.
- Credentials come from `.env` only. Never write a key, an account ID or an API response containing them to a file or log.
- Keep order sizes at the venue minimum notional or slightly above it.

## Steps and pass criteria

1. **Data-only live node** on `BTCUSDT` spot (`BinanceProductType.SPOT`, Demo environment).
   - Subscribe to H1 bars and log each bar's timestamp against wall-clock time over at least 3 H1 closes, the same as ticket 09 step 2.
   - Crypto trades 24/7, so there is no session gap and no `:15` bar.
   - **Pass:** each bar arrives once, stamped at bar close, within a bounded delay, and matches the venue's history for the same bars.
2. **Entry then OCO.**
   - The mocked Jev runs on the threaded `JevDispatcher` and approves the trade.
   - A small market BUY goes in. Once it fills, an OCO with the SL (`STOP_MARKET` → Binance `STOP_LOSS`) and the TP goes in for the filled quantity.
   - Nautilus's `bracket()` is denied on Binance ("planned"), so the entry and the OCO are sent separately.
   - If the OCO is rejected or never acknowledged within a bounded time, close the position at once (ticket 09, step-1 finding 4).
   - **Pass:** the position is open with both exit legs working at the venue, and the verdict was delivered on the event thread.
3. **Restart.**
   - `kill -9` the node while the position is open, then restart it with reconciliation on.
   - **Pass:** reconciliation succeeds, and the position plus both OCO legs are tracked. A reconciliation failure must stop startup before any order is sent.
4. **Flatten.** Cancel the exits and sell the position. **Pass:** the BTC balance is back to its pre-spike level within the lot step, and there are no open orders.
5. **Reject.** Send an order below the venue minimum notional. **Pass:** Nautilus marks it REJECTED, not left ACCEPTED (compare ticket 09's #5752 check on IB).

## Record

- Write results into `docs/research/nautilus-spike.md`, under the crypto follow-up section. Include versions, the environment used (Demo or testnet), the bar timing table, every PASS/FAIL line, and anything the adapter did that differs from IB.
- Note fees as charged by the demo venue, against the assumed ~10 bp.

## Outcome

- **All pass:** Nautilus can run a spot crypto demo. The next decision, whether crypto joins the plan, goes to the user as a plan change and ADR.
- **Step 2 or 3 fails** (exits not working at the venue, or not re-adopted after restart): record why. Crypto is not considered again until that is solved, because an unprotected spot position breaks the fail-closed rule.
