# NautilusTrader v2 spike (ticket `kronos-jev/09`)

Does NautilusTrader `2.0.0rc9` earn PAPER execution? Decision: `docs/adr/0001-…`. Results: `docs/research/nautilus-spike.md`.

**Paper only.** Every script talks to `127.0.0.1:4002` (paper port). `paper_bracket.py` refuses to run unless the Gateway's only account is a `DU…` paper account and `ENABLE_LIVE_TRADING` is not true. Credentials come from the repo `.env` through `--env-file`; none are in this directory.

## Setup

```sh
cd spikes/nautilus
uv sync                 # Python 3.13 venv, nautilus_trader==2.0.0rc9 (pinned), ib_async==2.0.1
uv run pytest -q        # fee model, Jev dispatcher, same-bar report, double-run determinism
```

Gateway (run from the repo root; pinned `ghcr.io/gnzsnz/ib-gateway:10.50.1h`):

```sh
# steps 1-2: read-only API
docker compose -p jevquant-ibgw --env-file .env -f spikes/nautilus/ibgw/docker-compose.yml up -d
# step 3 only: read-write API on the PAPER account (stop the read-only one first)
docker compose -p jevquant-ibgw --env-file .env -f spikes/nautilus/ibgw/docker-compose.paper-rw.yml up -d
```

## Steps

| Step | Command | Client IDs |
|---|---|---|
| 1. Pull EURUSD H1 BID+ASK into `data/catalog` | `uv run python scripts/pull_history.py ["1 Y"]` | 31 |
| 1. Double backtest + same-bar SL/TP report | `uv run python scripts/run_backtest.py [seed] [sl_pips] [tp_pips]` | — |
| 2. Data-only live node, bar timing log | `uv run python scripts/live_data.py <seconds>` | 32 |
| 2. Check the live bars against history | `uv run python scripts/check_live_bars.py` | 31 |
| 2. Exec client on a read-only Gateway? | `uv run python scripts/probe_exec_readonly.py` | 33, 34, 35 |
| 3. PAPER bracket / restart / flatten / reject | `uv run python scripts/paper_bracket.py <mode>` | 36, 37, 38 |

Step 3 sequence: `bracket` (keeps running) → `kill -9 <pid>` while the position is open → `restart` (reconciliation must pass and must report the position, SL and TP) → `flatten` → `reject`. Events go to `data/paper/events.jsonl`.

## Layout

- `spike/fees.py`: `IbkrFxFeeModel`, `max(0.2 bp × USD notional, USD 2)`.
- `spike/jev.py`: `JevDispatcher`, which stands in for v1's missing `run_in_executor`. It is inline in backtest; in live it runs on a worker thread, and the event-thread `drain()` delivers the verdict.
- `spike/strategy.py`: a trivial SMA-side strategy, a mocked Jev and an IB-valid bracket.
- `spike/ambiguity.py`: trades whose exit bar touched both SL and TP, with P&L both ways.
- `spike/data.py`: adds synthetic bar volume. IBKR FX bars have volume 0, which leaves the v2 venue with no market.
- `spike/backtest.py`: the `BacktestNode` run: NETTING/MARGIN/USD, leverage 20, seeded 1-tick slippage.
