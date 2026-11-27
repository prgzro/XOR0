# Journal: the Kronos Edge test

A running, dated record of the journey from "use Kronos to trade" to a verdict. Each entry records what was done, why, what went wrong and how it was fixed. It's written as the work happens and never rewritten afterwards. Times are UTC (Egypt is UTC+2).

- **Goal (user):** 2–6% a month on the IBKR paper account.
- **Question this test answers:** do Kronos Forecasts, turned into trades by a fixed rule, earn positive R after costs on data Kronos never saw?
- **Rules:** `docs/research/kronos-edge-test.md` (the pre-registration).
- **Map:** `.scratch/kronos-jev/map.md`.
- **Code:** `spikes/kronos/`.

## Status board

| step | state | when |
|---|---|---|
| 1. Decide the rules (grilling) | ✅ done | 2026-11-26 |
| 2. Install Kronos and measure speed | ✅ done: Kronos-small, N = 30 | 2026-11-26 |
| 3. Build the simulator, statistics and audits | ✅ done: 24 tests pass | 2026-11-26 |
| 4. Lookahead audit | ✅ 3 of 3 PASS | 2026-11-26 |
| 5. Download IBKR history (majors) | ✅ 21 of 21 files, checksums recorded | Thu 18:20 |
| 6. Commit the pre-registration | ✅ branch `kronos-edge-test` | Thu ~18:25 |
| 7. Forecasts 2010–2019, 7 majors | ✅ 70 of 70 files, integrity checked | Fri 12:13 |
| 8. Choose the settings (in-sample) | ✅ run 2: 0.55 / 0.25 selected; every set −0.13 R in-sample | Fri 12:33 |
| 9. Unseal and run the exam (2025-07 → now) | ⬜ | **Fri ~10:00: verdict** |
| 10. Contamination check (2020 → 2025-06) | ⬜ | Fri ~18:00 |
| 11. Gold test (only if the majors pass) | ⬜ | later |

---

## 2026-11-26 (Thursday)

### ~14:00 Where we started

- The v1 idea (SQ9 levels on MT4) had already failed its edge test: −0.10 R per trade out-of-sample, no better than random lines.
- v2 replaces it with Kronos forecasts, the Jev approval and the Risk Gate on IBKR.
- The map's bottleneck was the speed ticket ("Kronos install and speed on this machine"), which blocks the Edge test, which decides go/no-go for everything else.

### ~14:15 Grilling: 23 decisions on how to test honestly

The user answered "yes" to all 23 recommendations. The ones that matter most:

- **Data:** IBKR's own MIDPOINT bars into Kronos and BID/ASK bars for fills. The XM data is a cross-check only.
- **Windows:**
  - choose the settings on 2010–2019, which is **before Kronos's FX training data starts (2020)**;
  - report 2020 → 2025-06 as a contamination check;
  - the exam is 2025-07 → now, **sealed and run once**.
- **Fixed rules:**
  - 12 threshold sets and one global pick;
  - SL/TP from the forecast paths;
  - Time exit after 24 bars;
  - SL first when one bar hits both;
  - gaps fill at the open;
  - real costs (spread from bid/ask, 1 tick of slippage, commission, overnight financing).
- **The verdict rule was tightened.** GO needs mean R > 0, a CI lower bound > 0, and ≥ 100 trades. "Beats the baselines but loses money" is a no-go.
- **Statistics from the quant skills:**
  - cluster bootstrap by day;
  - Holm correction;
  - deflated Sharpe;
  - PBO (CSCV);
  - Monte Carlo drawdowns;
  - an authenticity audit;
  - a research log.
- **Your 2–6% monthly goal** is reported as a target check and **never used for tuning**. At a fixed risk, monthly return ≈ risk × trades a month × mean R. Tuning toward a return number on data you've already seen is how v1 fooled itself.

Glossary: added **Horizon**, **Time exit** and **Edge test**.

### 14:45 Disk space

The disk was 99% full (6.3 GB free), and PyTorch with CUDA needs about 5 GB. The user freed space, leaving 50 GB.

### 14:56 Kronos installed

- `spikes/kronos/`, its own uv venv, torch 2.8.0+cu128. The GTX 1650 (compute 7.5) works with CUDA.
- The first download timed out at uv's 30 s limit, and the retry with `UV_HTTP_TIMEOUT=600` worked.
- Kronos source at commit `67b630e6`. It's cloned, never modified.

### ~15:00 Reading the Kronos code: three problems found

1. **It averages the sample paths** (`kronos.py:467`). The test needs every path to compute `p_up` and the quantiles.
2. **It never calls `model.eval()`.** The small model has **25% dropout**, which stays switched on while forecasting.
3. **Its random draws depend on the batch** (`torch.multinomial` on the global RNG). The same Forecast changes depending on what it's batched with, which breaks the truncation audit.

**Fix:** our own sampler (`spike/kronos_paths.py`). It returns all paths, runs in eval mode, and uses **Gumbel-max sampling with one seeded generator per (symbol, bar)**. That's mathematically the same distribution, but each Forecast is reproducible on its own.

A fourth trap, which would have been a lookahead leak:
- Kronos needs the **timestamps of the future bars**, and taking them from the real data would leak holidays and gaps.
- **Fix:** `spike/calendar.py` generates them from a fixed New York-time rule. It has IBKR's 17:15 session-open bar, and gold's 18:00 open.

### 15:15 IBKR history download started

- Read-only paper Gateway on 127.0.0.1:4002, 1-year requests, ≥ 11 s apart (IBKR's limit is 60 per 10 minutes).
- A smoke test on gold worked.
- The full pull runs from 2009-09, so there are 400 bars of lookback before 2010.

### 15:18–15:23 Simulator and statistics, test-first

- `spike/strategy.py`:
  - ATR;
  - the Candidate rule;
  - the trade simulator: entry at the next open on ask/bid + 1 tick, SL clamped between 0.5 and 3 ATR, SL before TP in the same bar, gaps filled at the open, Time exit, commission, financing.
- `spike/stats.py`: cluster bootstrap, Holm, PF, max DD, deflated Sharpe, PBO by CSCV, Monte Carlo (simple and block), monthly returns.
- **A useful simplification:** commission and financing are dimensionless in R (notional ÷ risk = entry ÷ risk distance), so no currency conversion is needed. The USD 2 commission minimum can never apply at USD 10k of risk.
- **24 tests, all passing.**

### 15:41 EURUSD history complete

107,206 H1 bars, 2009-09 → 2026-11.

### ~15:45 First speed test: far too slow

- Kronos-small with 30 paths took **11 s per Forecast**. The full test would have taken **about 160 days**.
- 12 Forecasts at once ran out of the GPU's 4 GB.
- **Cause:** the vendor loop has no KV cache. At each of the 24 steps it re-runs all ~424 tokens, and it repeats the same 400-bar context for each of the 30 paths.

### 15:53 The fix: a 68× faster sampler with identical output

- **KV cache:** each new step computes only the new token.
- **Shared prefix:** the 400-bar context is computed once per Forecast and shared by all 30 paths. That also solved the memory problem.
- A detail found in the code: the s2 cross-attention applies RoPE at position 0, which is the identity, so its keys can be cached directly.
- **Check:** compared with the reference loop, **100% of paths were bit-identical (max diff 0), at 68× the speed.**

### ~15:55 Discovery: Kronos reverts to the mean, even on pure noise

- On a synthetic random walk, which by construction has no mean reversion, Kronos forecast a confident move back toward the 400-bar average: `p_up` of 1.00 or 0.00, sometimes overshooting the mean.
- The vendor predictor does the same, so it's the model, not our code. This confirms ticket 01's warning.
- **Response:** a fourth baseline was added before any result, "revert to the 400-bar mean". If Kronos can't beat that one-line rule, it isn't adding anything.

### ~16:00 Model choice: Kronos-small, N = 30

Measured with N = 30:

| model | Forecasts/s | full test |
|---|--:|--:|
| mini | 12.6 | — |
| small | 8.6 | ≈1.7 days |
| base | 3.6 | ≈4.0 days |

fp16 was slower on this card (0.9/s) and changed the paths, so it was rejected. The pre-registered rule (largest model within ≈3 days) **picks small**. The weight revisions are pinned in code. Write-up: `docs/research/kronos-install-speed.md`.

### 16:12 Lookahead audit 1: PASS

- EURUSD 2015-03: the same Forecasts with the future data **cut off**, and with it **replaced by garbage**.
- 241 Forecasts, max difference 0, and all 12 grid sets' decisions identical.
- The cleaning rules flagged 2 real EURUSD spikes and kept them: the 2013-09-18 FOMC "no taper" decision and the 2013-11-07 ECB rate cut.

### ~16:15 Calendar rule checked against reality

The generated future bar times match IBKR's real next bar **100%** of the time, and the full 24-bar sequence **98.9%**. The misses are holidays (Easter, Christmas, New Year), which is accepted, since using them would mean leaking the future.

### ~16:15 Forecasting started, then a slowdown

- The first long run (2010 → 2025-06) had finished **no year in 35 minutes**, when a year should take about 12.
- **Cause:** a lookahead audit was running on the CPU at the same time, using all 16 cores. The GPU job needs the CPU for its sampling noise.
- **Fix:** both stopped, the audits moved to the GPU, and the job restarted on its own.

### ~16:18 Lookahead audits 2 and 3: PASS

GBPUSD 2012-06 and EURUSD 2018-09. With the future cut off or corrupted: identical Forecasts and identical decisions. **All 3 audits pass.**

### ~16:18 Order changed: verdict first

The in-sample period now runs for every symbol first, then the exam, then the contamination check, which doesn't affect the verdict. This brings the answer about 13 hours earlier.

### ~16:20 Universe narrowed to the 7 majors (user)

- **Now in:** EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD.
- **Crosses:** out.
- **Gold:** next, as its own pre-registered test, only if the majors pass. It uses the frozen rules and settings.

This was decided before any result was seen, and recorded in the pre-registration, the ticket and the map. Consequences:
- faster, with the verdict about 6 hours sooner;
- fewer trades: ~25 a month, so a 2% month needs about +0.08 R per trade or more;
- a higher risk of the "Inconclusive" verdict (< 100 trades).

### 16:26 Resources

| resource | use |
|---|---|
| GPU | 99%, 3.5 of 4 GB, 62 °C, 49 W |
| CPU | ~3.7 of 16 cores, package 78 °C (limit 100) |
| RAM | 1.4 GB |
| disk | ~7.3 GB |

All within safe limits for the laptop. Advice given: keep it plugged in, vents clear, no games or heavy CPU work during the run.

### 18:07 Progress check

- **Download:** 6 of 7 majors complete; NZDUSD has MIDPOINT and BID done, ASK is downloading (about 3 minutes left).
- **Forecasts:** EURUSD 2010–2018 done, 2019 running. Every year took 715–720 s at a steady **8.67 Forecasts/s**, matching the speed test exactly. About 6,200 Forecasts per year.
- **Forecast:** the remaining 6 majors × 10 years × 12 min ≈ 12 h, so the in-sample Forecasts should finish **Fri ~06:30 UTC**.
- **GPU:** 99%, 3.5 GB, 62 °C, unchanged and safe.

### 18:10 Caught: AUDUSD midpoint history silently cut short

- **The check:** before freezing the data, bar counts and start dates for all 21 files. Every file starts at 2009-09 except **AUDUSD MIDPOINT, which starts at 2018-11-26** (49,745 bars instead of ~107,000).
- **Cause:** one IBKR request timed out. ib_async returns an empty list on a timeout, and the pull script read "empty" as "no more history", so it stopped and wrote a short file without any error.
- **Impact if missed:** AUDUSD would have had no in-sample Forecasts for 2010–2018. That would have quietly shrunk the selection sample and changed which settings get picked.
- **Fix:**
  - an empty reply is retried 3 times, 60 s apart;
  - the script **refuses to write** any history that starts more than 7 days after the requested start;
  - AUDUSD MIDPOINT was downloaded again: 107,209 bars, from 2008-11 (trimmed to 2009-09), the same count as BID and ASK.
- **Cost:** none. AUDUSD's Forecasts hadn't started (they're queued after GBPUSD, USDJPY and USDCHF).
- The full pull for the crosses and gold was stopped. It isn't needed for the majors test and can be resumed later (the script resumes on its own).
- **Lesson** (data-cleaning skill): check coverage, not just validity. Every bar in the short file was valid. The problem was the bars that were missing.

### 18:20 Data frozen

- SHA-256 of all 21 files recorded in the pre-registration.
- **Out-of-sample end fixed at 2026-11-26 15:00 UTC (exclusive)**, the earliest end across the 21 files. Each file's last bar was still forming at pull time, so every Forecast bar is complete.

### ~18:25 Pre-registration committed

- Commit **`fcbef95`** on branch `kronos-edge-test`. This commits the pre-registration, docs, tickets, code, tests and lookahead audit results.
- Not committed: price data, Forecasts, the venv, the Kronos clone, `.env` (all gitignored).
- From this commit on, the rules are frozen. Any change goes under "Disclosed deviations".

### 21:00 Health check of the Forecasts so far (no trade results looked at)

The user asked whether the results look good. Trade results are computed only once, on the full in-sample period, so this checks only that the Forecast files are sound:

- 23 files (EURUSD and GBPUSD complete, USDJPY 2010–2012): **143,028 Forecasts, 0 missing values, 0 duplicate bars**, ATR > 0 everywhere.
- The path quantiles are ordered (q10 ≤ median ≤ q90) in 100% of rows. The long SL is below the price in 99.8% of rows, and the short SL above it in 99.9%. The rest are degenerate and get clamped or skipped by the rules.
- **`p_up` is strongly polarised**: the 25th percentile is 0.03, the median 0.87 and the 75th percentile 1.00. Most Forecasts have nearly all 30 paths on one side, which fits the reversion-to-the-mean behaviour found earlier. Whether that confidence is *right* is exactly what the in-sample evaluation and the "revert to 400-bar mean" baseline will show.

### 23:20 Laptop safety watch started (user request)

- **Readings at the start:** CPU package 85 °C (hottest core; the limit is 100 °C), GPU 61 °C, fans at ~4,000 RPM, plugged in, 48 GB of disk free.
- **The watch:** every 60 s it logs the CPU and GPU temperatures, power and disk to `spikes/kronos/results/safety_watch.log`.
- **It pauses the Forecast process (SIGSTOP)** if any of these holds for 3 readings in a row:
  - CPU ≥ 95 °C;
  - GPU ≥ 87 °C;
  - the charger is unplugged;
  - less than 5 GB of disk is free.
- A pause loses no work. The job resumes with `kill -CONT <pid>`.
- The watch ends on its own when the in-sample run finishes.

### Fri 2026-11-27 00:00–02:14: overnight checks

- The run held steady at 8.66–8.68 Forecasts/s. By 02:14, 50 of 70 symbol-years were done: EURUSD, GBPUSD, USDJPY, USDCHF and AUDUSD complete. USDCAD started at 02:11.
- The AUDUSD re-download works: 2010 has 6,240 Forecasts.
- **Safety watch:** 174 readings, 0 pauses. The CPU peaked at 90 °C (the limit is 95 °C), the GPU at 65 °C (the limit is 87 °C). The laptop stayed plugged in, with 48 GB of disk free.

### ~02:10: two bugs fixed before the exam (user approved: "fix the two Bugs")

A read-only review of the code found two bugs. Neither touches the primary verdict, but both would have damaged the exam's report. They're recorded as disclosed deviations D1 and D2 in `docs/research/kronos-edge-test.md`.

1. **The baselines mixed up symbols** (`evaluate.py`): their risk and reward distances were looked up by time only.
   - Fixed by keying them by symbol, then time.
   - Checked on 2019 EURUSD and USDJPY: the baseline mirrors 563/564 and 612/613 of Kronos's own entry bars, in the right price units.
2. **The 2025 file-name clash** (`run_forecasts.py`): the contamination and sealed runs both write `SYM_2025.parquet`, and the second one would silently skip it.
   - Fixed: an existing file from another window is now an error.
   - The sealed run gets its own folder, `small_n30_oos`.

- The check printed counts and distances only, not R, so it isn't a trial.
- The in-sample run wasn't interrupted.

### ~02:30: a stricter GO rule (user: "go with your recommendation")

- **Decision:** a GO now also needs Kronos to beat the "revert to the 400-bar mean" baseline on the same trades. The test is paired R differences, mean > 0 and CI lower bound > 0. Otherwise the verdict is "NO-GO (not better than revert-to-mean)".
- **Why:** Kronos agrees with that one-line rule 88% of the time. A slow AI model that only repeats a one-line rule isn't worth running.
- Recorded as deviation D3. It's coded in `evaluate.py`, but that file hasn't been run yet. It gets a smoke test on in-sample data once the Forecasts finish, before the seal is broken.

### 05:13–10:45: the safety watch paused the run (charger unplugged)

- At 05:13 the charger was unplugged. After 3 readings on battery, the watch paused the forecast process at 05:15 (SIGSTOP) and exited, as designed.
- Progress at the pause: 65 of 70 symbol-years; NZDUSD 2010–2014 done, 2015 in progress. No work was lost, because a paused process keeps its state.
- At 10:45 the charger was back and the laptop had cooled (CPU 29 °C, GPU 31 °C). The watch was restarted first, then the job resumed (`kill -CONT`). It came back at 100% GPU.
- The new ETA for the in-sample Forecasts was about 11:45 UTC.

### 11:06: slower after the resume (the GPU is power-capped)

- NZDUSD 2015 had about 6 minutes of work left at the pause, but 20 minutes after the resume it still hadn't finished.
- **Cause:** since the charger event, the laptop firmware caps the GPU at **20 W** (it asks for 50 W). `nvidia-smi` shows "SW Power Cap: Active", P5, and about 19 W drawn.
  - The CPU is fine: performance governor, average about 2.3 GHz, no RAPL cap below the default.
- **Effect:** the speed only, not the results. The Forecasts are seeded per Forecast, so the numbers are identical at any speed.
- **Action:** none on the system. The user was told and asked to re-seat the charger.

### 11:10: the real cause, a clean stop and a reboot

- **The real cause:** while it was on battery, the laptop **suspended** (system sleep) and woke at 10:44 UTC. The NVIDIA driver logged "Failed to handle Power Source change event", so the GPU stayed in battery mode: a 20 W cap, P5, and memory at 810 MHz.
- NZDUSD 2015 finished at **1.31 Forecasts/s**, against the normal 8.68. Its row count is the normal 6,209, so the slowdown affected the speed only.
- The user chose to reboot to reset the driver. The run was stopped cleanly first, with SIGTERM, between years. No file was half-written.
- **State:** 66 of 70 symbol-years are saved; NZDUSD 2016–2019 are left (about 50 minutes at full speed).
- Durable copies were made, because the scratchpad in `/tmp` may not survive the reboot:
  - the safety watch is now at `spikes/kronos/scripts/safety_watch.sh`;
  - the code review is now at `docs/journal/kronos-edge-test-review-2026-11-26.md`.
- **Lesson:** turn off automatic sleep for the whole test, not only on AC power.

### 11:17–11:18: after the reboot, checks and restart

- **GPU back to normal:** `nvidia-smi -q -d POWER` shows a current and requested limit of **50 W**, with SW Power Cap not active. (The short `--query-gpu=power.limit` form prints `[N/A]` on this driver, so the full query is the one to trust.) The charger is online (`ADP1 = 1`), with 55 GB of disk free. At idle the CPU was 44 °C and the GPU 45 °C.
- **Sleep blocked for the run:** the job runs under `systemd-inhibit --what=sleep:idle:handle-lid-switch --mode=block`. This applies the 11:10 lesson without changing any system setting, and the block ends when the job ends.
- **Start order:** the job started first, at 11:18:00, and the safety watch 8 s later. The reason: the watch exits at once if it finds no job running.
- **Running:** `FROM=2010-01-01 TO=2020-01-01 SYMBOLS=NZDUSD ./scripts/run_pre_oos.sh >> results/run_is.log`, which skips the 66 existing files. NZDUSD 2016–2019 are left, with an ETA of about 12:06 UTC.

### 11:19–11:30: the smoke test overheated the CPU, so the watch paused the run

- At 11:19 I started a code-path smoke test of `evaluate.py` (with `nice`) alongside the Forecasts. The CPU went from 69 °C to **97 °C** within a minute. After 3 readings ≥ 95 °C, the watch paused the job at 11:21 (SIGSTOP) and exited, as designed. The Forecasts alone peaked at 90 °C overnight.
- The smoke test was stopped. The CPU cooled to 44 °C. At 11:29:46 the watch was restarted first, then the job resumed with `kill -CONT 12511`: P0, 50.7 W, 99% GPU, CPU 79 °C. No work was lost, and the new ETA is about 12:15 UTC.
- **Lesson:** run nothing CPU-heavy alongside the Forecasts on this laptop; even `nice` doesn't limit heat.

### 11:19–11:35: smoke test of `evaluate.py` (partial), no results looked at

- **How:** a harness in the scratchpad imports `evaluate.py`, points every stage's window at **2019 only** (EURUSD and USDJPY), and writes to the scratchpad. It doesn't touch `results/`. It prints the section structure with **every number masked**, so this is a code check, not a trial. No repo file was changed.
- **`select`: ran.** The grid, selected set, PBO, deflated Sharpe and feature-test sections are all present. PBO is `nan`, which is expected with 1 yearly block; the real run has 10.
- **`contamination`: ran.** It shows the primary result, secondary, all 4 sensitivities, all 3 baselines (D1, keyed by symbol), the D3 paired test ("paired on 1175 of 1177 trades") and the 1,000-repeat random baseline.
- **`oos`: not reached.** The run was stopped for heat. The calibration, Monte Carlo, target and verdict code is still untested, and it gets re-run once the Forecasts finish.
- **Bug found (the feature tests, not the verdict):** in 57% of trades all 30 paths agree, so `p_edge` = 0.5 = the median = the max. `x > median` is then empty, the difference is `nan`, and `abs(perm) >= nan` is always False, so the code prints **p = 0.000, Holm p = 0.000**. That's a false "significant feature". It isn't fixed yet; it's waiting for the user's decision (possible D4).
- **A count-only observation, with no R looked at:** the trade counts barely change with P_MIN (1265 / 1257 / 1235 / 1212 at MOVE_MIN 0.25), because Kronos's 30 paths are often unanimous.

### ~11:40: D4, the feature-test ties fix (user approved: "Tie-aware split, as D4")

- **Fix** in `evaluate.py`: split at `x > median`, falling back to `x ≥ median` if one side is empty; if a side is still empty, the feature is "not testable (ties)", p = 1.
- 3 new unit tests in `tests/test_evaluate.py`; the suite now has 27 tests and all pass.
- Recorded as D4 in `docs/research/kronos-edge-test.md`. It only affects the exploratory feature tests, and it was fixed before the selection ran and before the seal was broken.

### ~11:39: NZDUSD 2016 done (67 of 70)

- 6,209 Forecasts in 1,223 s. That's 5.08/s on the wall clock, but the time includes the 8.5-minute thermal pause (≈ 523 s), so the real speed is about 8.8/s, normal for full power. The row count matches the other NZDUSD years.
- Years left: 2017–2019, about 36 min, so the ETA is about 12:16 UTC.

### ~11:51: NZDUSD 2017 done (68 of 70)

- 6,194 Forecasts in 699 s (8.86/s), at full speed. Years left: 2018–2019, with an ETA of about 12:15 UTC.

### ~12:03: NZDUSD 2018 done (69 of 70)

- 6,208 Forecasts in 701 s (8.85/s). Only 2019 is left, with an ETA of about 12:15 UTC.

### ~12:08: an integrity check of the 69 saved in-sample files (no R looked at)

- **Checked per file:** timestamps inside the file's year, sorted, no duplicates, and every one present in the MIDPOINT bars. No NaNs. `p_up` in [0, 1], ATR > 0, q10 ≤ median ≤ q90. `last_close` equals the bar close at `ts` (alignment, no lookahead). Coverage against the year's bars.
- **Result: clean.**
  - 428,492 Forecasts, with 100% coverage of the bars in every file.
  - Every `last_close` matches its bar's close.
  - No NaNs, duplicates or out-of-year timestamps.
- **One flag, not an error:** `sl_long ≥ last_close` (or the mirror for shorts) in 0.15% of Forecasts, all with p_up ≥ 0.967. This follows from the definition: the 10th percentile of path lows can sit above the close when almost every path rises. The simulator clips the SL to 0.5–3 ATR on the correct side of the actual fill (`spike/strategy.py:116`, `:123`), so no trade is affected.
- **Context:** the share of unanimous Forecasts (all 30 paths on one side) is 47–69% per symbol-year, which matches the smoke-test observation.
- NZDUSD 2019 is still running; it gets the same check when it lands.

### 12:13: in-sample Forecasts complete, 70 of 70 files

- NZDUSD 2019: 6,208 Forecasts in 709 s (8.76/s). `run_is.log` ends with "forecasts 2010-01-01 -> 2020-01-01 done". The job exited cleanly, the watch ended itself, and the sleep block was released.
- **Safety, 11:30–12:13:** 0 pauses. The CPU peaked at 94 °C at 12:02, 1 °C under the limit; the GPU peaked at 65 °C. The laptop stayed on the charger, with 55 GB free.
- **Integrity check of all 70 files:** clean. 434,700 Forecasts, 100% coverage of the existing bars in every file, every `last_close` equal to its bar's close, and no NaNs, duplicates or out-of-year timestamps.
- **A data-source fact, disclosed (not a run error):** NZDUSD 2010 has 5,841 Forecasts against 6,240 for the other majors.
  - The cause is IBKR's own NZDUSD history: until about October 2010 it lacks about 2 hours a day between 18:00 and 22:00 UTC, the thin late-US/early-NZ session.
  - That's 30–66 hours a month, 399 net hours in 2010.
  - The other differences at 21–22 UTC are the daily break moving with NZ vs US daylight saving, and they cancel out (2011: 185 missing, 185 extra).
  - **Effect:** fewer NZDUSD candidate bars in 2010, and Kronos context windows that span those short gaps. The data is fixed and checksummed by the pre-registration, so nothing is changed.

### 12:15–12:22: smoke test of `evaluate.py` finished, PASS

- The same harness (2019 only, EURUSD and USDJPY, scratchpad output, numbers masked) re-ran `select` with the D4 fix and ran `oos` for the first time. It took 7.5 minutes, with the CPU peaking at 77 °C and nothing else running.
- **`select`:** every section present. `p_edge` now gets a real split instead of the false p = 0.000. PBO is still `nan`, as expected with 1 yearly block.
- **`oos`:** every section present.
  - the verdict line;
  - primary, secondary and sensitivities;
  - the baselines with the D3 paired test, and the random baseline;
  - calibration (12,416 Forecasts = 2 × 6,208, and 10 deciles);
  - the feature tests;
  - the target check and the Monte Carlo drawdowns.
  - The only "nan" match was the word "financing".
- **Disclosed:** one line can't be masked because it prints text, not a number: "Mean R ≤ 0: no risk level reaches the target". So the 2019 EURUSD+USDJPY slice at set 0.60/0.5 had mean R ≤ 0, in-sample, 2 of 7 symbols and 1 of 10 years. It isn't a trial and can't steer anything, because the selection is the fixed pre-registered rule (highest mean R among sets with ≥ 100 trades) and the set used is one of the 12 grid sets already counted.
- The code is ready for the real stages; no further changes.

### 12:22–12:40: the in-sample selection ran, and its result is invalid (bad ticks in the IBKR BID/ASK data)

- `evaluate.py --stage select` ran in 2.5 minutes, exit 0. It picked **P_MIN 0.7, MOVE_MIN 0.5**: n = 42,226, win rate 0.370, **mean +0.917 R [−0.150, +3.069]**, PF 2.41, max DD 4,805 R, PBO 0.694, DSR 0.917.
- **That isn't plausible.** A 37% win rate with a mean of +0.9 R, a max DD of 4,805 R, a per-trade SR of 0.004 and a std of 216 R point to outliers.
- **Cause:** one AUDUSD trade on 2012-02-23 comes out at **+44,411 R**. The IBKR **BID open of the 22:15 UTC bar is 79.95**, against a true price of ≈ 1.0717. The long's TP "gap-filled" at that open.
  - Also: an EURUSD long on 2014-01-06 lost −22 R when its SL "gap-filled" at a **BID of 1.3200** (true ≈ 1.3634; the ASK open in the same bar is 1.4240).
  - The simulator applied the pre-registered fill rules correctly. The data is wrong.
- **What R was seen (in-sample only):** the grid table above, plus per-symbol means for the selected set. AUDUSD shows +7.1 R because of that trade; the other six show **−0.10 to −0.17 R**. The median trade is −1.03 R. 84 trades have |R| > 10.
- **How widespread, from the price data alone** (no Forecasts, no R; the sealed window's *price* bars were counted, not forecast):
  - **2,161 bars** have a BID/ASK value > 1 ATR outside the mid bar's range, 280 of them > 3 ATR outside; 77 bars are crossed (BID > ASK).
  - About 75% of the > 1 ATR cases sit on the **22:15 UTC reopen bar** after IBKR's daily break.
  - Per symbol (> 1 ATR, 2010–2019 / 2025-07 →): EURUSD 57/12, GBPUSD 59/68, USDJPY 57/36, USDCHF 165/219, AUDUSD 46/33, USDCAD 51/97, NZDUSD 241/147.
  - Some are probably real rollover spread blowouts, which are a real cost. Others are impossible prints.
- **Why the audit missed it:** the pre-registered intrabar check confirms that fills fall inside the bar's bid/ask range, and a bad tick *defines* that range. The integrity check of 12:13 covered the Forecast files, not the BID/ASK bars.
- **Saved as evidence:** `results/select_v1_badticks.md`, `select_v1_badticks_trades.parquet`, `selected_set_v1_badticks.json`.
- **Stopped here.** A data-cleaning rule would be a new deviation (D5), so it's the user's decision. Nothing is unsealed.

### ~12:50: D5, cleaning the bad BID/ASK ticks (user approved: "Clean > 3 ATR, as D5")

- `clean_quotes` in `spike/data.py`: any BID/ASK value > 3 ATR outside the mid bar's range, or a crossed bar, means the bar's BID/ASK is replaced by mid ∓ the median half-spread of the previous 400 bars. MIDPOINT and the Forecasts are unchanged.
- **On the real data:** 384 bars replaced (36–86 per symbol). No crossed bars are left, and the largest remaining deviation is 2.99 ATR. The AUDUSD 79.95 bar now reads BID 1.0717 / ASK 1.0718.
- 3 new tests in `tests/test_data.py`; the suite now has 30 tests and all pass. Recorded as D5 in `docs/research/kronos-edge-test.md`.
- **Side findings, disclosed and not changed:**
  - The MIDPOINT bars have spikes too (60–130 per symbol, mostly at 22:15). They're part of the Kronos input, and cleaning them would mean re-running the Forecasts.
  - IBKR's median close spread is often 0, so the base costs may be low. The XM-spread sensitivity covers this.
- **Next:** re-run the selection as run 2.

### 12:30–12:33: the in-sample selection, run 2 (D5 data): every set loses about −0.13 R

- `evaluate.py --stage select` exited 0 in 2.6 minutes. Output: `results/select.md`, `select_trades.parquet`, `selected_set.json`.
- **All 12 sets are negative:** mean −0.126 to −0.135 R per trade, each with a 95% CI entirely below 0 (e.g. [−0.145, −0.107]), PF 0.79–0.80, n = 38,572–45,666.
- **Selected by the pre-registered rule:** **P_MIN 0.55, MOVE_MIN 0.25** (n = 45,666, win rate 0.408, mean −0.126 R [−0.145, −0.107]).
  - PBO 0.000: the sets are nearly identical, so the ranking is stable.
  - Deflated Sharpe: SR −0.083, DSR 0.000.
- **Consistent everywhere:** every symbol is negative (−0.097 USDCAD to −0.159 USDCHF), and every year 2010–2019 is negative (−0.073 in 2011 to −0.159 in 2012).
- **Clean:** the largest trade is +21.7 R and the worst −10.7 R, with no |R| > 25. The median trade is −1.02 R, which is a full stop-loss plus costs.
- **Feature tests** (in-sample, selected set, Holm over 6): significant are `p_edge` −0.053 (more confident = worse), `sl_atr` +0.087 and `dispersion_atr` +0.039. Not significant: `move_abs`, `atr_pctile`, `hour`. These are exploratory; only in-sample winners get checked out-of-sample.
- **What the rules say next:** a negative in-sample best doesn't stop the test. The only selection-stage no-go is "no set with ≥ 100 trades". The selected set goes to the sealed exam unchanged.
- **Waiting for the user:** whether to commit D1–D5 before unsealing.

---

## Research log (trial count for the deflated Sharpe)

Every variant run on real results goes here, including failed ones. Speed runs and audits don't count as trials.

| when | variant | window | n | mean R | note |
|---|---|---|---|---|---|
| Fri 12:25 | 12-set grid, run 1 (raw IBKR BID/ASK) | in-sample 2010–2019 | 38,632–45,727 per set | +0.42 to +0.92 (invalid: one +44,411 R bad-tick trade) | selected 0.7/0.5; invalid, see journal 12:22–12:40 |
| Fri 12:33 | 12-set grid, run 2 (D5: BID/ASK bad ticks cleaned) | in-sample 2010–2019 | 38,572–45,666 per set | −0.126 to −0.135, all CIs < 0 | selected 0.55/0.25; the same 12 variants re-run on corrected data |
