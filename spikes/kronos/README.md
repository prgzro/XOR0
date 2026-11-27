# Kronos spike: install, speed and the Edge test

Tickets `.scratch/kronos-jev/issues/02-kronos-on-this-machine.md` (resolved) and
`06-kronos-edge-test.md`. Pre-registration: `docs/research/kronos-edge-test.md`.
Speed write-up: `docs/research/kronos-install-speed.md`.

## Setup

```bash
cd spikes/kronos
git clone https://github.com/shiyu-coder/Kronos.git vendor-Kronos
git -C vendor-Kronos checkout 67b630e67f6a18c9e9be918d9b4337c960db1e9a
UV_HTTP_TIMEOUT=600 uv sync          # torch 2.8.0+cu128, ~5 GB
.venv/bin/python -m pytest -q        # simulator, calendar and statistics tests
```

Data comes from the read-only IBKR paper Gateway on 127.0.0.1:4002 (see `spikes/nautilus/ibgw/`). It never places orders.

## Pipeline

| step | command | output |
|---|---|---|
| data | `uv run python scripts/pull_ibkr.py --from 2009-09-01` | `data/ibkr/<SYM>_<MIDPOINT,BID,ASK>.parquet` |
| speed | `.venv/bin/python scripts/bench.py --model small --items 12` | one JSON line |
| fast = reference? | `.venv/bin/python scripts/check_fast.py small 2` | identical-path share |
| lookahead audit | `.venv/bin/python scripts/audit_lookahead.py --symbol EURUSD ...` | `results/audit_lookahead.md` |
| Forecasts, pre-OOS | `scripts/run_pre_oos.sh` | `results/forecasts/small_n30/<SYM>_<YYYY>.parquet` |
| selection | `.venv/bin/python scripts/evaluate.py --forecasts results/forecasts/small_n30 --stage select` | `results/select.md` |
| contamination | `... --stage contamination --set P,M` | `results/contamination.md` |
| Forecasts, OOS | `run_forecasts.py --from 2025-07-01 --to <end> --unseal <pre-reg commit>` | sealed until the commit is recorded |
| verdict | `... --stage oos --set P,M` | `results/oos.md` |

## Code

- `spike/kronos_paths.py`: model loading (pinned revisions), the reference sampler and the fast KV-cached sampler (bit-identical).
- `spike/calendar.py`: future bar times from a fixed rule, so no calendar leaks in.
- `spike/strategy.py`: ATR, Forecast statistics, the Candidate rule and the trade simulator (fills, gaps, same-bar SL/TP, Time exit, commission, financing).
- `spike/data.py`: loading and the pre-registered cleaning rules.
- `spike/stats.py`: cluster bootstrap, Holm, deflated Sharpe, PBO by CSCV, Monte Carlo drawdowns, monthly returns.
