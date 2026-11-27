# Kronos zero-shot Edge test on the FX majors, H1 (research)

Ticket: `.scratch/kronos-jev/issues/06-kronos-edge-test.md` ("Does Kronos have a zero-shot edge on FX + gold H1?"). Plan: `JEV_QUANT_MASTER_PLAN.md` §5 and §8. Vocabulary: `GLOSSARY.md` (Forecast, Horizon, Candidate, Time exit, Edge test).

Status: **pre-registration agreed with the user in a grilling session (2026-11-26), with the model and N fixed by the speed measurements** (`docs/research/kronos-install-speed.md`). Nothing out-of-sample has been run, and no in-sample result has been looked at. The pre-registration is binding once it's committed. That commit's hash is recorded under "Pre-registration commit" below, and every later change goes under "Disclosed deviations".

## User goal and how this test serves it

The user's goal is **2–6% a month** on the account. At a fixed risk per trade:

> monthly return ≈ risk per trade × trades per month × mean R (net of costs)

At 1% risk and roughly 25 trades a month across the 7 majors, that takes a mean of about **+0.08 R to +0.24 R per trade after costs**. This test measures whether that edge exists out-of-sample. The goal is **reported as a target check** (below). It is **not an objective to tune for**: tuning toward a return target on data you've already seen produces exactly the overfit result that this test is designed to rule out.

## Hypothesis

- **Mechanism.** FX and gold H1 prices have small, recurring short-horizon structure: volatility clustering, continuation after liquidity-driven moves, and reversal after session-driven overshoots (Asia → London → New York handovers, the 16:00 London fix, rollover). Much of that flow comes from participants who trade without regard to price over hours: corporate hedgers, fixing orders, central-bank and reserve flows, and stop cascades. Kronos was pretrained on K-line sequences from many markets, so it may pick up this structure as the shape of its path distribution (direction, skew and dispersion over 24 bars) better than a single linear rule does.
- **Who is on the other side.** Price-insensitive hedgers and fixing flows, and stop-driven traders. These flows are structural, so they're expected to persist.
- **Timescale consistency.** Session and fixing effects play out over hours to about a day, so H = 24 H1 bars and a Time exit at H match the mechanism. A holding period far from that would be a red flag.
- **Prior.** Modest. Ticket 01 found FX forecast correlation of only ≈0.02–0.05 in the Kronos paper, and no FX trading result. A no-go is a likely and legitimate outcome.

## Pre-registration

### Data

- **Universe (user, 2026-11-26): the 7 FX majors only:** EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD. The crosses are out of this test. **Gold (XAUUSD) gets its own test after this one passes**, with these rules and the set selected here, frozen and run on gold's own data. That test must be pre-registered before any gold result is seen.
- **Primary:** IBKR H1 history. Kronos gets MIDPOINT bars. Fills use BID and ASK bars (`docs/research/ibkr-paper-connection.md`).
- **Cross-check only:** the XM H1 history (bid only, offset 1.1 pip, server time UTC+2/+3 converted to UTC).
- **Cleaning (data-cleaning skill):** rules are fixed before results are seen and every correction is logged.
  - Drop bars with high < low, or with a close outside [low, high].
  - Flag any bar whose mid return is more than 10 × ATR14. Spot-check it against XM, and keep it unless both sources disagree.
  - Never forward-fill missing bars. A gap is a gap.
  - Spot-check 20 random bars per symbol against XM.
- **Snapshot:** the downloaded bars are stored as Parquet, and their SHA-256 is recorded here before any run.

#### Data snapshot (majors), pulled 2026-11-26

- Source: IBKR paper Gateway, H1, `useRTH=False`, 2009-09-01 → pull time. 106,598–107,212 bars per file.
- **Out-of-sample end:** the series end at different hours (15:00–18:00 UTC on 2026-11-26) and the last bar of each file was still forming when it was pulled. The out-of-sample window therefore ends at **2026-11-26 15:00 UTC (exclusive)**, the earliest file end. Every Forecast bar is complete, and the same cut applies to all 7 symbols.
- AUDUSD MIDPOINT was pulled twice. The first pull hit an IBKR timeout and was silently truncated at 2018-11 (49,745 bars). The pull script now retries empty replies and refuses to write a short history. The file below is the complete second pull (107,209 bars). This was found and fixed before any result was seen.

| file | SHA-256 |
|---|---|
| `EURUSD_MIDPOINT.parquet` | `f5611b17ecf7097bfd16f2f6494c134e937fefcf8b6a70f51e2b4a95792f7aa6` |
| `EURUSD_BID.parquet` | `80890440050b8b25ea73280c1a53fc5fdcc392d70c665acf944973c110395893` |
| `EURUSD_ASK.parquet` | `1ffedb30e5cd025a912288bb1a2e79ba9f6811e0e60c0340ad3f4c07cc0e32ed` |
| `GBPUSD_MIDPOINT.parquet` | `bbd56ae7e0fb0dfba5692053b9d078862829ec15962e364b10b3503671e6f569` |
| `GBPUSD_BID.parquet` | `bda0562d79e77f0aab51f2418a5160b7a0aa97fa487f4df06d444ab09d55a7ce` |
| `GBPUSD_ASK.parquet` | `4ffdbd42acc253414e9939b364160c09566f256d781f36e2ca77167fdefe7917` |
| `USDJPY_MIDPOINT.parquet` | `c96cfbcc9b330e67fdae369f828a4df92f0562a8c5ca43819d23d77949c9375b` |
| `USDJPY_BID.parquet` | `932c0bcc97e7035caaf92717ed924595ca829db6c7b597dea7eeb0817bd5410e` |
| `USDJPY_ASK.parquet` | `5efe7e01164448cd9e7293d533bda1ece02dbd36db83eb46493e5d6e828e4442` |
| `USDCHF_MIDPOINT.parquet` | `a6c5ec3bc344187deeb0ae1e94ad8766ca7a212ab291ad7ca53f3d3e36125788` |
| `USDCHF_BID.parquet` | `a429c8f4660ff6558a13f9f16d0754b1b2c408e5969afb23a0426c8e9ca4cd99` |
| `USDCHF_ASK.parquet` | `5d3e3c88910cf83323371ca783137ca765e0932b9c5d1e2744d6155ed05de564` |
| `AUDUSD_MIDPOINT.parquet` | `8257dabd70a2700743c54fd9f00048135ccaf48bf861b8c3f3fd782f36c92e6d` |
| `AUDUSD_BID.parquet` | `62d704c3673da7d8d342e5aef6be3a506eebba4c27fd2947d57d6c1a1e47454d` |
| `AUDUSD_ASK.parquet` | `9210fd37b8990036d7b6613fbedd0900aefe69aae4c36dc0494fdeb43a28543f` |
| `USDCAD_MIDPOINT.parquet` | `3e20ac9624032731184ed9c11aa6982a0b7180da98b516f1db6daf74f94ed989` |
| `USDCAD_BID.parquet` | `02dc9910da2cfed8c4b50332c5b2706f7fea91eef1a43b0018737ffa6aebacb3` |
| `USDCAD_ASK.parquet` | `8daa146f991297076e49c4ec1bfc26de376b27c31a0ce1d65945bbf6317e28a0` |
| `NZDUSD_MIDPOINT.parquet` | `3ece0c7cfd080be919000b19be8ffc92a48ae0bc1b23146522dfa56d7db65f87` |
| `NZDUSD_BID.parquet` | `ba7a2d8e12552576e28ac3fca144a0c55653894a4e1d476d43ff014280736ec5` |
| `NZDUSD_ASK.parquet` | `9a4d19ccec745bc7a1463d7d92ffab8657f323e2de87e3ea4247322b0995dd46` |

### Windows

| window | dates | use |
|---|---|---|
| In-sample (selection) | 2010-01-01 → 2019-12-31 | choose `P_MIN` and `MOVE_MIN`. Before Kronos's FX pretraining (starts 2020). |
| Contamination check | 2020-01-01 → 2025-06-30 | reported only. If it's much better than in-sample, that's evidence of memorisation. |
| **Out-of-sample (sealed)** | 2025-07-01 → the last complete H1 bar before the pre-registration commit | run **once**, after the commit. |

If the speed measurements show 2010–2019 can't be computed in time, the in-sample period is subsampled (whole years, chosen before any run). The out-of-sample period is never subsampled.

### Forecast

- **Model and N: Kronos-small, N = 30.** The rule was the largest model, with N ≥ 30, whose full run fits in ≈ 3 GPU-days. Small takes ≈ 1.7 days at 8.6 Forecasts/s; base would take ≈ 4.0 days at 3.6/s. Weights: `NeoQuasar/Kronos-small` revision `901c26c1332695a2a8f243eb2f37243a37bea320` with `NeoQuasar/Kronos-Tokenizer-base` revision `0e0117387f39004a9016484a186a908917e22426`, pinned in code. Vendor code at commit `67b630e67f6a18c9e9be918d9b4337c960db1e9a`.
- **Fixed settings:**
  - lookback 400, Horizon H = 24 bars, max_context 512;
  - **T = 1.0, top_p = 0.9, top_k = 0** (README defaults);
  - `model.eval()`, clip ±5, volume and amount = 0;
  - base seed 20261126; per-Forecast seed = SHA-256 of `seed|SYMBOL|bar-open ISO time`.
- **Sampler:** `spike/kronos_paths.py:sample_paths_fast`. It returns all N paths, and its output is bit-identical to the vendor-equivalent reference loop. It uses Gumbel-max sampling from a per-Forecast generator, so a Forecast doesn't depend on its batch.
- **Future bar times** fed to Kronos come from a fixed New York-time rule (`spike/calendar.py`), never from the real data:
  - FX: on the hour, with a 17:15 session-open bar;
  - gold: no 17:00 bar.
  - It matches the real 24-bar sequence 98.9% of the time; holidays are the misses.
- **Forecast statistics saved per bar**, since raw paths are too big to store: `p_up`, median close at H, the 10th percentile of path minimum lows, the 90th percentile of path maximum highs, and the 10th and 90th percentiles of the close at H.
- **Cadence:** a Forecast at **every H1 bar close** for every symbol, using only bars up to and including that close.

### Candidate (plan §5)

- `p_up` = the share of paths whose close at H is above the current mid close. `move` = the median path's return at H, in ATR14.
- **ATR14:** Wilder, on MIDPOINT H1, using data up to bar t only.
- **Long** if `p_up ≥ P_MIN` and `move − cost ≥ MOVE_MIN`, with cost = expected round-trip cost in ATR. **Short** mirrors this.
- **Grid (12 sets):** `P_MIN` ∈ {0.55, 0.60, 0.65, 0.70} × `MOVE_MIN` ∈ {0.25, 0.5, 1.0} ATR.
- **Selection:** the single global set with the highest pooled in-sample mean R among sets with ≥ 100 in-sample trades. No per-symbol or per-direction tuning. If no set reaches 100 trades, that's a no-go at the selection stage.
- At most one open position per symbol. A Candidate on a symbol with an open position is dropped.

### Exits (fixed, not tuned)

- **SL (long):** take each path's lowest low over H, then the 10th percentile of those across the N paths. It's kept between 0.5 ATR and 3 ATR from the actual entry fill. Shorts mirror this: the 90th percentile of each path's highest high.
- **TP:** the median path's close at H.
- **Time exit:** at market at the close of the 24th bar after entry, counted in **bars, not hours** (weekends carry).
- **Same-bar SL and TP:** assume SL first. TP first is reported as a sensitivity.
- **Gap through SL or TP:** fill at that bar's open.
- No minimum R:R in this test. That belongs to the Risk Gate.
- **Degenerate TP:** if the actual entry fill is already at or beyond TP (e.g. a long whose ask open is ≥ the median close at H), there's no trade.
- A position blocks its symbol through the bar before its exit bar. A Candidate on the exit bar's close may trade.

### Fills and costs

- **Entry:** the open of bar t+1, at ASK for longs and BID for shorts, + 1 tick of slippage. Never the close of bar t.
- **Exits:** SL and TP trigger on the bid side for longs and the ask side for shorts, + 1 tick of slippage. The Time exit fills at the close on the exit side.
- **Spread:** paid through the historical bid/ask fills.
- **Commission:** `max(0.2 bp × notional, USD 2)` per side, on IDEALPRO (USD 1M account at 1% risk, so no odd-lot penalty).
- **Financing:** a flat 0.5 bp of notional for every 17:00 New York rollover crossed.
- **Sensitivities:** XM-level spread, zero financing, TP first on same-bar hits, and 2 ticks of slippage.
- **R** = net P&L ÷ risk distance (entry fill to SL). Commission and financing are proportional to notional, so in R they're dimensionless: notional ÷ risk = entry ÷ risk distance, whatever the currency. That means no USD conversion is needed. The USD 2 minimum never binds: at USD 10k of risk with an SL ≤ 3% of price, notional is ≥ USD 333k, so 0.2 bp of notional is ≥ USD 6.7.

### Statistics

- **Primary test (one):** pooled out-of-sample mean R at base costs, with a 95% CI from a **cluster bootstrap by calendar day** (5,000 resamples, fixed seed). The clusters stop correlated same-day USD trades from inflating the sample.
- **Secondary:**
  - win rate, PF, max DD in R;
  - per symbol, Holm-corrected over 7. These can never turn a pooled no-go into a go;
  - long and short separately;
  - the contamination window.
- **Selection bias (statistical-significance skill):**
  - Report the deflated Sharpe ratio with the honest trial count: 12 grid sets, plus every variant in the research log.
  - Estimate PBO with combinatorially symmetric cross-validation over the 12 sets on the in-sample years, 10 one-year blocks, purged by 24 bars at each boundary.
- **Baselines:** each trades exactly the Kronos entry bars in its own direction, with the **same risk and reward distances** as the matching Kronos trade, mirrored for direction, plus the same Time exit and costs.
  - random direction (seed 7, 1,000 repeats);
  - momentum: the sign of the last 24-bar return;
  - mean reversion: the opposite sign;
  - **revert to the 400-bar mean:** sign(window mean − close). Added because Kronos forecasts reversion to the window mean even on a pure random walk (`docs/research/kronos-install-speed.md`). If Kronos can't beat this one-line rule, it isn't adding anything.
- **Calibration:** on **every** Forecast, out-of-sample. A reliability table by `p_up` decile, plus the Brier score against a 0.5 constant. Also the directional hit rate against 50%.

### Verdict

- **Go:** pooled out-of-sample mean R > 0, **and** the CI lower bound > 0, **and** n ≥ 100 trades.
  - **Added by D3:** **and** Kronos beats the "revert to the 400-bar mean" baseline, paired on the same symbol and entry bar. The mean of (Kronos R − baseline R) must be > 0, and its day-clustered CI lower bound must be > 0. If Kronos meets the other three conditions but not this one, the verdict is "NO-GO (not better than revert-to-mean)".
- **Inconclusive:** n < 100. Keep collecting forward data in SIGNAL_ONLY mode. Build nothing that trades.
- **No-go:** anything else, including "beats the baselines but ≤ 0 R". Record that as "the Forecast has information but no tradable edge", which feeds the separate, pre-registered fine-tuning decision.

### Target check (reported, never selected on)

- **Monthly returns:** at 1% risk, from the out-of-sample trades in entry order. Report the median month, the 5th percentile and P(month ≥ 2%).
- **Monte Carlo** (Monte Carlo skill): 2,000 simple and 2,000 block-bootstrap resampled trade sequences (5-day blocks). Report the max DD distribution (median, 95th, 99th percentile) and where the historical path sits in it.
- **Risk to reach target:** the risk per trade needed for a 2% median month, and the 95th-percentile drawdown that would come with it. Sizing decisions are made later, against the pessimistic percentiles.

### Jev features (exploratory → confirmatory)

- **The six features:**
  - `|p_up − 0.5|`
  - `move` in ATR
  - dispersion (the 90th minus 10th percentile at H, in ATR)
  - SL distance in ATR
  - ATR14 percentile over the last 400 bars
  - hour of day (UTC)
- **Test:** an in-sample median split on R, Holm over 6. Only an in-sample winner is checked out-of-sample. Anything outside this list is labelled exploratory.

### Authenticity audit (must pass before any number is reported)

Following `backtest-result-authenticity-audit`, the record of each step goes below.

1. **Truncation test** (`scripts/audit_lookahead.py`): cut-offs at three dates in the in-sample window. Every Forecast, Candidate and fill before each cut-off must be identical to the full run.
2. **Future-corruption test:** randomise the bars after a cut-off. Nothing before the cut-off may change. Automated as a regression test.
3. **Feature audit:** confirm that ATR14, the Kronos input window and the cost estimate read only bars ≤ t. **Merge audit:** confirm that BID, ASK and MIDPOINT are aligned by bar-open UTC timestamp, and that the USD conversion uses the same bar close.
4. **Intrabar check:** every SL/TP fill falls inside its bar's real bid/ask range. Gap bars are listed.
5. **Limitation:** OHLC only. The path inside a bar is unknown, and that's covered by the SL-first assumption and the TP-first sensitivity.
6. **Reconciliation:** compare against the IBKR paper fills from the Nautilus spike step 3, once those exist.

### Reproducibility

- Pinned `uv.lock`, plus the Kronos commit hash and model weight checksums recorded here.
- Fixed seeds, checked by running a 1-month slice twice and confirming identical output.
- Config in one versioned file (`config.toml`) and not hard-coded.
- Results tagged with the code commit and the data SHA-256.

## Research log

Every variant run, including failed ones, gets one line here: date, variant, window, n, mean R. This feeds the deflated Sharpe trial count.

| date | variant | window | n | mean R | note |
|---|---|---|---|---|---|
| — | — | — | — | — | nothing run yet |

## Pre-registration commit

**`fcbef959e8fd1dde5d0e4d918d8be5dbc86740f6`** (`fcbef95`), on branch `kronos-edge-test`, 2026-11-26 ~18:25 UTC. The rules above are binding from this commit. The out-of-sample run is unsealed with `--unseal fcbef95`.

## Disclosed deviations

### D1 (2026-11-27 ~02:10 UTC): baseline geometry keyed by symbol (bug fix, approved by the user)

- **Bug:** `scripts/evaluate.py` keyed the baselines' mirrored risk and reward distances by timestamp only (`{ts: (risk, reward)}`), pooled over all symbols.
  - A baseline on one symbol could trade at a bar where only *another* symbol had a Kronos trade.
  - It would then use that symbol's distances, in the wrong price units (e.g. EURUSD's 0.0018 on USDJPY).
- **Fix:** the geometry is now `{symbol: {ts: (risk, reward)}}`. Each baseline, and each random-direction repeat, mirrors only its own symbol's Kronos trades, as the plan intended ("same entry bars, same risk and reward distances, own direction").
- **Check (2019, EURUSD and USDJPY):** a baseline that copies Kronos's direction trades 563 of 564 and 612 of 613 of Kronos's own entry bars.
  - Median risk: 0.00185 vs 0.00180 (EURUSD), and 0.161 vs 0.155 (USDJPY).
  - 98–99% of trades have the same exit reason.
  - Only counts and distances were looked at, no R, so it isn't a trial.
- **Unchanged, disclosed:**
  - The baselines take every Kronos entry bar, even when the baseline's own previous trade is still open. Kronos's entries never overlap, but a baseline going the other way can exit later.
  - The mirror is anchored on the mid close, not the filled entry, so the distances differ slightly.
- **Effect:** only the secondary baseline comparison. The primary verdict, the selection and the statistics are untouched.
- **Timing:** fixed before any evaluation was run and before the seal was broken.

### D2 (2026-11-27 ~02:05 UTC): forecast files refuse to resume from another window (bug fix, approved by the user)

- **Bug:** `scripts/run_forecasts.py` names output files `SYM_YEAR.parquet` and skips any file that already exists.
  - The contamination run (2020 → 2025-06) and the sealed run (2025-07 →) both write `SYM_2025.parquet`.
  - With the same output folder, the second run would silently skip 2025, and the sealed exam would lose 2025-07 → 2025-12 (or the contamination check would lose 2025-01 → 06).
- **Fix:** before skipping an existing file, the script checks that its timestamps lie inside the requested window, and stops with an error if they don't.
  - The sealed run will also use its own folder: `--out results/forecasts/small_n30_oos`.
- **Check:** tested on `EURUSD_2019.parquet`. With the same window it resumes; with a 2019-07 → window it stops with the error.
- **Effect:** none on Forecast values, which are seeded per Forecast and unchanged. It only prevents missing data.
- **Timing:** edited while the in-sample run was going. The change only touches the "file already exists" branch, which no remaining in-sample symbol hits (USDCAD started on the new code at 02:11 and runs normally).

### D3 (2026-11-27 ~02:30 UTC): a GO must also beat the revert-to-mean baseline (stricter rule, approved by the user)

- **Gap:** the plan said "if Kronos can't beat this one-line rule, it isn't adding anything", but the verdict didn't require it.
  - The in-sample Forecasts agree with sign(400-bar mean − close) 88% of the time (92% among confident Forecasts), so this risk is real: Kronos could pass on R > 0 while only repeating the one-line rule.
- **Rule added:** a GO also needs Kronos to beat that baseline, paired on the same symbol and entry bar.
  - The mean of (Kronos R − baseline R) must be > 0, with its day-clustered bootstrap CI lower bound > 0 (the same test as the primary verdict).
  - Otherwise the verdict is "NO-GO (not better than revert-to-mean)".
  - The same comparison is reported at every stage that runs the baselines.
- **Direction:** this only makes a GO harder. It can't turn a NO-GO into a GO.
- **Timing:** decided before any evaluation was run and before the seal was broken. The user chose it after it was put to them as a yes/no question.

### D4 (2026-11-27 ~11:40 UTC): the feature median split handles ties (bug fix, approved by the user)

- **Bug:** `feature_tests` in `scripts/evaluate.py` split each feature at `x > median`. With N = 30 paths, `|p_up − 0.5|` only takes values k/30, and in the 2019 smoke test (EURUSD and USDJPY) 57% of trades had all 30 paths agree (`p_edge` = 0.5 = the median = the max).
  - The "above" group was empty, so the difference was `nan`.
  - In the permutation test, `abs(perm) >= nan` is always False, so the code printed **p = 0.000, Holm p = 0.000**: a false "significant feature", which would then be "confirmed" out-of-sample.
- **Fix:** split at `x > median`. If that leaves one side empty, split at `x ≥ median` instead. If a side is still empty, the feature is reported as "not testable (ties)" with p = 1. Three unit tests cover this (`tests/test_evaluate.py`).
- **Effect:** only the exploratory feature tests. The selection rule, the primary verdict and every other statistic are untouched.
- **Timing:** found by a structure-only smoke test (every number masked, so not a trial) on 2019 data, and fixed before the in-sample selection ran and before the seal was broken. The user chose the tie-aware split over "mark untestable only" and "leave as is".

### D5 (2026-11-27 ~12:50 UTC): bad BID/ASK ticks are cleaned (data fix, approved by the user)

- **Problem:** IBKR's H1 BID/ASK history has impossible prints, mostly on the 22:15 UTC bar after the daily break.
  - Example: the AUDUSD 2012-02-23 22:15 BID open is **79.95** (true ≈ 1.0717).
  - Example: the EURUSD 2014-01-06 22:15 BID low is 1.3200 and the ASK open 1.4240 (true ≈ 1.3634).
  - The pre-registered fill rules turned them into a **+44,411 R** TP gap-fill and a −22 R SL gap-fill, which made the first in-sample selection (run 1, `results/select_v1_badticks.md`) invalid.
  - The pre-registered cleaning (`_bad`: malformed OHLC) can't catch them, because each bar is internally consistent. The intrabar audit can't either, because the bad tick *defines* the bar's range.
- **Rule** (`clean_quotes` in `spike/data.py`), fixed from price data before any re-run:
  - A bar is a bad quote bar if any BID or ASK OHLC value lies more than **3 ATR** (the previous bar's ATR14, causal) outside [mid low, mid high], or if BID > ASK in any of OHLC.
  - Its BID and ASK OHLC are replaced by the mid OHLC ∓ the median close half-spread of the previous 400 bars.
  - Spread widening up to 3 ATR is kept as a real rollover cost.
- **Scope:**
  - The same rule applies to every window, the exam included.
  - **MIDPOINT is never changed,** so the Kronos inputs and the 434,700 saved Forecasts are unaffected (`run_forecasts.py` never reads BID/ASK).
  - It replaces 384 bars over all dates: EURUSD 55, GBPUSD 36, USDJPY 46, USDCHF 68, AUDUSD 44, USDCAD 54, NZDUSD 86.
  - 3 unit tests (`tests/test_data.py`).
- **Disclosed residual risks, not fixed:**
  - The MIDPOINT bars also have spikes: 60–130 bars per symbol with a wick > 3 ATR beyond the open, close and previous close, and 9–35 per symbol opening with a gap > 3 ATR, mostly at 22:15. Some are real events; some are probably bad prints. They're in the Kronos inputs and the ATR, and cleaning them would mean re-running all the Forecasts.
  - IBKR's median close spread is often 0 (e.g. EURUSD 2014), so the base cost model may understate the spread. The pre-registered XM-spread sensitivity covers this.
- **Timing:** decided after run 1's in-sample result was seen (it was dominated by the bad ticks; see the journal), and before the seal was broken. The user chose the 3 ATR threshold over 1 ATR, over skipping the 22:15 bar, and over stopping. The 12-set selection re-runs as run 2, and both runs are in the research log.

## Result (2026-11-27 15:10 UTC)

**NO-GO.** The sealed exam (2025-07-01 → 2026-11-26, 7 majors, set P_MIN 0.55 / MOVE_MIN 0.25, HEAD `fabc439`, run once): n = 6,813, mean **−0.188 R [−0.243, −0.129]** at base costs, and −0.146 R before costs.
- Kronos beats 25.1% of the random-direction repeats.
- Paired against revert-to-the-400-bar-mean, it's −0.016 R [−0.035, +0.003].
- Its calibration (Brier 0.435 against 0.250 for a constant) shows over-confident Forecasts with no directional information (hit rate 0.508).
- The full report is in `spikes/kronos/results/oos.md`; the narrative and the audit are in `docs/journal/kronos-edge-test.md` (14:33–15:10).

**Authenticity audit, step 4 (intrabar):** 6,812 of 6,813 fills fall inside their bar. The exception, and 27 similar trades, enter on a wide-spread reopen bar whose exit-side open is already through the SL. The simulator fills them at the SL instead of the open, which is optimistic by −0.0014 R on the pooled mean. This is disclosed and not fixed; it can't change the verdict.
