# JEV QUANT: Master Plan (v2: Kronos + Jev + Interactive Brokers)

Version 2, 2026-11-26. It replaces v1 (SQ9 indicator on MT4/XM), which is archived at `docs/archive/JEV_QUANT_MASTER_PLAN_v1_SQ9_MT4.md`.

**Why v1 was dropped:** two pre-registered tests found no edge in SQ9 levels. With V2's real Origin rule on 6.8–17 years of XM history, out-of-sample came to −0.10 R per trade, and the 45° levels were respected no more than random lines (`docs/research/edge-revalidation.md`). The SQ9 research stays in `docs/research/` for reference.

---

## 1. Mission

Build a Python trading service that:

1. forecasts price with **Kronos**, an open-source foundation model for candlestick data (github.com/shiyu-coder/Kronos, MIT);
2. turns those forecasts into **Candidates**: proposed trades with a direction, entry, SL and TP;
3. asks **Jev**, the OpenCode Zen decision API, to approve or reject each Candidate;
4. lets an **independent Risk Gate** size, block or allow the trade;
5. executes on **Interactive Brokers**: signal-only, then a paper account, and guarded live only later.

The system must be measurable at every step. Any part that can't be shown to add value out-of-sample gets removed.

## 2. Non-negotiables

- **Default mode is PAPER.** Live trading stays off (`ENABLE_LIVE_TRADING=false`). Only the user turns it on, by explicit config. The service refuses to start live if any safety setting is missing, and never switches modes silently.
- **Secrets come from env only:** `OPENCODE_API_KEY` and IBKR credentials. Never hardcode, log, commit or echo them in errors. `.env` is gitignored, and `.env.example` documents the names.
- **No look-ahead.** Every forecast, Candidate and Jev snapshot uses only bars closed at decision time. Kronos's own pretraining data must not overlap the out-of-sample period (§8).
- **Fail closed.** If Kronos errors, Jev errors or times out, a response is malformed, data is stale, or IBKR is disconnected, no trade is placed.
- **The Risk Gate is authoritative.** Jev can only reject, or approve what the mechanical rule proposed. It can never reverse direction or move SL/TP.
- **Go/no-go gates:** if the Kronos edge test (§8) fails, we don't build execution.

## 3. Universe and timeframe

- **Instruments:** FX majors and crosses (EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, EURGBP, EURJPY, GBPJPY, EURCHF) on IBKR IDEALPRO, plus gold. Whether gold is spot XAUUSD or gold futures (e.g. MGC) depends on IBKR availability for the user's account (open research).
- The symbol list is configurable.
- **Signal timeframe:** H1 closed bars. Kronos reads the last **400 bars** and forecasts the next **24** (one trading day). Both are configurable, but the lookback stays ≤ 512, the model's context limit.

## 4. Architecture

One Python 3.13 service on **NautilusTrader v2**, with modules behind narrow interfaces. Nautilus provides the event loop, the IBKR adapter, the Parquet bar catalog, the backtest engine and order and position tracking. Our modules run inside it, so the same strategy code runs in backtest and live. PAPER execution through Nautilus depends on a spike passing, with a thin `ib_async` layer as the fallback (`docs/adr/0001-nautilustrader-v2-engine-execution-spike-gated.md`).

| Module | Responsibility |
| --- | --- |
| `data` | IBKR historical and live H1 BID/ASK bars through the Nautilus IB adapter, the Parquet catalog, a stale-data check. Backtests read the same catalog. |
| `forecast` | Kronos wrapper: load the model and tokenizer once, then batch-predict **N sample paths** per symbol (default N = 30) and return the forecast distribution. |
| `signal` | Turns a forecast distribution into a Candidate or nothing (§5). Pure and deterministic, given the forecast. |
| `jev` | Builds the decision snapshot, calls Jev over HTTP, validates the response (§6). |
| `risk` | The Risk Gate (§7). Our own code, independent of Nautilus. It runs inside the strategy before any order is submitted. Nautilus's RiskEngine is only a backstop (order size and rate), and its `HALTED` state is the kill switch. |
| `execution` | `SIGNAL_ONLY`, `PAPER` (IBKR paper account), `LIVE` (guarded). It uses the Nautilus IB execution client against our pinned IB Gateway, or `ib_async` if the spike fails. |
| `journal` | Append-only records of every forecast, Candidate, Jev decision, risk verdict, order and outcome. Restart-safe. |
| `backtest` | Walk-forward replay of `data → forecast → signal → (jev) → risk → simulated fills` on the Nautilus backtest engine. It uses BID/ASK bars, a custom IBKR fee model, seeded slippage, and reports trades where SL and TP were hit in the same bar both ways. |

The loop runs on each H1 close for each symbol: fetch bars, forecast, build a Candidate, ask Jev, run the Risk Gate, execute, then journal.

There is no MT4, MQL4 or Node bridge.

Hardware: a GTX 1650 (4 GB), 16 cores and 23 GB of RAM. Kronos-small (25M) and base (102M) inference should fit, and speed must be measured. Fine-tuning large models is out of reach locally.

## 5. Signal: from forecast to Candidate

From the N sample paths over the horizon H:

- `p_up` = share of paths whose close at H is above the current close; `p_down` = 1 − `p_up`.
- `move` = the median forecast return at H, expressed in ATR14 units.
- A **long Candidate** fires when `p_up ≥ P_MIN` and `move ≥ MOVE_MIN` after costs, where the cost is spread plus commission plus slippage, in ATR. Shorts mirror this.
- **SL and TP** come from the forecast distribution and ATR. For example, SL beyond the 10th-percentile path low, capped at k·ATR; TP at the median path's target. The exact rule is fixed in the edge test's pre-registration (§8).
- At most one open position per symbol. A new Candidate on a symbol with an open position is ignored.

`P_MIN`, `MOVE_MIN`, N, H and the SL/TP rule are the only free parameters. They are chosen in-sample only.

## 6. Jev decision engine

Reference: `docs/reference/jev-opencode-zen-guide.md`.

- **Endpoint:** `POST https://opencode.ai/inference/systemone/v1/systemone` with `Authorization: Bearer $OPENCODE_API_KEY`. The model defaults to `jev-1.13-free`, with `jev-1.13` and `jev-1.14` as configurable alternatives.
- **Snapshot** (bars closed at decision time only):
  - symbol, timeframe, time;
  - recent bar summary, ATR, spread;
  - the Kronos distribution: `p_up`, median and quantile paths, `move`;
  - the Candidate: direction, entry, SL, TP, R:R;
  - rolling past performance of the system (no future outcomes).
- **Questions:**
  - `choice` → `APPROVE_<DIR>` / `NO_TRADE`;
  - `noul` → "Is there a critical condition that should block this trade?";
  - `score` → a setup quality from 1 to 5. This is a qualitative score, not a probability.
- **Validation:**
  - expected model, structure, keys, value ranges and request ID;
  - no duplicate processing;
  - a reply in the opposite direction counts as a reject;
  - a timeout or malformed reply means reject (fail closed).
- **Thresholds are configurable.** Jev's probabilities are never treated as win probabilities.
- **Jev must earn its place.** In replay, approved trades must beat all Candidates out-of-sample. Otherwise Jev is dropped or relegated to the critical-risk veto only.

## 7. Risk Gate

Independent and authoritative. Every check is configurable, and every rejection is journalled with its reason.

- **Sizing:**
  - risk per trade as a % of equity, sized from the SL distance using IBKR contract specs;
  - IDEALPRO minimums, size increments and the account base currency.
- **Limits:**
  - max spread;
  - max open positions, overall and per currency exposure (correlated pairs count together);
  - max daily loss and max drawdown;
  - min R:R;
  - min available funds and margin.
- **Order safety:**
  - duplicate-order prevention;
  - a slippage limit;
  - no trading during configured blackout windows (e.g. weekend gaps, rollover).
- The Gate may reject a trade or reduce its size. It never moves SL/TP.

## 8. Validation gate: is there a Kronos edge? (Phase 1, before building execution)

A pre-registered, walk-forward test of Kronos used as-is (zero-shot, no fine-tuning):

- **Data:** IBKR's own H1 BID/ASK history (from 2005 for 10 pairs, 2007 for NZDUSD, 2010 for XAUUSD; `docs/research/ibkr-paper-connection.md`). The XM history we already hold (2020-02 → 2026-11, bid only) is a cross-check only.
- **Leakage:** find Kronos's pretraining data cutoff. Only bars **after** that cutoff count as true out-of-sample. Earlier bars are in-sample at best.
- **Pre-registration:** the forecast settings (model size, N, H, T, top_p), Candidate rule, SL/TP rule, costs (spread, commission, slippage) and split are all written down before any out-of-sample result is seen.
- **Metrics:**
  - directional hit rate vs 50%, and calibration of `p_up`;
  - strategy trades, win rate, mean R with a bootstrap CI, PF and max DD;
  - per symbol, with a multiple-comparison correction;
  - compared against naive baselines: random entries with the same SL/TP, and a momentum baseline.
- **Go** only if the pooled out-of-sample mean R after base costs is > 0, the bootstrap 95% CI lower bound is > 0, and there are at least 100 trades. **Inconclusive** if fewer than 100 trades: keep collecting forward data in SIGNAL_ONLY mode. **No-go** otherwise, including when Kronos beats the baselines but earns ≤ 0 R: stop, or try fine-tuning as a separate, pre-registered experiment. Full pre-registration: `docs/research/kronos-edge-test.md`.

## 9. Execution modes

- **SIGNAL_ONLY:** forecast, Candidate, Jev and risk run as normal, and the result is journalled. No orders.
- **PAPER:** orders go to the **IBKR paper account** through IB Gateway. Bracket orders (entry plus SL/TP) are tracked and reconciled against IBKR positions on restart.
- **LIVE:** the same as PAPER on a live account. It needs `EXECUTION_MODE=LIVE`, `ENABLE_LIVE_TRADING=true` and every risk limit set explicitly, or startup refuses. Never enabled by the agent.

## 10. Journal and analytics

JSONL (or SQLite) with one record per event, keyed by a Candidate ID, and restart-safe.

Analytics report:
- Jev approved vs rejected outcomes;
- long vs short;
- per symbol;
- by `p_up` bucket, volatility regime and Jev score;
- forecast calibration over time.

Past outcomes may be summarised into future Jev snapshots. That isn't training: Jev's weights don't change.

## 11. Testing

- **Unit tests:** the signal rule, sizing, Risk Gate checks, Jev response validation (including malformed, timeout and opposite-direction replies) and journal recovery.
- **Kronos wrapper:** a deterministic test with a fixed seed and a tiny model or a mock.
- **Integration:** the full loop against recorded bars with a mocked Jev and a mocked IBKR. Then a SIGNAL_ONLY dry run on the IBKR paper account.
- **Backtest reproducibility:** the same inputs and seed give the same results.

## 12. Phases

0. **Discovery:** IBKR API and products, Kronos install and speed on this machine, Kronos training cutoff, and Jev response shapes.
1. **Kronos edge test (§8).** This is the go/no-go point.
2. **Signal + Risk Gate + journal,** with tests.
3. **Jev decision engine,** plus a replay showing whether Jev adds value.
4. **IBKR data + SIGNAL_ONLY** running live.
5. **PAPER** on the IBKR paper account, with reconciliation and restart safety.
6. **Backtest and Jev replay tooling,** with full analytics.
7. *(Operations, beyond this spec)* Continuous paper trading, then a user decision on LIVE.

## 13. Acceptance criteria (Phases 0–6)

1. The Kronos edge test is pre-registered and run, and its out-of-sample window lies after Kronos's training cutoff.
2. No look-ahead in forecasts, Candidates or Jev snapshots, proven by a test.
3. Signal, Risk Gate and Jev validation are covered by unit tests, including the fail-closed paths.
4. Jev's value is measured, approved vs all Candidates, out-of-sample.
5. PAPER orders appear in the IBKR paper account with SL/TP attached, and they reconcile after a restart.
6. LIVE refuses to start without explicit config. Default is PAPER.
7. No secrets in the repo, logs or errors.
8. Every decision and rejection is journalled with its reason.
