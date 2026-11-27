# Independent investigation: JEV QUANT v2, Kronos Edge test

**Scope.** This report was produced on Thursday 2026-11-26, between 21:00 and 21:30 UTC (23:00–23:30 Egypt time, UTC+2).

The investigation was **read-only**:
- No project file, configuration or parameter was changed.
- No process was started, stopped or restarted.
- No profit or loss figure was calculated.
- The only new numbers are descriptive statistics of the existing Forecast files. They use no future prices (§4 and §8 say how they were computed).

**Author's disclosure.** This report was written by the same AI agent that designed and implemented the work it reviews. I've tried to look for my own mistakes. A reader should still treat this as a self-review and weigh it accordingly.

**Labels used:**
- ✅ **Verified:** checked directly against code, files, logs or `git`.
- ⚠️ **Inference / estimate:** reasoning or an estimate, not a measurement.
- ❌ **Confirmed issue:** a defect established by reading the code.
- **Unverified:** a claim recorded in project documents whose underlying evidence (script or output) isn't saved in the project.

**Terms defined at first use:**
- **R:** profit or loss expressed in units of the initial risk. 1R = the distance from the entry fill to the stop loss. +1R means "won as much as was risked".
- **ATR14:** Average True Range over 14 bars (Wilder smoothing). A measure of typical bar size, used to scale distances.
- **In-sample (IS):** data used to choose settings.
- **Out-of-sample (OOS):** data not used to choose anything. Here it's a "sealed exam", run once.
- **Pre-registration:** writing down every rule, and committing it to git, before any result is seen.
- **Baseline:** a deliberately simple strategy that Kronos must beat to show it adds value.
- **Bootstrap CI:** a confidence interval estimated by resampling the trades many times.

---

## 1. Executive summary

**What the project is trying to achieve.**
- The question is whether **Kronos** can earn a positive return after realistic costs, trading the 7 major FX pairs on 1-hour bars, on data it has never seen.
- Kronos is a publicly released AI model, pretrained on price candles from many markets.
- It's used **zero-shot**: as released, with no extra training.
- This test is the **go/no-go gate** for the rest of the planned system (`JEV_QUANT_MASTER_PLAN.md` §8 and §12 Phase 1). That system is:
  - "Jev", an AI trade-approval layer;
  - an independent Risk Gate;
  - execution on an Interactive Brokers (IBKR) paper account.

**The user's goal** is 2–6% a month.
- By design, that number is **reported, never optimised for** (`docs/research/kronos-edge-test.md`, "User goal").
- Tuning toward a return target on data already seen is the classic way to produce a backtest that fails live.

**Current state (21:25 UTC):**
- ✅ The price data is downloaded and frozen. SHA-256 checksums of all 21 files are recorded.
- ✅ All rules are committed to git before any result: commit `fcbef95`, branch `kronos-edge-test`.
- ✅ The GPU is generating in-sample (2010–2019) Forecasts: **26 of 70 symbol-years done**.
- ✅ **No profit or loss figure has been computed yet**, for any period.

**The four things a reviewer most needs to know:**

1. ❌ **The baseline comparison code has a bug** (`scripts/evaluate.py:241`).
   - The table of trade geometry (risk and reward distances) that the baselines copy is keyed by timestamp only, not by (symbol, timestamp), so the symbols get mixed together.
   - The **primary GO/NO-GO verdict is not affected**, because it uses Kronos's own trades only.
   - But the comparison against the simple strategies will be wrong.
2. ❌ **A file-name collision for the year 2025** (`scripts/run_forecasts.py:80-82`).
   - The contamination window and the sealed exam both write `SYM_2025.parquet`.
   - Whichever runs second silently skips its 2025 data.
   - With the planned order (the exam first), the contamination report loses 2025-H1. If the order were reversed, the **exam would silently lose 2025-H2**.
3. ⚠️ **Kronos behaves largely like a "revert to the recent average" rule.**
   - Its forecast direction matches the sign of (400-bar average − current close) **88.4%** of the time, and **91.6%** among its confident forecasts.
   - Its median forecast move over 24 hours is **4.06 ATR**, which is large.
   - **Consequences:**
     - the threshold grid (0.55–0.70 probability, 0.25–1.0 ATR move) probably filters very little;
     - the 12 settings may produce nearly identical trades;
     - the comparison against a "revert to the 400-bar mean" baseline becomes the most important scientific question in the test. That's exactly the comparison item 1 breaks.
4. ⚠️ **The steps after the in-sample run aren't scheduled automatically.** Selection, the sealed exam and the verdict all need the agent to run them in a live session. No cron job or background trigger exists for them.

---

## 2. System architecture

```
IBKR Gateway (paper account, read-only API, 127.0.0.1:4002)
   │  scripts/pull_ibkr.py   →  data/ibkr/<SYM>_{MIDPOINT,BID,ASK}.parquet
   ▼
spike/data.py: load()   — cleaning + alignment of the three series → Bars
   ▼
scripts/run_forecasts.py — at every H1 bar close: last 400 MIDPOINT bars → Kronos-small
   │                       → 30 sampled paths × 24 future bars
   │  (spike/kronos_paths.py: sample_paths_fast;  spike/calendar.py: future_bar_times)
   │  → results/forecasts/small_n30/<SYM>_<YYYY>.parquet   (summary statistics only)
   ▼
scripts/evaluate.py      — Candidate rule → simulate() → trades in R → statistics → verdict
   │  (spike/strategy.py, spike/stats.py)
   ▼
results/{select,contamination,oos}.md, *_trades.parquet, selected_set.json
```

Everything lives in `spikes/kronos/`. It's a research **spike**, not the production system. Jev, the Risk Gate and order execution don't exist yet, and that's deliberate: they wait on this test.

**Environment:**
- ✅ `spikes/kronos/pyproject.toml` plus `uv.lock`: torch 2.8.0+cu128, Python 3.12, pandas 2.2.2, ib_async 2.0.1.
- ✅ The Kronos source is cloned unmodified into `vendor-Kronos/` at commit `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (gitignored).
- ✅ Hardware: NVIDIA GTX 1650 with 4 GB of VRAM.

---

## 3. Trading logic: exactly how it decides to trade

| # | Question | What the code actually does | Where |
|---|---|---|---|
| 1 | Data source | IBKR historical data via the paper-account Gateway. `useRTH=False`, `whatToShow` ∈ {MIDPOINT, BID, ASK}, 1-year requests ≥ 11 s apart. Read-only: it never places orders. | `scripts/pull_ibkr.py` |
| 2 | Instruments | The 7 majors: EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD. User decision on 2026-11-26, before any result. | `spike/data.py:18`; `scripts/run_pre_oos.sh:8` |
| 3 | Timeframe | H1 (1-hour bars). The timestamp is the bar-open time in UTC. IBKR's session-open bar starts at 17:15 New York time and is 45 minutes long. | `pull_ibkr.py` (`barSizeSetting="1 hour"`, `formatDate=2`) |
| 4 | History | ✅ 2009-09-01 → 2026-11-26, with 106,598–107,212 bars per file (see the notes below). | Checksum table in `docs/research/kronos-edge-test.md` |
| 5 | Cleaning | See the notes below. | `spike/data.py:30-61` |
| 6 | Kronos input | 400 MIDPOINT OHLC bars, with volume and amount set to 0. Z-score normalisation over those 400 bars only, clipped to ±5. Time features: minute, hour, weekday, day, month, in **UTC**. | `spike/kronos_paths.py:185-194`, `:75-76` |
| 7 | Kronos output | 24 future OHLC bars, generated autoregressively (one bar at a time, each bar a pair of tokens). | `kronos_paths.py:179-267` |
| 8 | The 30 paths | 30 independent samples from the model's predictive distribution, all from the same context. Each has its own random (Gumbel) noise, with a fixed seed per (symbol, bar). | `kronos_paths.py:69-72`, `:79-88` |
| 9 | Interpreting paths | Summarised per Forecast (see the notes below). The raw paths aren't stored. | `run_forecasts.py:96-101`; `spike/strategy.py:70-80` |
| 10 | Signal | **Long** if `p_up ≥ P_MIN` **and** `move − cost ≥ MOVE_MIN`; **short** is the mirror. `move = (median_close − close) / ATR14`. `cost` is the expected round trip in ATR: the spread at bar t's close, plus 2 ticks, plus 2 × 0.2 bp commission. | `strategy.py:83-95` |
| 11 | Accept or skip | Skipped if there's no signal; if the symbol already has an open position (`busy_until`); if there's no bar t+1; or if the TP is "degenerate" (the entry fill is already at or past it). | `evaluate.py:81,108`; `strategy.py:111,118,125` |
| 12 | Entry price | The open of bar t+1: **ASK + 1 tick** for longs, **BID − 1 tick** for shorts. Tick = 0.00005, or 0.005 for USDJPY. Never the close of bar t. | `strategy.py:115,122`; `data.py:15` |
| 13 | Stop Loss | See the notes below. | `strategy.py:17,116,123` |
| 14 | Take Profit | Yes: the median path close at bar 24. If it's on the wrong side of the actual entry, there's no trade. | `strategy.py:117-126` |
| 15 | Sizing and risk | See the notes below. | `evaluate.py:287-302`; `stats.py:120-123` |
| 16 | Simulation | See the notes below. | `strategy.py:130-153` |
| 17 | Metrics | See the notes below. | `strategy.py:155-161`; `spike/stats.py` |

**Notes on some of the questions:**

- **(4) History:**
  - AUDUSD MIDPOINT was downloaded twice. The first copy was silently truncated at 2018-11 (§5).
  - Forecasts start in early January 2010, because the first 399 bars are needed as lookback (`run_forecasts.py:86`).

- **(5) Cleaning:**
  - ✅ Drops malformed bars: high < low, open or close outside the bar's range, or non-finite values.
  - ✅ Keeps only timestamps present in all three series (intersection, `data.py:44`).
  - ✅ No forward-filling.
  - ✅ *Flags* (but keeps) bars whose mid return exceeds 10 × ATR.
  - ❌ The pre-registration's XM cross-checks are **not implemented** (§12). Those were: spot-check flagged bars against XM, and check 20 random bars per symbol.

- **(9) Interpreting the paths.** The statistics saved per Forecast are:
  - `p_up`: the share of paths whose close at bar 24 is above the current close;
  - `median_close`: the median close at bar 24;
  - `sl_long`: the 10th percentile of each path's lowest low;
  - `sl_short`: the 90th percentile of each path's highest high;
  - `q10_close`, `q90_close`: the 10th and 90th percentiles of the close at bar 24.

- **(13) Stop Loss:**
  - **Long:** the 10th percentile, across the 30 paths, of each path's lowest low.
  - **Short:** the mirror, the 90th percentile of each path's highest high.
  - Either way it's then **clamped to 0.5–3 ATR from the actual entry fill**.

- **(15) Sizing and risk:**
  - **The simulation doesn't size positions.** Everything is in R.
  - Commission and financing are proportional to notional, so in R they equal `bp × entry / risk_distance`. That's currency-free.
  - "1% risk per trade" appears only in the monthly-return target check, compounded as `∏(1 + 0.01·R) − 1`.

- **(16) Simulation:**
  - The trade walks bars e … e+23 (24 bars), with e = t+1.
  - Longs exit on the BID side and shorts on the ASK side.
  - **Gap:** if a bar after the entry bar *opens* beyond the SL or TP, it fills at that open.
  - **Both SL and TP inside one bar:** the SL is assumed first (`tp_first=False`).
  - **Otherwise:** a **Time exit** at the close of the 24th bar.
  - There's 1 tick of slippage on every exit, including the TP. That's conservative.

- **(17) Metrics:**
  - `r_gross` = direction × (exit − entry) / risk. Spread and slippage are already in the fills.
  - `r_net` = `r_gross` − commission (0.2 bp per side) − financing (0.5 bp per 17:00 New York rollover crossed).
  - `stats.py` provides:
    - the mean with a 95% CI from a cluster bootstrap by calendar day (5,000 resamples, seed 0);
    - win rate, profit factor (PF = gross wins ÷ gross losses), and max drawdown in R;
    - Holm correction (a multiple-testing adjustment of p-values);
    - the deflated Sharpe ratio (DSR: a Sharpe ratio adjusted for how many variants were tried);
    - PBO by CSCV (probability of backtest overfitting via combinatorially symmetric cross-validation);
    - Monte Carlo drawdown distributions.

---

## 4. Kronos deep dive

**Model:**
- ✅ `NeoQuasar/Kronos-small`, revision `901c26c1332695a2a8f243eb2f37243a37bea320`.
- ✅ Tokenizer `NeoQuasar/Kronos-Tokenizer-base`, revision `0e0117387f39004a9016484a186a908917e22426`.
- Both are pinned in `spike/kronos_paths.py:56-59`.
- About 24.7M parameters, with a maximum context of 512 tokens.
- ⚠️ The revisions are pinned, but **weight checksums aren't recorded**, although the pre-registration says they are ("Reproducibility").

**Why Kronos-small:**
- The pre-registered rule was "the largest model with N ≥ 30 paths whose full run fits in ≈ 3 GPU-days".
- Measured: small at 8.6 Forecasts/s (≈ 1.7 days), base at 3.6/s (≈ 4.0 days).
- The choice was made on **speed only**, not on any result. Source: `docs/research/kronos-install-speed.md`.

**Input:** a 400 × 6 array: OHLC, plus volume = 0 and amount = 0.
- It's normalised with the mean and standard deviation of those 400 bars only (`kronos_paths.py:187-188`), so there's no future information.
- The tokenizer turns each bar into a two-part token (s1 and s2, 10 bits each).
- ⚠️ **Volume is zero.** The Kronos paper says FX was *evaluated* without volume. It doesn't say whether FX was *trained* with volume. Unknown (`docs/research/kronos-training-data.md:49`).
- ⚠️ **The time features are in UTC.** The timezone used in training is unknown.

**Output:** 24 tokens, decoded back to OHLC and de-normalised with the same mean and standard deviation.

**Are the 30 paths independent scenarios?**
- They're **independent samples from the model's own distribution**, conditioned on the identical context.
- They are **not 30 independent pieces of evidence about the market**.
- If the model is overconfident (a narrow, one-sided distribution), all 30 paths will agree. That agreement says nothing about whether the forecast is right.
- Sampling: temperature 1.0, top_p 0.9, top_k 0 (`kronos_paths.py:43-52`).

**What "directional agreement" and "confidence" mean here:**
- They mean `p_up` and nothing else: the fraction of the 30 paths that end above the current close.
- `p_up = 1.0` means all 30 paths ended higher. **It's the model's opinion, not a calibrated probability.**
- Calibration is measured only in the exam stage: a reliability table by `p_up` decile, the Brier score against a constant 0.5, and the directional hit rate (`evaluate.py:264-279`).

**Changes from the vendor's inference code** (all documented in `kronos_paths.py:1-12`):
1. The vendor code **averages the paths** (`vendor-Kronos/model/kronos.py:467`). The project's sampler returns every path.
2. The vendor predictor **never calls `eval()`**, so the model's 25% dropout stays active during forecasting. Fixed at `kronos_paths.py:64-65`.
3. The vendor's random draws depend on the batch composition. Replaced with Gumbel-max sampling from one seeded generator per Forecast (`:79-88`), so each Forecast is reproducible on its own.
4. A fast sampler with a key/value cache and a context shared across the paths (`:179-267`).
   - Recorded as **bit-identical** to a reference loop, and 68× faster.
   - ✅ The comparison script (`scripts/check_fast.py`) exists, and an assertion (`:183`) guards the condition under which the fast path is exact.
   - **Unverified:** the "100% identical" result is recorded in the docs and the journal, but no saved output exists in `results/`.

**Future bar times:**
- `spike/calendar.py` generates them from a fixed New York-time rule, never from the data, so that future holidays can't leak in.
- Recorded result (`kronos-install-speed.md:71-73`): it matches the real next bar 100% of the time, and the full 24-bar sequence 98.9%, over 3,000 random EURUSD and GBPUSD bars.
- **Unverified:** the script that produced this isn't saved in the project.

---

## 5. Work completed

### V1 and why it failed

- ✅ V1 traded **SQ9 levels** (45° geometric price levels) on MetaTrader 4. The source is `docs/research/edge-revalidation.md`.
- **Results:**
  - Real levels were respected 55.4% of the time. Deliberately shifted fake levels were also respected 55.4% (edge −0.0 percentage points). That's **no edge**.
  - The strategy's out-of-sample result: 119 trades, mean **−0.10 R** (95% CI −0.35 to +0.17), PF 0.86.
  - Even with zero costs it was −0.04 R.
  - All 16 parameter sets were negative even in-sample.
- **Why it failed:** the idea itself had no edge. It wasn't an implementation problem.

**Lessons carried into V2:**
- pre-registration before any result;
- one global parameter set chosen by a fixed rule, with at least 100 in-sample trades;
- control or baseline comparisons;
- Holm correction;
- the SL-first convention;
- a strict verdict rule.

### Chronology, 2026-11-26 (UTC)

The sources are `docs/journal/kronos-edge-test.md` (written by the agent during the work; "~" times are approximate), `git log`, and the logs.

| Time | Event | Evidence |
|---|---|---|
| ~14:15 | Design interview ("grilling"): 23 methodology decisions, all accepted by the user | journal; ticket 06 |
| 14:45–14:56 | Disk space freed; Kronos and CUDA torch installed. The first download timed out; fixed with `UV_HTTP_TIMEOUT=600` | journal |
| ~15:00 | Vendor code review: the 3 problems above, plus the calendar-leak risk | journal; `kronos_paths.py:1-12` |
| 15:15 | IBKR history download started | `data/pull.log` |
| 15:18–15:23 | Simulator and statistics written test-first; 24 tests pass | `tests/` |
| ~15:45 | First speed test: 11 s per Forecast, ≈ 160 days for the full test | journal |
| 15:53 | Fast sampler: 68× faster, bit-identical (unverified, see §4) | journal; `check_fast.py` |
| ~15:55 | Kronos found to revert to the mean even on a synthetic random walk; a 4th baseline added | `kronos-install-speed.md:12` |
| ~16:00 | Kronos-small with N = 30 chosen by the speed rule | `kronos-install-speed.md` |
| 16:12–16:18 | 3 lookahead audits, all PASS | `results/audit_lookahead.md` |
| ~16:15 | The first long run was slowed by a concurrent CPU audit; both stopped and restarted | journal |
| ~16:20 | The user restricted the universe to the 7 majors | ticket 06; `data.py:18` |
| 18:10 | **AUDUSD MIDPOINT found silently truncated** (49,745 bars, from 2018-11). An IBKR request timed out; the empty reply was read as "no more history". Fixed with retries plus a refusal to write a short history. Re-downloaded: 107,209 bars | `data/pull.log:237-239`; `pull_ibkr.py` |
| 18:20 | Data frozen with SHA-256 for 21 files. Exam end fixed at 2026-11-26 15:00 UTC (the earliest file end) | pre-registration doc |
| ~18:25 | Commits **`fcbef95`** (the pre-registration) and `6a4bec9` (records its hash) on branch `kronos-edge-test` | `git log` |
| ~20:55 | Health check of the Forecast files | journal (**uncommitted change**) |

### Verification of the reported figures

All of these were recomputed at 21:07 UTC from `results/forecasts/small_n30/*.parquet`.

| Reported figure | Status | Detail and limitations |
|---|---|---|
| 143,028 Forecasts | ✅ correct at the time | EURUSD 62,157 + GBPUSD 62,157 + USDJPY 2010–2012 (18,714) = 143,028. **Now 155,446** (26 files). |
| EURUSD complete | ✅ | 10 files, 2010-01-03 22:15 → 2019-12-31 20:00 UTC |
| GBPUSD complete | ✅ | Same span |
| USDJPY started | ✅ | Now 2010–2015 done; 2016 running |
| Zero missing values | ✅ | 0 NaN in all columns |
| Zero duplicate bars | ✅ | No duplicate (symbol, ts). **Limitation:** checked on the Forecast files, not on the raw price files. |
| 100% correct range ordering | ✅, but **a weak check** | q10 ≤ median ≤ q90 computed from the same 30 values is **mathematically guaranteed**. It only confirms the files are stored correctly. **It says nothing about forecast quality.** I should have said so when I reported it. |
| SL on the correct side 99.8–99.9% | ✅, with qualification | 99.83% (long) and 99.86% (short), measured **relative to bar t's close, not the actual entry fill**. The other ~0.15% don't create bad trades: `simulate` clamps the SL to 0.5–3 ATR from the real entry (`strategy.py:116,123`), so the actual SL is always on the correct side. |
| Stable 8.67 Forecasts/s | ✅ | Every completed year took 714–721 s, at 8.63–8.68 Forecasts/s. Source: `results/run_is.log`. |
| 30 paths with strong directional agreement | ✅, with correction | 58.3% of Forecasts have all 30 paths on one side (`p_up` exactly 0 or 1), and 76.7% have `p_up` ≥ 0.9 or ≤ 0.1. **Correction:** I earlier reported "median `p_up` 0.87". That was true on 23 files, but on 25 files it's 0.53. The distribution is **bimodal** (peaks at 0 and 1), so its median is unstable and not meaningful. The accurate description is "strongly polarised". |

**Limits of the health check:**
- It verifies that the files are sound, **not that the forecasts are right**.
- It was logged in the journal, but that edit is **not committed** (`git status`: `M docs/journal/kronos-edge-test.md`).

### Tests and audits

- ✅ **24 unit tests** (`spikes/kronos/tests/`): 12 for the simulator, 6 for the calendar, 6 for the statistics. The last run, at the commit, gave 24 passed.
- ❌ **`scripts/evaluate.py` has no tests and has never been run on real data.** It contains the bugs in §12.
- ✅ **Lookahead audit** (`scripts/audit_lookahead.py`) on EURUSD 2015-03, GBPUSD 2012-06 and EURUSD 2018-09.
  - It compares Forecasts made with the full data, with the data cut off after a date, and with the data after that date replaced by garbage.
  - Max difference 0, and identical decisions for all 12 parameter sets → PASS.
  - **Limitation:** it covers the Forecast and the Candidate decision only, **not the fills or `evaluate.py`**. The pre-registration says "every Forecast, Candidate and fill".
  - **Limitation:** it's not a pytest regression test, although the pre-registration says it is automated as one.

### Data flags

Source: `results/run_is.log`.
- EURUSD: 7 bars over 10 ATR, including 2013-09-18 (FOMC), 2013-11-07 (ECB cut) and 2016-06-03 (NFP).
- GBPUSD: 3, including 2016-10-06 23:00 (the sterling flash crash).
- USDJPY: 16.
- All are kept, and **none was cross-checked against XM**.
- ⚠️ **Contradiction:** the journal says EURUSD had 2 flags; the log shows 7. The 2 were those visible in the audit window, so the journal is inaccurate on this point. The log is authoritative.

---

## 6. Current runtime status (21:25 UTC)

**Processes** (`ps`):
- `bash ./scripts/run_pre_oos.sh`, PID 1219028, running for about 3 h 13 m. It loops over the 7 symbols in order.
- `.venv/bin/python -W ignore scripts/run_forecasts.py --model small --paths 30 --batch 12 --from 2010-01-01 --to 2020-01-01 --symbols USDJPY`, PID 1334614.
  - It's using about 371% CPU (≈ 3.7 cores).
- No data download is running. It was stopped deliberately at 18:10, because the crosses and gold aren't needed for this test.

**GPU:** GTX 1650 at 98–100% utilisation, 3,549 of 4,096 MiB, 63 °C, 49.6 W. The load average is about 4.

**Bottleneck:** ⚠️ GPU-bound, with a significant CPU share.
- The random noise is generated on the CPU, one generator per Forecast.
- Earlier, competing CPU work measurably slowed the job.
- No network is involved.

**Progress:**

| Symbol | Years done | Forecasts |
|---|---|---|
| EURUSD | 10/10 | 62,157 |
| GBPUSD | 10/10 | 62,157 |
| USDJPY | 6/10 (2016 running) | 31,132 |
| USDCHF, AUDUSD, USDCAD, NZDUSD | 0/10 | queued |

- **Errors, warnings, retries, skips:** none. `results/run_is.log` contains only the data-flag lines and progress lines. `results/run_pre_oos.log` is an empty leftover from an earlier attempt.
- ⚠️ **Estimate:** 44 symbol-years remain × ~718 s ≈ 8.8 hours. That puts completion at **about 06:10 UTC on Friday 2026-11-27 (≈ 08:10 Egypt time)**, if the speed holds and the laptop doesn't sleep or throttle.

---

## 7. Research methodology

### Why 2010–2019?

- ✅ The Kronos paper (Table 13) says its FX pretraining data **starts on 2020-01-31** (`docs/research/kronos-training-data.md:12`).
- So 2010–2019 FX is probably unseen as FX, which makes it suitable for choosing thresholds.
- **Caveats:**
  - ⚠️ That relies on the paper. **Nobody has confirmed that the Hugging Face weights are the paper's checkpoints** (Kronos GitHub issue #265 is unanswered).
  - The model did see other markets before 2010 (equities from 1990, Chinese futures from 2010), so generic price patterns may be familiar to it.

### The three windows

| Window | Dates | Role |
|---|---|---|
| **Development / in-sample** | 2010-01-01 → 2019-12-31 | Choose `P_MIN` and `MOVE_MIN` only. |
| **Contamination check** (a validation-style window, report only) | 2020-01-01 → 2025-06-30 | Kronos may have trained on this. If results here are much better than in-sample, that suggests memorisation. It never affects the verdict. |
| **Sealed exam (OOS)** | 2025-07-01 → 2026-11-26 15:00 UTC | **Run once.** The weights were uploaded on 2025-06-30/07-01 and never replaced (`kronos-training-data.md:10,61`), so this is after any possible training. |

### What "pre-registered" means here

Before any profit figure was seen, these were all written into `docs/research/kronos-edge-test.md` and committed (`fcbef95`):
- the data and its checksums;
- the windows;
- the model, its revisions and the seeds;
- the Candidate rule;
- the threshold grid and the selection rule;
- the SL, TP and Time exit rules;
- the costs;
- the statistics and the baselines;
- the verdict rule.

Any later change must be listed under "Disclosed deviations". That section is still empty.

**What can still change:**
- Only `P_MIN` and `MOVE_MIN`, and only through a fixed rule: of the 12 sets, the one with the highest pooled in-sample mean R among sets with ≥ 100 trades (`evaluate.py:182-186`).
- Everything else is frozen.

**What would violate the protocol:**
- running the exam more than once, or before selection;
- using any set other than the one the rule picks;
- changing any rule after seeing in-sample results without disclosing it;
- dropping or adding symbols after seeing their results;
- running extra variants without logging them in the research log, which feeds the deflated Sharpe trial count.

**Why profit is withheld until the right stage:**
- If EURUSD's profit were computed now, it could tempt changes: a threshold, a dropped symbol, an extra filter.
- Every "fix after looking" adds hidden degrees of freedom and makes the final result look better than it is. That's **data snooping**.
- Computing once, on all 7 symbols, with the fixed rule keeps the number of trials known (12). That keeps the deflated Sharpe and PBO honest.

### Did the sealed exam influence any decision?

- ✅ There's **no evidence that any exam-period result was seen**:
  - no 2025 or 2026 Forecast files exist;
  - the seal is enforced in code (`run_forecasts.py:38-50`): any Forecast at or after 2025-07-01 requires `--unseal` with a commit that is an ancestor of HEAD and is recorded in the pre-registration document.
- **Transparency caveats:**
  - ⚠️ **Exam-period prices were downloaded and read, but not results:**
    - the cleaning log prints the timestamps of large moves in that period (2025-08-22, 2025-09-02);
    - the calendar check sampled bar *times* from the whole history.
  - ⚠️ **The designing agent's (my) training knowledge extends to June 2026**, overlapping about 12 months of the exam window. The rules weren't tuned on it. But the designer has general awareness of how markets behaved then. That's a theoretical source of bias and should be disclosed.
  - ⚠️ V1 used XM data 2023-07 → 2026-11 as its out-of-sample period, for an unrelated strategy.

### Safeguards against bias

| Bias | Safeguard | Status |
|---|---|---|
| Look-ahead in the Forecast | Window ≤ t; per-window normalisation; future bar times from a fixed rule; 3 audits PASS | ✅ |
| Look-ahead in ATR and cost | `wilder_atr` uses bars ≤ t (unit test `test_atr_uses_only_past_bars`); `cost_atr` uses bar t's spread | ✅ |
| Filling on bar t's close | Entry at the t+1 open | ✅ |
| Holiday leakage | Fixed calendar | ✅ |
| Survivorship | Not applicable to the FX majors | ✅ |
| Instrument selection | Universe fixed before any result | ✅ |
| Overfitting in selection | 12 sets, global choice, ≥ 100 trades, DSR, PBO | ✅ (but see §12, risk A) |
| Intrabar ambiguity | SL first; TP first as a sensitivity | ✅ |
| Fill feasibility (each fill inside the bar's real range) | **Not implemented** (audit item 4) | ❌ |
| Merge audit (BID/ASK/MID alignment) | Done by intersection (`data.py:44`), but no separate recorded check | ⚠️ |

---

## 8. Mean-reversion comparison

### How the behaviour was found

- At ~15:55 UTC, on a synthetic random walk (data with no mean reversion by construction), Kronos forecast a confident move back toward the 400-bar average.
- The vendor's own predictor did the same, so it's the model, not the project's code.
- **Unverified:** that script wasn't saved. The evidence is `kronos-install-speed.md:12` and the journal.

### New measurement (this investigation)

This uses no future prices: it compares each Forecast with past data only. It covers 149,235 Forecasts.

| Measure | Value |
|---|---|
| Kronos median direction = sign(mean of last 400 closes − current close) | **88.4%** |
| Same, among confident Forecasts (`p_up` ≥ 0.7 or ≤ 0.3; n = 135,449) | **91.6%** |
| Per symbol | EURUSD 89.2%, GBPUSD 88.0%, USDJPY 87.4% |
| Median absolute median-move at bar 24 | **4.06 ATR** (90th percentile 12.25, 99th 22.79) |
| Median spread of outcomes (q90 − q10) | 3.67 ATR |

**Interpretation** (⚠️ inference):
- Kronos mostly says "price will revert to its recent average", and by a large amount.
- ⚠️ A rough estimate, not measured: a typical realised absolute 24-hour move in FX is around 2.5–3.5 ATR. If so, Kronos's *median* (central) forecast is larger than a typical absolute move.
- That looks like overconfidence, possibly an artefact of normalising each window to its own mean. **This is not established.**
- The exam's calibration table will show whether the confidence is justified.

**Genuine signal or model tendency? Unknown.**
- Short-horizon mean reversion in FX can be real.
- The real question is whether Kronos adds anything beyond a one-line rule.
- It disagrees with that rule only ~11.6% of the time. Its added value can come only from those cases and from its SL/TP geometry.

### The baselines as implemented (`evaluate.py:240-260`)

- **Revert to the 400-bar mean:** `sign(mean(close[t-399..t]) − close[t])`, on the same MIDPOINT data and the same window Kronos sees.
- **Momentum / mean reversion:** the sign of the last 24-bar return, or its opposite.
- **Random direction:** seed 7, 1,000 repeats.
- **Intended design** (pre-registration): trade **exactly Kronos's entry bars**, with the **same risk and reward distances** as the matching Kronos trade, the same Time exit and the same costs. Only the direction differs.
- **As implemented:** ❌ not identical (§12, issue 1):
  - The geometry lookup `geom = {r.ts: (r.risk, r.reward) ...}` (line 241) is keyed by **timestamp only**.
  - So a symbol's baseline trades at any hour when **any** symbol had a Kronos trade.
  - It can take a risk distance expressed in another symbol's price units. For example, EURUSD's 0.002 applied to USDJPY near 110 is then clamped to 0.5 ATR, with a TP almost at the entry.
  - The baselines also skip the one-position-per-symbol rule (`evaluate.py:78-82`).
- **So "evaluated under identical conditions" is not true in the current code.**

**Which metrics decide whether Kronos adds value?**
- **None are mandatory.** The baselines are informational, and the verdict doesn't depend on them.
- The pre-registration does say "beats the baselines but ≤ 0 R" is a NO-GO.
- **It doesn't cover the reverse case**: Kronos gets a GO, but the revert-to-mean baseline does as well or better. Under the current rules that's still a GO for Kronos. This is a design gap (§14).

**If Kronos were removed and only simple mean reversion were used:** ⚠️ estimate.
- Because the directions agree 88% of the time, the trades would be largely the same trades in the same direction.
- The differences would be in the SL (10th percentile of the path lows) and the TP (the median close), which also come from Kronos.
- Only a correct baseline comparison can measure Kronos's net contribution. **That's the comparison the bug currently breaks.**

---

## 9. Remaining work (chronological)

| # | Stage | Inputs | Outputs | Command | Gate to proceed | Failure modes |
|---|---|---|---|---|---|---|
| A | Finish in-sample Forecasts (running) | Data + model | 70 files | `scripts/run_pre_oos.sh` (running) | All 70 files exist | Sleep or throttling, OOM, power loss. Resumable, because each symbol-year is its own file. |
| B | **Selection** | 2010–2019 Forecasts + data | `results/select.md`, `select_trades.parquet`, `selected_set.json`, PBO, DSR, feature tests | `evaluate.py --forecasts results/forecasts/small_n30 --stage select` | One set with ≥ 100 trades, otherwise NO-GO at selection | **`evaluate.py` has never run.** Bugs are possible; any fix must be technical only and disclosed. |
| C | **Exam Forecasts** | Data + the seal | `SYM_2025.parquet` and `SYM_2026.parquet` for 7 symbols | `run_forecasts.py --from 2025-07-01 --to "2026-11-26 15:00" --unseal fcbef95 --symbols EURUSD,GBPUSD,USDJPY,USDCHF,AUDUSD,USDCAD,NZDUSD --batch 12` | 14 files | `--symbols` **must** be given explicitly: the default lists 12 symbols, and the crosses' data isn't downloaded. ⚠️ Estimate: ~62k Forecasts ÷ 8.67/s ≈ 2 h. |
| D | **Verdict** | Exam Forecasts + the selected set | `results/oos.md`: verdict, secondary results, sensitivities, baselines, calibration, Monte Carlo, target check | `evaluate.py --stage oos --set P,M` | — | The baseline bug (issue 1). The 1,000 random repeats may take minutes. |
| E | Contamination check | 2020 → 2025-06 Forecasts (~13 GPU-hours) | `results/contamination.md` | `FROM=2020-01-01 TO=2025-07-01 scripts/run_pre_oos.sh`, then `evaluate --stage contamination --set P,M` | — | ❌ **The 2025 file collision** (issue 2): run after C, it silently skips 2025-H1. |
| F | Gold test | Only after a GO | A new pre-registration for gold | Requires downloading XAUUSD first (its files were deleted; the pull was stopped) | GO on the majors + a new pre-registration | Gold is not confirmed to be in Kronos's training data and may be out of distribution. |

**Checking the reported schedule:**
- **"Friday ≈ 08:20 Egypt: first profit numbers on 2010–2019"**
  - ⚠️ Consistent with the estimate (A finishing ≈ 08:10).
  - **Only if the agent is active then and runs B.** Nothing is scheduled automatically.
- **"≈ 10:30–11:00 Egypt: the verdict"**
  - ⚠️ B (minutes) + C (≈ 2 h) + D (minutes) ≈ 08:15 + 2:15 ≈ 10:30.
  - Plausible if `evaluate.py` needs no debugging. **Any bug delays it.**
- **Date:** Friday 2026-11-27.

**After the verdict** (`JEV_QUANT_MASTER_PLAN.md` §8, §9, §12, §13):
- **GO does not approve real money.** The sequence after it is:
  1. the gold test (its own pre-registration);
  2. Phase 2: Signal + Risk Gate + journal (ticket 08);
  3. Phase 3: the Jev decision engine (ticket 07), which must show added value out-of-sample;
  4. Phase 4: SIGNAL_ONLY, running live without orders;
  5. Phase 5: PAPER trading on the IBKR paper account, with reconciliation and restart safety;
  6. LIVE: the user's decision only. It needs explicit configuration, and the agent never enables it.
- **INCONCLUSIVE (n < 100):** collect forward data in SIGNAL_ONLY mode, and build nothing that trades.
- **NO-GO:** stop, or run fine-tuning as a separate, pre-registered experiment.

---

## 10. Friday's evaluation

1. **Selection (B):**
   - For each of the 12 sets, `run_symbol` walks all 7 symbols. Trades are pooled and the statistics computed.
   - The rule picks one set.
   - It also prints:
     - PBO over 10 yearly blocks;
     - DSR with 12 trials;
     - feature tests: a median split with a 5,000-permutation test, Holm over 6 features.
2. **Exam Forecasts (C):** the seal must pass.
3. **Verdict (D):**
   - the primary result and the verdict;
   - secondary results: long and short, per symbol with Holm, gross;
   - 4 sensitivities: TP first, 2 ticks of slippage, no financing, XM spreads;
   - 4 baselines;
   - calibration;
   - out-of-sample confirmation of any in-sample feature winner;
   - Monte Carlo drawdowns;
   - the target check.

---

## 11. GO / NO-GO criteria

**Mandatory** (`evaluate.py:213-214`; it matches `JEV_QUANT_MASTER_PLAN.md` §8 and the pre-registration):

| Verdict | Condition |
|---|---|
| **GO** | Pooled out-of-sample mean R > 0 **and** the lower bound of the 95% day-clustered bootstrap CI > 0 **and** n ≥ 100 trades |
| **INCONCLUSIVE** | n < 100 |
| **NO-GO** | Anything else, including "beats the baselines but ≤ 0 R" |

**Informational only** (no thresholds, never part of the verdict):
- win rate, PF, max drawdown in R;
- long and short separately;
- per symbol with Holm (it can never turn a pooled NO-GO into a GO);
- the gross result;
- the 4 sensitivities;
- the 4 baselines;
- calibration (hit rate, Brier);
- DSR and PBO;
- Monte Carlo drawdown percentiles;
- monthly returns at 1% risk: the median, the 5th percentile, and P(month ≥ 2%);
- the risk per trade needed for a 2% month.

**From the requested list:**

| Metric | Status |
|---|---|
| Expectancy | Implemented, as mean R |
| Number of trades | Implemented |
| Spread, slippage, commission | Implemented, in the fills and in R |
| Robustness across instruments | Per symbol, informational |
| Robustness across regimes | Only via the yearly PBO in-sample and the contamination window |
| Sharpe | Only per trade, inside the DSR |
| Net profit in money | **Not implemented**: everything is in R or % |
| Annualised return | **Not implemented** |
| Sortino ratio | **Not implemented** |
| Exposure | **Not implemented** |
| Separate average win / average loss | **Not implemented** |

**Does it measure genuine out-of-sample predictive value?**
- Yes, in the sense that:
  - the window follows the weights' upload date;
  - the rules are frozen;
  - it's run once;
  - calibration is measured on every Forecast.
- But the window is **only ~17 months**, roughly one market regime.
- A GO would be evidence of "an edge in this period, at these costs", **not a guarantee for the future**. That's why paper trading follows.

---

## 12. Technical and quantitative risks

The findings are prioritised by their impact on the validity of the experiment.

### ❌ Confirmed issues

**1. Baseline geometry keyed by timestamp only** (`scripts/evaluate.py:241`, used at `:79` and `:92-95`).
- `geom` holds all 7 symbols' trades keyed by `ts`. Consequences:
  - a symbol's baseline trades whenever *any* symbol traded;
  - it borrows another symbol's risk and reward distances, in different price units (JPY prices are ~100× the others);
  - the one-position-per-symbol rule isn't applied.
- **No effect on the primary verdict.** But it invalidates the key scientific comparison (Kronos versus revert-to-mean).
- Not fixed, as instructed. A fix restores the pre-registered design rather than changing it, but it must happen **before stage D** and be disclosed as a bug-fix deviation.

**2. The 2025 file-name collision** (`scripts/run_forecasts.py:80-82`).
- Contamination (to 2025-07-01) and the exam (from 2025-07-01) both write `small_n30/SYM_2025.parquet`. The second run skips silently, because the file exists.
- In the planned order, the contamination report loses 2025-H1.
- If the order were reversed, **the exam would silently lose 2025-H2**.
- The fix is a separate `--out` directory per window.

**3. `evaluate.py` is untested and has never run** on real data. It's the main source of surprises for Friday.

**4. Documentation versus code discrepancies.** The pre-registration document is the stated authority; where the code differs, the code is what will actually run.

| The pre-registration says | What actually exists |
|---|---|
| PBO "purged by 24 bars at each boundary" | `pbo_cscv` (`stats.py:76-94`) **doesn't purge**. |
| "Config in one versioned file (`config.toml`)" | It doesn't exist. Settings are hard-coded in `SamplerConfig`, `strategy.py:15-17` and `evaluate.py:30-36`. |
| "Model weight checksums" | Not recorded. |
| "Fixed seeds, checked by running a 1-month slice twice" | Not done in that form. The audits show determinism only indirectly. |
| XM spot-checks (flagged bars, and 20 random bars per symbol) | Not done. |
| Audit item 3 (a written feature and merge audit) | Not done. |
| Audit item 4 (every fill inside its bar's range, gap bars listed) | Not done. |
| The future-corruption test "automated as a regression test" | It exists only as a script. |
| "Risk per trade for a 2% *median* month" | The code uses the *mean* monthly R (`evaluate.py:296-298`). |
| "Monthly returns … in entry order" | The code groups by exit time (`:288`). |
| The exam ends at 2026-11-26 15:00 UTC | Enforced only by `run_forecasts --to`. `evaluate.py` uses 2100 as its end (`:36`). Trades near the end may exit on a bar that was still forming at download time (e.g. AUDUSD 18:00). The impact is small. |

**5. The lookahead audit doesn't cover the fills or `evaluate.py`.**

### ⚠️ Risks requiring investigation

**A. The thresholds probably don't bind.**
- 77% of Forecasts have `p_up` ≥ 0.9 or ≤ 0.1, and the median |move| is 4 ATR, far above `MOVE_MIN` (≤ 1 ATR).
- So the 12 sets may yield nearly identical trades, and the trade count will be set mostly by the one-position-per-symbol rule.
- That doesn't invalidate the verdict. But the grid was designed without knowing the scale of Kronos's output, and PBO and DSR over near-duplicate sets carry little information.
- The pre-registration's "≈ 25 trades a month" is probably far too low. ⚠️ That's an estimate; it wasn't computed.

**B. Kronos ≈ revert to the mean** (§8). Kronos's added value may be small, and the comparison that measures it is currently broken.

**C. The CI may be too narrow.**
- Trades last ~24 bars, so they straddle days, and all 7 symbols share USD exposure.
- Clustering by UTC entry day may understate correlation.
- Weekly clustering would be more cautious. It isn't pre-registered, so it could only be added as a disclosed sensitivity.

**D. The costs assume a USD 1M account.**
- With a smaller account, the USD 2 commission minimum binds.
- IDEALPRO odd lots (below USD 25k) cost ~1.5 bp more (ticket 06).
- **The user's real account size is unknown to me.**

**E. Slippage** of 1 tick (half a pip) may be optimistic around news. Mitigated by gap fills at the real open, and by real historical bid/ask spreads.

**F. Financing** is a flat 0.5 bp per night in both directions. Real swaps depend on rate differentials and can be positive. This is a simplification.

**G. Out-of-distribution inputs:** volume is zero, and the time features are in UTC. Both effects are unknown.

**H. A short exam window** (~17 months): roughly one regime, with no regime split inside the out-of-sample data.

### ✅ Correctly handled

- The code-enforced seal on the exam window.
- Entry at the t+1 open on the real ask/bid.
- SL first, gap fills at the real open, exits on the correct side.
- No future data in ATR or the cost estimate.
- `eval()` mode, per-Forecast seeds, and a sampler identical to the reference (as recorded).
- A leak-free calendar.
- SHA-256 checksums of the data.
- The truncated AUDUSD download, caught before it affected anything.
- The verdict rule, coded exactly as documented.

### Unknowns that can't currently be verified

- Whether the Hugging Face weights are the paper's checkpoints.
- Whether FX was trained with volume, and in which timezone.
- Whether the mean-reversion behaviour is a normalisation artefact or a learned prior.
- The user's real account size.
- Whether `evaluate.py` runs without errors.

---

## 13. File and code reference map

| Component | File | Key lines |
|---|---|---|
| Master plan | `JEV_QUANT_MASTER_PLAN.md` | §5 Signal, §8 Validation gate, §9 Modes, §12 Phases, §13 Acceptance |
| Pre-registration | `docs/research/kronos-edge-test.md` | Windows, Candidate, Exits, Verdict, SHA-256 table, commit `fcbef95` |
| Journal | `docs/journal/kronos-edge-test.md` | Has an uncommitted change |
| Install and speed | `docs/research/kronos-install-speed.md` | |
| Kronos training data | `docs/research/kronos-training-data.md` | Lines 7–13, 49, 61 |
| V1 failure | `docs/research/edge-revalidation.md` | TL;DR |
| Ticket / map | `.scratch/kronos-jev/issues/06-kronos-edge-test.md`; `.scratch/kronos-jev/map.md` | |
| Data download | `spikes/kronos/scripts/pull_ibkr.py` | Retry and truncation guard |
| Load and clean | `spikes/kronos/spike/data.py` | 15 (ticks), 18 (MAJORS), 19 (OOS_START), 30–61 |
| Sampler | `spikes/kronos/spike/kronos_paths.py` | 43–52 (SamplerConfig), 56–59 (revisions), 62–66 (`eval`), 69–88 (seeds, Gumbel), 179–267 (fast path) |
| Calendar | `spikes/kronos/spike/calendar.py` | 8–33 |
| Strategy and simulator | `spikes/kronos/spike/strategy.py` | 15–17 (costs and clamp), 56–67 (ATR), 70–80 (stats), 83–95 (cost, Candidate), 106–161 (`simulate`) |
| Statistics | `spikes/kronos/spike/stats.py` | 12–24, 50–55, 58–73, 76–94, 97–123 |
| Forecast runner | `spikes/kronos/scripts/run_forecasts.py` | 38–50 (seal), 79–104 |
| Pipeline | `spikes/kronos/scripts/run_pre_oos.sh` | 5–13 |
| Evaluation | `spikes/kronos/scripts/evaluate.py` | 30–37, 68–109, 182–201, 213–214, 240–260, 262–302 |
| Audit | `spikes/kronos/scripts/audit_lookahead.py`; `spikes/kronos/results/audit_lookahead.md` | |
| Tests | `spikes/kronos/tests/` | 24 tests |
| Logs | `spikes/kronos/results/run_is.log`; `spikes/kronos/data/pull.log` | |
| Forecasts | `spikes/kronos/results/forecasts/small_n30/` | gitignored |

**Git:**
- Branch `kronos-edge-test`.
- Commits `fcbef95` (the pre-registration) and `6a4bec9` (records the hash), on top of `773123f` (master).
- Working tree: `docs/journal/kronos-edge-test.md` modified, uncommitted.
- No secrets are in the repository. `.env` is gitignored, and none was read for this report.

---

## 14. Questions we should investigate together

1. **Fix the baseline bug (issue 1) before stage D, as a disclosed deviation?** My recommendation is yes: it restores the pre-registered design.
2. **Give the exam a separate `--out` directory (issue 2) before running it?** My recommendation is yes, disclosed.
3. **If Kronos gets a GO but revert-to-400-bar-mean does as well or better, is it still a GO *for Kronos*?** The current rules say yes. Scientifically, the thing worth building would then be the baseline, not Kronos. **This must be decided before any result is seen.**
4. **What is the real IBKR account size?** Below roughly USD 100k, the costs should be re-run as a disclosed sensitivity.
5. **Add weekly clustering of the CI as a disclosed sensitivity?**
6. **Accept the non-binding grid as it stands** (the rules are frozen), and record it as a lesson for the next experiment?
7. **Kronos's moves look larger than typical moves.** Is the de-normalisation suspect? A disclosed sanity check on realised in-sample moves could follow stage B.
8. **The pre-registered checks that weren't done** (the XM spot-checks, audit items 3 and 4): run them before the verdict, or formally record them as dropped?
9. **Who runs stages B, C and D on Friday morning?** They need an active session. Automating them would need a scheduled job, at your decision.
10. **The designer's (my) market knowledge up to June 2026:** is it worth an independent review of the frozen rules by a reviewer who hasn't seen any results?
