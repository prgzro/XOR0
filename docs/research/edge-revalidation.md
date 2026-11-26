# Edge revalidation under V2's real rules (research)

Ticket: `.scratch/jev-quant/issues/14-edge-revalidation.md`. Run 2026-11-26, offline. MT4 was not run and no web sources were needed.
Follows `space-validation.md` (ticket 12). Uses the Origin rule from `v2-origin-auto-detect.md` ("Live pinning", ticket 13), the confirmed-Origin policy from `v2-repaint.md` (ticket 03), the deep XM history from `xm-history-depth.md` (ticket 15), and costs from `backtest-data-source.md` (ticket 11).

## TL;DR

- **No edge, at any level of the test.** This is a **no-go for "Jev on top of a mechanical SQ9 edge"**: there's no mechanical edge to filter.
- **The 45° levels aren't respected any more than control lines are.** Over **688,417** first touches on 12 symbols × H1/H4/D1 (6.8 / 7.7 / 17 years), real levels are respected 55.4% of the time. Lines shifted by half a step are respected 55.4%, and lines shifted by a random phase 55.3%. The edge is **−0.0 pp (95% CI −0.1 to +0.1)**. No single symbol/TF cell is significant after Holm correction (best raw p = 0.017, out of 72 tests).
- **The strategy loses money out-of-sample, and its levels do no better than fake ones.** The tolerances were chosen in-sample (IS, entries before 2023-07-01). Out-of-sample (OOS, 2023-07-01 to 2026-11-26) gave **119 trades, win rate 29.4%, mean −0.10 R (95% CI −0.35 to +0.17), PF 0.86, max DD 18.1 R**. Even with no costs at all it's −0.04 R. Every one of the 16 tolerance sets was negative in IS. The control strategy, which runs the same machine on a grid shifted ±22.5°, does no worse: −0.08 R over all periods against −0.13 R for the real grid. An anchored walk-forward over 2022–2026 gave −0.19 R (n = 147).
- **No symbol or TF stands out once multiple comparisons are corrected for.** No cell has an IS "winner" (IS n ≥ 10 and p < 0.05). Only 2 of 36 cells even reach 10 OOS trades. The positive-looking per-symbol numbers (GBPJPY +0.71 R, n = 9; USDCAD +0.38 R, n = 12) are noise at these sample sizes.
- **V2's Origin rule and this sequence barely fit together.** V2's Origin is the *older* of the two 270-bar extremes. By the time the Origin is confirmed it's a median **252 bars old**, and price is a median **489°** away from it. In **68%** of setups price is already past the 360° target. So the 90 → 45 → 90 → retest sequence has usually played out (or failed) before the Origin is even known:
  - If the sequence is replayed from the Origin bar, the strategy takes **1 trade in 6.8 years** on EURUSD H1.
  - If every stage has to happen after confirmation, it takes about **30 trades a year across all 36 symbol/TF series**. Of 9,754 setups, 88% die waiting for the 45° pullback.
- **A Jev filter has nothing to amplify.** No observable at entry separates winners from losers in-sample after Holm correction and then holds up out-of-sample. Trend, volatility, setup age and the distance metrics all fail. The nearest candidate is pullback depth: a deeper pullback close did better in IS by 0.54 R (raw p 0.04, Holm 0.46) and in OOS by 0.49 R (p 0.06). That's a weak hypothesis to log, not a filter. A filter can only remove trades from a stream whose gross mean is ≤ 0 and whose levels aren't special. With about 30 trades a year, it also couldn't be validated for years.

## Pre-registration

These were fixed in code (`study.py`, `analyze.py`) before the in-sample selection was run. The OOS stage was run once, after the choice was printed (`is.md`, then `oos.md`).

- **Universe:** EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, EURGBP, EURJPY, GBPJPY, EURCHF, GOLD × H1, H4, D1.
- **Data:** `XMGlobal-Demo 2` `.hst` files, copied to the scratchpad and read only from there.
  - H1 runs 2020-02 to 2026-11 (42,033 bars), H4 2019-02 to 2026-11 (12,069), D1 2009 to 2026-11 (4,585).
- **Split:** in-sample = entries before **2023-07-01**; out-of-sample = from 2023-07-01 to 2026-11-26. On H1 that's about 3.4 years each way.
- **Selection rule:** one global tolerance set for all symbols and TFs. It's the set with the highest pooled IS mean R at base costs among those with ≥ 100 IS trades. Nothing is tuned per symbol or per TF.
- **Free tolerances: a grid of 16 sets.** Each one is a reading of a stage in master plan §4:
  - `pb`: the pullback close must be ≤ 45° + pb. Values: 0.10 or 0.25 step.
  - `rt`: the retest is a wick ≤ 90° + rt, and the retest fails on a close < 90° − rt. Values: 0.10 or 0.25 step.
  - `mrt`: the maximum bars from breakout to retest confirmation. Values: 10 or 30.
  - `mst`: the maximum bars from the 90° touch to the pullback, and from the pullback to the breakout. Values: 50 or 150.
- **Fixed rules:**
  - **Breakout:** a close > 90° + 0.05 step.
  - **Initial move:** a wick ≥ 90°, within `mst` bars of the setup start.
  - **Entry:** the next bar's open after the retest-confirmation close (a close back beyond 90°).
  - **Exits:** SL at 0°, TP at 360°.
  - **Invalidation:** a **wick beyond 0°** (a 0° breach), the stage timeouts above, or a failed retest. A drop-out never invalidates a setup.
  - **One active setup per symbol/TF:** a setup runs until it is invalidated or its trade closes. Each Origin identity is used once.
- **Origin rule (confirmed-Origin policy, ticket 13):**
  - At each closed bar t, take bars t−269…t (seen from bar t+1, these are shifts 1…270).
  - Find the highest High and the lowest Low, with **ties going to the older bar**. The Origin is the older of the two.
  - A low gives a bullish Origin and a high a bearish one. Close[1] vs the Origin then always agrees with the Origin's kind.
  - A setup starts at the first bar where an unused identity is current and no setup is active.
  - The Origin and Space are **frozen** at that start.
  - **Sensitivity:** the same with shifts 1…269 (W = 269).
- **Space:** `10^round(log10(O / (4·ATR14²)))`, with Wilder ATR14 at the Origin bar. It's frozen per Origin.
- **Levels:** `level(θ) = (√(O·S) + d·θ/180)² / S`.
- **Costs:**
  - Bars are Bid. A long fills at Ask = Open + spread + slippage. Its SL fires on Bid ≤ SL and fills at SL − slippage (or at the open, on a gap). Its TP is a limit on Bid.
  - A short fills at Bid − slippage. Its SL fires on **Ask (= Bid + spread) ≥ SL** and fills at SL + slippage (or at Open + spread, on a gap). Its TP fires on Ask ≤ TP.
  - **Fixed spread, in points:** EURUSD 24, GBPUSD 28, USDJPY 31, USDCHF 32, AUDUSD 27, USDCAD 35, NZDUSD 35, EURGBP 28, EURJPY 37, GBPJPY 47, EURCHF 40, GOLD 77.
    - Each value is the larger of the MarketInfo snapshot (02:14 EET) and the median measured from `ticks.raw` (01:54–01:57), ×1.1 and rounded up. Both measurements were taken near the daily rollover, the widest time of day (`xm-history-depth.md`, `backtest-data-source.md` Q4). So the spread is already conservative for normal sessions, and the ×1.1 pads it further.
  - **Slippage:** 3 points on FX and 10 points on GOLD, on the entry fill and on SL fills.
  - **Commission:** 0 in the base case. A sensitivity case uses $7 per round-turn lot, converted to R per trade with the contract size, the risk distance and the quote-to-USD rate at entry (taken from the same-TF USDJPY, USDCHF, USDCAD and GBPUSD closes).
  - Swap is not modelled.
- **Intrabar ambiguity:** when the SL and TP fall in the same bar, the SL is assumed. History can't resolve this: M1 only covers the last ~10 weeks (ticket 15).
- **R:** profit divided by the risk distance (entry fill to SL). Trades still open at the end of the data are marked to market (none in OOS).
- **Statistics:**
  - Trade-level bootstrap with 5,000 resamples for the CIs. p = the bootstrap P(mean ≤ 0).
  - Holm and BH corrections over the testable cells (OOS n ≥ 10).
  - Max DD is the largest drop in the cumulative R curve, with trades taken in order of entry time.

### Disclosed deviations

1. **The setup-start semantics were changed after a smoke test, before any R result was used.**
   - The first design replayed each frozen Origin's stages from the Origin bar onward. That's legal, since all those bars are closed at confirmation.
   - A smoke test (EURUSD, one tolerance set) gave 1, 0 and 0 trades on H1, H4 and D1. The pattern had almost always completed or failed before the Origin was confirmed.
   - I then made "fresh start" the main variant: every stage must happen on bars after the confirmation bar t0. This is what an EA implementing §4.3 would do, since each transition needs a source candle at or after the setup's start.
   - The same smoke test showed one fresh-start number on the full EURUSD history: 12 H1 trades, +0.43 R. I didn't use it for any choice.
   - Both variants are reported below.
2. In the walk-forward only, the minimum count for re-selection is 30 trades. No tolerance set reaches 100 trades before 2023.

## 1. Level respect vs control lines

**Method.** This is ticket 12's method, with three fixes:
- It uses V2's real Origin rule under the confirmed policy, not stand-in Origins.
- It looks forward only, from the confirmation bar.
- It adds a second control and uses a cluster bootstrap.

**How a touch is scored.** For every confirmed Origin identity (Space frozen), take the first touch of each line within bars t0+1…t0+300.
- A line is **respected** if the wick reverses ≥ 0.4 step (18°) back to the approach side before any close ≥ 0.4 step through, within 100 bars.
- A touch-bar close through the line counts as a break. A bar with both a reversal and a close-through also counts as a break (conservative).
- Unresolved touches are dropped.

**Lines compared.**
- Real lines: 45°·k for k = 1…31.
- Control "half": the same lines shifted by 22.5°.
- Control "phase": the same lines shifted by a random φ ∈ U(5°, 40°), drawn once per Origin.

**CIs.** The bootstrap resamples clusters, a cluster being a (symbol, TF, month of t0), with 2,000 resamples. Clustering is needed because consecutive Origins overlap in time.

Pooled results (`resp.md`):

| slice | real touches | real | half-step ctl | random-phase ctl | real−half pp [95% CI] | real−phase pp [95% CI] |
|---|---|---|---|---|---|---|
| ALL, 45..1395° | 688,417 | 0.554 | 0.554 | 0.553 | −0.0 [−0.1, +0.1] | +0.0 [−0.1, +0.1] |
| ALL, 45..360° | 204,656 | 0.562 | 0.564 | 0.564 | −0.2 [−0.4, +0.0] | −0.1 [−0.4, +0.1] |
| H1 | 495,028 | 0.556 | 0.556 | 0.556 | −0.1 [−0.2, +0.1] | −0.0 [−0.1, +0.1] |
| H4 | 145,916 | 0.545 | 0.543 | 0.545 | +0.2 [−0.1, +0.4] | +0.0 [−0.2, +0.3] |
| D1 | 47,473 | 0.559 | 0.558 | 0.557 | +0.1 [−0.4, +0.6] | +0.2 [−0.2, +0.6] |
| W = 269, ALL | 690,394 | 0.553 | 0.553 | 0.553 | −0.0 [−0.1, +0.1] | −0.0 [−0.1, +0.1] |

- **The test is precise, and the effect is zero.** The pooled CI is ±0.1 pp, so even a 0.3 pp effect would have shown up. It doesn't. Restricting to the strategy's own range (45° to 360°), the real lines are, if anything, slightly *less* respected.
- **Per cell:** 36 cells × 2 controls = 72 tests. Real−control differences range from −1.1 to +1.6 pp. The smallest raw p is 0.017, and **every Holm-adjusted p is 1.00**. The full table is in `resp.md`.
- **Answer to Q1: no.** There is no statistically meaningful respect for 45° levels on any symbol or TF, on 7 to 17 years of data.

## 2. The mechanical strategy

### In-sample selection (`is.md`)

All 16 tolerance sets were negative in-sample, from −0.41 R to −0.16 R, on 67 to 135 trades. The rule picked **set 14: pb 0.25, rt 0.25, mrt 30, mst 50** (IS −0.158 R, n = 107).

### Headline (`oos.md`)

| slice | trades | win rate | mean R [95% CI] | PF | max DD R | p(mean≤0) |
|---|---|---|---|---|---|---|
| IS, base (spread + slip) | 107 | 0.271 | −0.158 [−0.420, +0.120] | 0.78 | 22.8 | 0.88 |
| IS, gross (no costs) | 107 | 0.271 | −0.122 [−0.393, +0.159] | 0.83 | 19.6 | 0.80 |
| **OOS, base** | **119** | **0.294** | **−0.100 [−0.345, +0.168]** | **0.86** | **18.1** | 0.77 |
| OOS, gross (no costs) | 119 | 0.294 | −0.038 [−0.301, +0.242] | 0.95 | 15.2 | 0.62 |
| OOS, 2× spread | 119 | 0.277 | −0.190 [−0.428, +0.067] | 0.74 | 26.0 | 0.93 |
| OOS, base + $7/lot commission | 119 | 0.294 | −0.117 [−0.370, +0.155] | 0.84 | 19.0 | 0.82 |

- **Costs are a small part of R.** Spread plus slippage cost 0.06 R per trade on average (OOS). Commission at $7 per lot would add 0.017 R (median). The 45° step is about 1 to 1.6 ATR14, so the risk is about 3 ATR and costs stay small. The loss is not a cost artefact: it's negative gross.
- **Outcomes:** OOS had 84 SL and 35 TP exits; IS had 78 SL and 29 TP. No trade was still open at the end of the data.
- **Breakeven:** the average winner is about **+2.1 R** (p10 to p90: 1.3 to 2.7 R), not +3 R, because entry is past 90° and the risk includes the spread. That puts breakeven at about a 32% win rate. The observed 27 to 29% sits a little below it, which is what a random walk with this geometry plus costs gives.

### By TF and direction (OOS; IS in brackets)

| slice | trades | win rate | mean R [95% CI] |
|---|---|---|---|
| H1 | 88 (67) | 0.307 | −0.035 [−0.341, +0.298]  (IS −0.124) |
| H4 | 25 (29) | 0.240 | −0.299 [−0.771, +0.243]  (IS −0.031) |
| D1 | 6 (11) | 0.333 | −0.219 [−1.003, +0.620]  (IS −0.700) |
| long | 62 (55) | 0.355 | +0.077 [−0.280, +0.456]  (IS −0.023) |
| short | 57 (52) | 0.228 | −0.292 [−0.632, +0.072]  (IS −0.300) |

- **Longs vs shorts is not significant.** Longs beat shorts in both periods, but the median-split test puts the gap at +0.28 R in IS (p 0.31) and +0.37 R in OOS (p 0.17). The bullish and bearish geometry is symmetric: both 0→90 vs 90→360 ratios are ≈ 3. My reading is that this is sample noise, possibly helped by USD weakness in 2025–26.

### Per symbol and TF

Full table: `oos.md`.

- **Trades are too sparse for per-cell inference.** Only **2 of 36 cells** (EURUSD H1 and EURGBP H1, 12 trades each) reach 10 OOS trades. Both are negative (−0.14 R and −0.38 R; Holm 1.00, BH 0.86).
- **No IS winner exists to carry forward.** No cell has IS n ≥ 10 with IS p < 0.05.
- **Per symbol, all TFs together (OOS):** the range is −1.01 R (GBPUSD, 0 wins out of 9) to +0.71 R (GBPJPY, n = 9, p 0.075). With 12 comparisons, nothing survives correction.
- **No "winning symbol/TF" can be named.**

### Robustness and controls (same tolerance set)

| variant | IS mean R (n) | OOS mean R (n) |
|---|---|---|
| W = 269 (shifts 1…269) | −0.179 (109) | −0.122 (118) |
| control grid +22.5° (all levels and SL/TP shifted) | −0.263 (108) | +0.039 (117) |
| control grid −22.5° | +0.300 (81) | −0.361 (91) |
| **both controls, all periods** | −0.081 (397) | |
| **real grid, all periods** | −0.127 (226) | |
| reconstruct-from-Origin variant | +2.11 (1) | +0.69 (2) |

- **The SQ9 grid is no better than a grid moved half a step.** The controls flip sign between IS and OOS, which is how noise of this size behaves.
- **Reconstruct-from-Origin barely trades.** Across all 16 sets × 36 series × 17 years it gives 264 trades in total. With set 14, 33,699 setups were already dead by pullback timeout at confirmation, and 11,277 had a stale entry signal before confirmation.

### Anchored walk-forward (re-select each 1 January on all earlier entries, n ≥ 30)

| year | set chosen | trades | mean R [95% CI] |
|---|---|---|---|
| 2022 | 12 | 25 | −0.654 [−1.006, −0.241] |
| 2023 | 3 | 27 | −0.290 [−0.763, +0.244] |
| 2024 | 14 | 32 | −0.164 [−0.624, +0.303] |
| 2025 | 14 | 35 | +0.045 [−0.422, +0.563] |
| 2026 | 6 | 28 | +0.006 [−0.539, +0.603] |
| **pooled** | | **147** | **−0.189 [−0.410, +0.041]**, PF 0.75, max DD 30.4 R |

### Why so few trades: the funnel (set 14, main variant)

- **9,754 setups started, and 226 became trades** (2.3%).
- **End reasons:**
  - pullback timeout: 8,616 (88%)
  - 0° breach: 795
  - failed retest: 69
  - retest timeout: 16
  - end of data: 26
- **Price is already far from the Origin at confirmation.** p10/25/50/75/90 = **191° / 312° / 489° / 743° / 1,089°** from the Origin. Price is already past 90° in 98% of setups and past 360° in 68%.
- **The Origin is old when confirmed:** p10/50/90 = 119 / 252 / 269 bars.
- **Why:** V2's Origin is the *older* 270-bar extreme. A low only becomes the Origin once the high that came after it is the newest extreme, so by construction price has already rallied the whole 270-bar range away from it. With a k = 1 Space, the 45° step is about 1 to 1.6 ATR, and a 270-bar range spans many steps.
- **The consequence:** the 0° → 90° → 45° → 90° sequence in the master plan lives in the first few dozen bars after a swing. V2's rule only identifies that swing hundreds of bars later.
- **This is a design finding regardless of edge.** As specified, the strategy and V2's auto-Origin barely meet: about **30 trades a year across 36 symbol/TF series**, about 23 of them on H1. D1 gave 17 trades in 17 years across 12 symbols.

## 3. Could a Jev filter help?

**Test.** For 14 observables taken at the signal bar, split IS trades at the IS median and compare mean R above vs below the median. The p-value comes from a two-sided bootstrap, with Holm correction over the 14 features. The same IS threshold is then applied to the OOS trades (`oos.md`).

**Observables:**
- trend: 50-bar change in ATR, signed with the trade; distance from SMA200 in ATR
- volatility: ATR14 / mean ATR14 over 100 bars; ATR at entry / ATR at the Origin
- setup age: bars since the Origin; bars since confirmation; Origin age at confirmation
- distance metrics: risk in ATR; cost as a fraction of R; bars from breakout to entry; θ of the pullback close; maximum excursion before entry; θ at confirmation
- direction

| feature | IS hi−lo R | IS p (Holm) | OOS hi−lo R | OOS p |
|---|---|---|---|---|
| trend50 | +0.69 | 0.013 (0.16) | **−0.37** | 0.17 |
| bo_bars | +0.85 | 0.006 (0.08) | +0.16 | 0.65 |
| pb_th (pullback close θ) | −0.54 | 0.038 (0.46) | −0.49 | 0.057 |
| sma200 | +0.47 | 0.08 (0.87) | +0.11 | 0.67 |
| exc | +0.05 | 0.80 (1.00) | +0.60 | 0.027 |
| direction (long − short) | +0.28 | 0.31 (1.00) | +0.37 | 0.17 |
| all others | \|Δ\| ≤ 0.35 | ≥ 0.19 (1.00) | | ≥ 0.08 |

- **No feature passes "significant in IS after correction, then confirmed OOS."**
- The two strongest IS features don't hold. trend50 reverses sign in OOS. bo_bars (how long the retest took) vanishes in OOS.
- **pb_th is the only feature that keeps its sign and size across both periods.** Deeper pullback closes do better. It's a hypothesis to keep, not a finding: Holm 0.46 in IS, p 0.057 in OOS, and about 55 trades per half.
- H1 entry hour (4-hour buckets) shows nothing stable either. 16–19 h server time is the worst bucket in both halves (−0.28 / −0.58 R), but with n = 14 and 18.
- **Plausibility.** A filter like Jev can only lift the mean by dropping losers that are predictable *at entry*. Here the gross mean is ≤ 0, the levels carry no information beyond a shifted grid, and no observable predicts the outcome. A filter would also cut a stream of about 30 trades a year, which would take many years to validate.

## Verdict

- **There is no mechanical SQ9 edge to put Jev on top of, on any of the 12 symbols or 3 timeframes tested.** The 45° levels don't act as support or resistance, and the breakout-retest strategy is a random-walk payoff minus costs.
- **Ticket 12's null result came back on 7 to 17 years of data with V2's real Origin rule.** Its −0.10 R OOS is consistent with ticket 12's +0.04 R; both are noise around zero or slightly below.
- **Go/no-go input: no-go for an edge-driven EA built on this setup.**
- **If the project continues:**
  - It should be framed as a tooling or discretionary-assist product, such as reproducing V2's levels and journaling, with no claim of expectancy.
  - Or it needs a different, pre-registered strategy hypothesis.
  - Any such hypothesis must first reconcile the stage timing with V2's 270-bar older-extreme Origin. As specified, the two barely co-occur.

## Caveats

- **Power is limited.** With 119 OOS trades and an SD of about 1.4 R, the CI half-width is about 0.25 R. An edge of +0.1 to +0.2 R can't be excluded by the strategy test alone. But the level-respect test is very tight (±0.1 pp) and finds nothing, and no positive edge has shown up in tickets 12 or 14 on any slice that survives correction.
- **Spreads are fixed and taken from rollover snapshots**, not session profiles. Using 2× spread costs another 0.09 R per trade. Swap isn't modelled; it would matter for D1 and multi-day H4 holds.
- **SL-first on ambiguous bars is conservative.** M1 only covers the last ~10 weeks, so this can't be checked historically.
- **The state machine is one reasonable reading of master plan §4.** The other choices:
  - **The fresh-start semantics** are a disclosed post-smoke-test choice. The replay alternative is reported and barely trades.
  - **Wick-breach invalidation** (instead of close-breach) and **one active setup per symbol/TF.**
  - Concurrent setups per Origin, or a different initial-move rule, would change the trade count. They're unlikely to change the sign, since the levels themselves carry no information.
- **Overlap inflates precision.** Consecutive Origins overlap in time. Cluster-by-month only partly corrects for this, especially on D1, where a 300-bar window spans about 14 months. The respect CIs are probably a little too narrow. That only strengthens the null.
- **Space:** only the adopted rule (B10, k = 1) was tested. Ticket 12 showed that Space choice changes trade size, not edge.

## Scripts and outputs (session scratchpad, ephemeral)

`/tmp/claude-1000/-home-prgzro-Projects-XOR0/205c3630-a6e9-485f-b79e-e22a252b80f3/scratchpad/edge-revalidation/`

- `common.py`: HST reader, Wilder ATR, the confirmed-Origin rule (vectorised; `argmax` keeps the oldest bar on ties), Space, levels and cost tables.
- `study.py`: the state machine and fill simulator. It runs 16 tolerance sets × 36 series × 5 variants (main, W = 269, ±22.5° control grids, reconstruct). Writes `trades.pkl`.
- `respect.py` and `resp_an.py`: the level-respect test and its analysis. Output: `resp.md`.
- `analyze.py`: `is` stage (`is.md`), then `oos` stage (`oos.md`, `chosen.pkl`).
- `data/`: read-only copies of the 36 `.hst` files.
- Run with `python3 <script>` (numpy and scipy come from the user site, so not `-I`). The full rerun takes about 30 s on 15 processes.
