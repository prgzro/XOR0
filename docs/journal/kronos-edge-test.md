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
| 7. Forecasts 2010–2019, 7 majors | ⏳ EURUSD 9 of 10 years; 8.67/s steady | ETA Fri ~06:30 |
| 8. Choose the settings (in-sample) | ⬜ | Fri ~08:00 |
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

- Branch `kronos-edge-test`. This commits the pre-registration, docs, tickets, code, tests and lookahead audit results.
- Not committed: price data, Forecasts, the venv, the Kronos clone, `.env` (all gitignored).
- From this commit on, the rules are frozen. Any change goes under "Disclosed deviations".

---

## Research log (trial count for the deflated Sharpe)

Every variant run on real results goes here, including failed ones. Speed runs and audits don't count as trials.

| when | variant | window | n | mean R | note |
|---|---|---|---|---|---|
| — | — | — | — | — | no strategy result seen yet |
