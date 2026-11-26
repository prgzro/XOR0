# Space validation on history (research)

Ticket: `.scratch/jev-quant/issues/12-space-validation-on-history.md`. Gathered 2026-11-26.
Follows `docs/research/space-selection-formula.md` (ticket 02). Note: that doc's fit used EURUSD H1 chart07 = 100000. The current chart value is **10000** (see the "Correction" section of `docs/research/v2-live-observations.md`). This study settles the question on price data instead of on the user's charts.

Scripts (session scratchpad, not in the repo): `/tmp/claude-1000/-home-prgzro-Projects-XOR0/205c3630-a6e9-485f-b79e-e22a252b80f3/scratchpad/space-validation/`
- `hst.py`: HST v401 reader and Wilder ATR14.
- `study.py`: Origin rules, Space candidates, level-respect test, strategy state machine. Writes `results.pkl`.
- `analyze.py`: tables and bootstrap CIs. Saved outputs: `sel.md` (selection), `oos.md` (out-of-sample + D1), `eu.md` (EURUSD H1), `step.md`.

Data: `~/.wine/drive_c/Program Files (x86)/XM Global MT4/history/XMGlobal-Demo/*.hst`, read only. MT4 was not run.

## Answer: the adopted rule

**No Space rule is clearly better. Adopt the safest default, ticket 02's B10 with k = 1:**

```
Space = 10 ^ round( log10( Origin / (4 · ATR14²) ) )     ATR14 = Wilder ATR(14) at the Origin bar, signal TF
```

It is computed once per Origin and frozen. It stays a power of ten, so V2's panel can show the same levels.

Why this rule, given that nothing wins:

1. **The pre-registered selection rule fell through to the default.** The rule was: adopt the candidate with the best in-sample + validation expectancy only if (a) the 95% CI of its difference from k=1-snapped excludes 0, and (b) it is best under both Origin rules. No candidate met (a). Every difference CI spans roughly ±0.2 to ±0.35 R. No candidate met (b) either: the best was k=0.5-snap under one Origin rule and k=2-cont under the other.
2. **Level respect is not distinguishable from the null.** For every candidate, real 45° levels are respected within about **±1 percentage point** of control levels shifted by half a step. In-sample the edge is +0.3 pp for k=1-snap (CI −0.2 to +0.7); out-of-sample it is +0.2 pp (CI −0.7 to +1.0). With 12 candidates tested, the few CIs that exclude 0 are what chance alone produces, and none of them hold up across segments.
3. **k=1-snap keeps the trade size in a bounded ATR band.** Its 45° step stays between 0.59 and 1.69 ATR14 (p5 to p95). It reproduces most of the user's charts (ticket 02), and the panel can set it. The two digits rules are the only candidates with a clearly negative in-sample result (digits −0.13 R, CI −0.27 to −0.00), and their step size in ATR ranges far wider (0.9 to 8.7 ATR).

**Out-of-sample result of the adopted rule (reported once):** 138 trades, win rate 34.8%, expectancy **+0.04 R** (95% CI **−0.20 to +0.30**), PF 1.06, max DD 17.1 R. By Origin rule: fractal10 +0.06 R (n=81) and donch100 +0.01 R (n=57). **This is zero within noise. It is not evidence of profitability.**

## EURUSD H1: 10000 vs 100000

- **Neither Space is measurably better.** All EURUSD H1 data is used (2,260 bars, Oct 2025 to Mar 2026), both Origin rules pooled:

| Space | real touches | respect edge vs null (pp) | trades | win rate | expectancy R (95% CI) |
|---|---|---|---|---|---|
| 10000 (user's chart) | 351 | −1.7 [−8.5, +5.4] | 31 | 0.48 | +0.50 [−0.07, +1.04] |
| 100000 | 1254 | +0.5 [−2.0, +2.9] | 24 | 0.46 | +0.52 [−0.11, +1.18] |
| formula k=1 (picks 1e5 on 193/221 Origins, 1e6 on 28) | 1400 | −1.3 [−4.0, +1.5] | 20 | 0.50 | +0.56 [−0.16, +1.26] |
| formula k=2 (1e5 on 177, 1e4 on 44) | 1070 | 0.0 [−2.8, +2.8] | 30 | 0.47 | +0.65 [+0.08, +1.29] |

- **This 4.5-month window was favourable to everything.** The trade samples are tiny and overlapping, so no conclusion follows from these numbers. The k=2 CI that just excludes 0 is one of many comparisons.
- **A larger k explains the user's 10000, but it needs k ≈ 4 to 5, outside the tested grid.** At EURUSD H1 swing Origins, Space 10000 puts the 45° step at a median **4.6 ATR14** (IQR 3.9 to 5.2), so it corresponds to k ≈ 4.6. Space 100000 gives a median 1.46 ATR14. The tested k = 2 only reaches 10000 on 20% of Origins.
- **The digits rule explains it more simply.** The tutorial's "digits per timeframe" rule gives exactly 10000 on EURUSD H1. Neither k nor the digits rule matches the user's other charts, though: 10000 on EURUSD H4 and 100000 on GBPUSD H1. The best reading is that the user keeps a per-symbol "gear" by eye.
- **Verdict:** keep the formula (k = 1, which gives 100000 here). If the user prefers 10000 on EURUSD H1, a per-symbol override costs nothing measurable.

## Method

Everything below was fixed in `study.py` before any result was seen. Nothing was tuned afterwards.

- **Universe:**
  - FX: AUDUSD, EURCHF, EURGBP, EURUSD, GBPUSD, USDCHF, USDJPY, USDNOK, USDSEK, plus GOLD.
  - Selection and out-of-sample use H1 + H4. D1 is a separate robustness check (USDSEK has no D1 file). Futures and crypto are excluded.
  - Bar counts: about 2,050 to 2,600 per file, except EURUSD/GBPUSD/USDCHF/USDJPY H4 at about 14,300 bars (2009 to 2026). H1 files cover only Oct 2025 to Mar 2026.
- **Chronological split, per series:** the first 60% of bars is in-sample (IS), the next 20% validation, the last 20% out-of-sample (OOS).
  - A setup belongs to the segment of its Origin confirmation bar (respect test) or of its entry bar (trades).
  - The selection used IS + validation only. The OOS block was run once, after the choice was fixed.
- **Origin rules (non-repainting; closed bars only):**
  - `fractal10`: a bar whose low (high) is the strict extreme of ±10 bars. It is confirmed 10 bars later, and the setup starts at the next bar and lasts up to 300 bars. Setups can overlap.
  - `donch100`: at each closed bar, the more recent of the 100-bar lowest low and highest high, once it is at least 3 bars old. A low gives a bullish Origin, a high a bearish one. A new extreme replaces the Origin and ends the old setup.
- **Space candidates (12):**
  - `k{0.5, 0.75, 1, 1.5, 2}` in two forms each: `_snap` = `10^round(log10(O/(4k²·ATR14²)))`, and `_cont` = the unrounded value.
  - `digits`: `10^(D(tf) − max(1, integer digits of O))`, with H1 D = 5 and H4/D1 D = 4. This is the SQ9-36 / tutorial rule.
  - `digits_x10`: digits × 10, the user's FX offset.
  - For EURUSD H1 only: fixed 1e3, 1e4, 1e5, 1e6.
- **Levels:** V2 formula `level(θ) = (√(O·S) + d·θ/180)²/S`.
  - All tests work in θ, where `θ(p) = d·180·(√(p·S) − √(O·S))`, so one 45° step = 45 θ-units whatever the Space.
  - Origins with `√(O·S) ≤ 2.5` are skipped: the bearish 360° level does not exist there.
- **(a) Level respect:**
  - The grid is θ = 22.5·m for m = 1 to 32 (up to 720°). Even m are real 45° multiples; odd m are the **null**, the same grid shifted by half a step.
  - For each grid line, take the first bar whose range touches it inside the setup window. The approach side comes from the previous close.
  - **Respect** = price reverses ≥ 0.4 step (18°) back on the approach side, by wick, before any close ≥ 0.4 step through the line, within 100 bars.
  - A touch bar that closes through counts as a break. A later bar with both a reversal and a close-through also counts as a break (conservative).
  - Unresolved touches are dropped.
  - **Edge** = real respect rate − control respect rate. Its 95% CI comes from a bootstrap of Origins (300 resamples).
- **(b) Strategy** (`SQ9_90_BREAKOUT_RETEST`, master plan §4), with tolerances in steps:
  - Pullback tolerance 0.15 step (6.75°), breakout buffer 0.10 step (4.5°), retest zone 0.15 step (6.75°).
  - **Initial move:** a wick reaches 45° + tolerance.
  - **Pullback confirmed:** a close within ±tolerance of 45°.
  - **Breakout:** a close beyond 90° + buffer.
  - **Retest:** a wick returns within 90° + zone.
  - **Retest confirmed:** a close back beyond 90°. Entry is at the next bar's open.
  - **Invalidation:** any close beyond 0°; a breakout close before the pullback; a close more than one zone back inside 90° during the retest; 200 bars from start to entry; 30 bars from breakout to entry.
  - **Exits:** SL at 0°, TP at 360°. If both are touched in one bar, the SL is assumed. A gap through a level fills at the open. A trade still open at the end of data is marked to market.
  - **Spread:** the HST spread field is **0 in every file**, so fixed spreads were assumed and charged on entry and exit through bid/ask. Majors 1.8 to 2.5 pips, crosses 2.5 pips, USDNOK/USDSEK 40 pips, GOLD 0.35. No commission, swap or slippage.
  - **Reported:** trade count, win rate (R > 0), expectancy in R with a 95% CI from a trade-level bootstrap (1,000 resamples), profit factor, max drawdown in R (trades in time order, all series pooled).
- **(c) Step size:** the 45° step divided by ATR14 at the Origin bar.

## Results

### Selection: in-sample + validation, H1 + H4, both Origin rules

| Candidate | respect edge pp [95% CI] | trades | win rate | expectancy R [95% CI] | PF | max DD R | Δ vs k1-snap [95% CI] |
|---|---|---|---|---|---|---|---|
| k0.5_snap | +0.3 [+0.0, +0.6] | 132 | 0.348 | +0.017 [−0.226, +0.266] | 1.03 | 23.4 | +0.018 [−0.264, +0.297] |
| k0.5_cont | +0.1 [−0.2, +0.3] | 118 | 0.356 | −0.060 [−0.301, +0.181] | 0.91 | 20.6 | −0.059 [−0.357, +0.245] |
| k0.75_snap | +0.2 [−0.1, +0.5] | 336 | 0.310 | −0.003 [−0.158, +0.167] | 1.00 | 48.5 | −0.003 [−0.235, +0.247] |
| k0.75_cont | +0.6 [+0.3, +1.0] | 248 | 0.367 | +0.123 [−0.060, +0.300] | 1.19 | 15.5 | +0.123 [−0.116, +0.367] |
| **k1.0_snap** | +0.3 [−0.2, +0.7] | 519 | 0.291 | −0.001 [−0.174, +0.168] | 1.00 | 55.5 | (reference) |
| k1.0_cont | −0.1 [−0.6, +0.3] | 459 | 0.329 | +0.094 [−0.066, +0.266] | 1.14 | 29.5 | +0.094 [−0.135, +0.327] |
| k1.5_snap | +0.4 [−0.2, +0.9] | 776 | 0.277 | −0.031 [−0.172, +0.108] | 0.96 | 83.8 | −0.031 [−0.241, +0.199] |
| k1.5_cont | +0.2 [−0.5, +0.7] | 798 | 0.294 | −0.002 [−0.110, +0.116] | 1.00 | 62.1 | −0.001 [−0.190, +0.199] |
| k2.0_snap | +0.8 [+0.2, +1.4] | 922 | 0.297 | +0.016 [−0.108, +0.155] | 1.02 | 106.5 | +0.017 [−0.182, +0.225] |
| k2.0_cont | −0.1 [−0.8, +0.5] | 1111 | 0.297 | +0.022 [−0.088, +0.133] | 1.03 | 101.0 | +0.022 [−0.179, +0.227] |
| digits | +0.9 [−0.1, +1.6] | 785 | 0.293 | −0.134 [−0.270, −0.003] | 0.84 | 280.8 | −0.134 [−0.357, +0.081] |
| digits_x10 | +0.1 [−0.5, +0.5] | 644 | 0.252 | −0.128 [−0.269, +0.022] | 0.83 | 94.9 | −0.127 [−0.368, +0.092] |

Per-Origin-rule tables and the IS-only / validation-only splits are in `sel.md`.

- **The candidate ranking flips between Origin rules and between segments.** Under fractal10 the best is k0.5_snap (+0.11 R); under donch100 it is k2.0_cont (+0.17 R).
- **k0.75_cont's validation result does not hold.** It is +0.42 R on validation [+0.02, +0.85] but +0.04 R in IS, and +0.01 R OOS.

### Out-of-sample, H1 + H4 (all candidates shown for context; only k1.0_snap was chosen)

| Candidate | respect edge pp [95% CI] | trades | win rate | expectancy R [95% CI] | PF | max DD R |
|---|---|---|---|---|---|---|
| **k1.0_snap (adopted)** | +0.2 [−0.7, +1.0] | **138** | **0.348** | **+0.039 [−0.203, +0.295]** | **1.06** | **17.1** |
| k0.5_snap | +0.0 [−0.5, +0.6] | 35 | 0.400 | +0.109 [−0.347, +0.579] | 1.19 | 7.6 |
| k0.75_cont | −0.1 [−0.9, +0.7] | 71 | 0.366 | +0.014 [−0.303, +0.354] | 1.02 | 9.4 |
| k1.0_cont | +0.3 [−0.6, +1.0] | 123 | 0.317 | −0.147 [−0.384, +0.110] | 0.78 | 24.5 |
| k2.0_snap | +0.6 [−0.7, +1.8] | 247 | 0.409 | +0.091 [−0.362, +0.519] | 1.12 | 61.7 |
| k2.0_cont | +1.4 [−0.0, +2.8] | 260 | 0.388 | +0.147 [−0.033, +0.338] | 1.25 | 24.9 |
| digits | −0.3 [−2.1, +1.4] | 177 | 0.429 | +0.344 [+0.034, +0.680] | 1.63 | 28.1 |
| digits_x10 | +0.6 [−0.4, +1.5] | 192 | 0.354 | −0.019 [−0.568, +0.555] | 0.98 | 60.2 |

(Full table in `oos.md`.)

- **The digits rule looks good OOS (+0.34 R), but it was the worst rule in IS + validation (−0.13 R).** A full sign flip like that is the signature of noise or regime luck across 12 candidates. Picking it after seeing OOS would be exactly the overfitting this test exists to prevent.

### D1 robustness (all segments, no selection)

| Candidate | respect edge pp [95% CI] | trades | expectancy R [95% CI] |
|---|---|---|---|
| k1.0_snap | +0.5 [−0.2, +1.5] | 100 | −0.038 [−0.329, +0.216] |
| k1.0_cont | +1.2 [+0.3, +2.2] | 102 | +0.301 [−0.015, +0.627] |
| k2.0_snap | 0.0 [−1.2, +1.3] | 263 | +0.002 [−0.179, +0.190] |
| digits | 0.0 [−1.3, +1.1] | 217 | +0.050 [−0.149, +0.249] |

D1 shows the same picture: respect edges within about ±1.7 pp, with some negative CIs (k1.5_cont, k2.0_cont), and every expectancy CI spans 0.

### 45° step in ATR14 units (H1 + H4, all Origins)

| Candidate | p5 | p25 | median | p75 | p95 |
|---|---|---|---|---|---|
| k0.5_snap | 0.31 | 0.39 | 0.49 | 0.63 | 0.82 |
| k0.75_snap | 0.44 | 0.54 | 0.71 | 1.02 | 1.27 |
| **k1.0_snap** | **0.59** | **0.75** | **1.08** | **1.40** | **1.69** |
| k1.5_snap | 0.92 | 1.18 | 1.51 | 1.93 | 2.48 |
| k2.0_snap | 1.18 | 1.45 | 1.84 | 2.50 | 3.36 |
| `_cont` (any k) | k | k | k | k | k |
| digits | 0.93 | 3.08 | 4.42 | 5.94 | 8.73 |
| digits_x10 | 0.30 | 0.97 | 1.40 | 1.88 | 2.76 |

## Interpretation

- **The SQ9 45° grid shows no detectable support/resistance on this data, at any Space.** Raw respect rates rise with k (0.52 at k=0.5 to 0.60 at k=2), but the half-step-shifted control lines rise identically. Bigger steps mean a bigger reversal target relative to bar noise; the effect is not the levels.
- **The strategy's results are what a random walk with costs predicts.** Space only sets the trade size in ATR; the 0→90 vs 90→360 geometry fixes the payoff at about 3:1 (ticket 02 §1). The observed win rates of 25 to 43% and expectancies near 0 R fit that.
- **The Space choice is therefore an ergonomic and cost decision, not an edge decision.**
  - Smaller steps (low k, or ×10 Space) put spread at a larger share of R and give fewer completed sequences.
  - Larger steps give more trades but slower, larger ones with deeper drawdowns in R.
  - k = 1 snapped is the middle.

## Caveats

- **The spread is assumed, not measured.** The HST spread field is 0, and there is no commission, swap or slippage. The result is cost-approximate.
- **Overlapping samples make the CIs too narrow.** fractal10 setups overlap, and so do the two Origin rules on the same bars. The true CIs are wider than shown, which only strengthens "nothing is distinguishable".
- **The H1 history is short.** It covers only about 4.5 months (Oct 2025 to Mar 2026). Long history exists only for 4 majors on H4, and those dominate the H4 counts.
- **The Origin rules are stand-ins.** V2's auto-detect rule is still being researched. The conclusions held under both rules tested, and a different rule could still change the strategy numbers.
- **The state machine is one reasonable reading of master plan §4.** Its timeouts (200 / 30 bars) and invalidation choices were fixed in advance and not tuned. The respect test uses one reversal threshold (0.4 step) and one horizon (100 bars).
- **This is a mechanical test, not a profitability claim.** The Jev filter, risk engine, spread filter and position sizing are not modelled. Nothing here supports trading the strategy live.
