# Space selection formula (research)

Ticket: `.scratch/jev-quant/issues/02-space-selection-formula.md`. Gathered 2026-11-26.
Scripts (session scratchpad, not in the repo): `hst.py` (HST v401 reader, Wilder ATR), `rules.py` (candidate rules), `user2.py` (user-choice test), `volm.py` (volatility-measure test), `cross.py` + `tab.py` (17-symbol test).

**Adopting a formula is the user's decision.** This doc gathers the evidence and makes one recommendation.

## TL;DR

Recommended rule **B10** ("ATR-matched, snapped to a power of ten"):

```
Space = 10 ^ round( log10( Origin / (4 · k² · ATR14²) ) )      k = 1
```

- `ATR14` is Wilder ATR(14) on the **signal timeframe**, read at the **Origin bar**.
- `round` means round to nearest: `floor(x + 0.5)`.
- Space is computed **once per Origin** and frozen for the life of the setup.
- MQL4: `MathPow(10, MathFloor(MathLog10(origin / (4*k*k*atr*atr)) + 0.5))`.
- Meaning: pick the power of ten that makes one 45° step (`≈ 0.5·√(Origin/Space)`) closest to `k × ATR14`. Equivalently, `√(Origin·Space) ≈ Origin / (2·k·ATR14)`.

How it performs:

- **Against the user's charts:** it reproduces **6 of 7** Space choices exactly. The miss is GOLD D1, an Angle-144 chart: B10 gives 0.1, the user chose 0.01. Every k from 0.74 to 1.36 gives the same 6/7, and k = 1 sits in the middle of that range.
- **Against the alternatives:**
  - The author-school "digits per timeframe" rule reproduces 0 of 7. That rule is what V2 is said to use by default, and it matches SQ9-36's Multiplier table for 1.xxxxx prices. The user's FX choices are exactly one decade above it.
  - SQ9-36's table reproduces 0 of 7.
- **Across 17 symbols × H1/H4/D1** (50 combinations):
  - B10 keeps the 45° step between **0.58 and 1.74 ATR14**, and the median simulated trade resolves in **10 to 32 bars**.
  - The digits rule gives steps from **0.07 to 13.6 ATR**. Its median time to resolution runs from **1 to 776 bars**.
- **Fit with the author's teaching:** B10 automates the Space adjustment the tutorial does by eye ("Space is not fixed; we change it according to the speed of the movement", see §2.3).

## 1. The maths: what Space does

V2's level formula (confirmed in `docs/research/v2-live-observations.md`): `level(θ) = (√(O·S) ± θ/180)² / S`. Write `s = √(O·S)` and `N = O·S` (the "SQ9 number").

| Quantity | Exact | Approximation (s ≫ 1) |
| --- | --- | --- |
| 45° step from Origin | `(s·0.5 ± 0.0625)/S` | `0.5·√(O/S)` |
| 0°→90° (the risk) | `(s ± 0.25)/S` | `√(O/S)` |
| 90°→360° (the reward) | `(3s ± 3.75)/S` | `3·√(O/S)` |
| Relative 45° step | | `0.5/√N` |
| R:R at entry 90°, SL 0°, TP 360° | bull `3 + 3/(s + 0.25)`; bear `3 − 3/(s − 0.25)` | 3 |

(± is + for a bullish Origin, a low; − for a bearish one, a high.)

Consequences:

- **Space moves step size by its square root.** The step scales as `S^-1/2`, so ×10 Space makes the step **÷3.16** (√10), and ×100 Space makes it ÷10.
  - The data agrees: EURUSD at O = 1.2081, S = 10000 gives an exact 45° step of 0.0054894 against an approximation of 0.0054957 (`user2.py`).
  - The tutorial says the same thing: "angle 144 at Space 10000 is the same as angle 45 at Space 1000" ([t242275-37](https://forum.arabictrader.com/t242275-37.html)), and 45° × √10 ≈ 142°.
- **R:R depends only on √N.** It is about 3:1 at any Space. It only turns lopsided when √N is small: ≈ 2.4 to 2.7 on the bearish side when √N < 10.
  - √N < 10 happens on high-ATR% instruments, here crypto D1, NGAS D1 and SILVER D1.
  - Example: GOLD D1 at the user's S = 0.01 has √N = 7.5, giving a bearish R:R of 2.585 (`user2.py`).
  - When √N ≤ 2 (N ≤ 4), the bearish 360° level falls to zero or below and does not exist.
- **Space does not change the odds of a trade.** The 0→90 and 90→360 distances keep a fixed 1:3 ratio, so under a random walk P(TP before SL) ≈ 25% at every Space. The simulations agree, with TP hit rates of 20 to 31% for B10 (`cross.py`).
  - What Space *does* set is the **trade's size in ATR**, and so its **duration**, its **spread/commission share** and how much **bar noise** sits around the 45°/90° tolerance zones.
  - That makes "step ≈ k·ATR" the natural normalisation.

## 2. Evidence

### 2.1 The user's own choices (live chart profiles)

Control-panel values saved in `~/.wine/.../profiles/default/chart0{1..7}.chr` (objects `CP_AngleE`, `CP_SpaceE`, `CP_FrameT`, read only):

| Chart | Symbol | TF | Angle | Space (saved) |
| --- | --- | --- | --- | --- |
| chart01 | EURUSD | H4 | 90 | 10000 |
| chart02 | GBPUSD | H1 | 90 | 100000 |
| chart03 | GOLD | D1 | **144** | 0.01 |
| chart04 | GBPUSD | H1 | 90 | 100000 |
| chart05 | NGAS-APR26 | H4 | **180** | 100 |
| chart06 | EURUSD | H4 | 90 | 10000 |
| chart07 | EURUSD | H1 | 90 | **10000** |

**Discrepancy:** chart07 (EURUSD H1) has Space **10000** saved, but the user says they use **100000** on EURUSD H1. This doc follows the user's stated value. If chart07's 10000 is the real choice, no rule tested here fits it together with the EURUSD H4 = 10000 charts: both would need the same Space at very different ATRs. **The user should confirm.**

ATR14 is read at each chart's Origin bar from the HST files (`user2.py`):

| Chart | Angle | User Space | N=O·S | ATR14 | 45° step | step/ATR14 | step/ATR100 | 0→360/ATR | R:R (dir) | B* (k=1) cont. | log10(B*/user) | A (digits) | C (SQ9-36) | B10 k=1 (ATR14) | B10 k=1 (ATR100) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EURUSD H4 (chart01) | 90 | 10000 | 1.208e+04 | 0.0041512 | 0.0054894 | 1.32 | 2.12 | 10.5 | 2.973 | 1.75e+04 | +0.24 | 1000 ✗ | 1000 ✗ | 10000 ✓ | 100000 ✗ |
| EURUSD H4 (chart06) | 90 | 10000 | 1.151e+04 | 0.0040973 | 0.0053696 | 1.31 | 1.77 | 10.6 | 3.028 | 1.71e+04 | +0.23 | 1000 ✗ | 1000 ✗ | 10000 ✓ | 10000 ✓ |
| EURUSD H1 (chart07) | 90 | 100000 | 1.15e+05 | 0.002217 | 0.0016964 | 0.77 | 0.95 | 6.1 | 3.009 | 5.85e+04 | -0.23 | 10000 ✗ | 10000 ✗ | 100000 ✓ | 100000 ✓ |
| GBPUSD H1 (chart02) | 90 | 100000 | 1.348e+05 | 0.002312 | 0.0018352 | 0.79 | 0.77 | 6.3 | 2.992 | 6.3e+04 | -0.20 | 10000 ✗ | 10000 ✗ | 100000 ✓ | 100000 ✓ |
| GBPUSD H1 (chart04) | 90 | 100000 | 1.322e+05 | 0.0019985 | 0.0018184 | 0.91 | 0.84 | 7.3 | 3.008 | 8.27e+04 | -0.08 | 10000 ✗ | 10000 ✗ | 100000 ✓ | 100000 ✓ |
| GOLD D1 (chart03) | 144 | 0.01 | 55.86 | 112.52 | 367.44 | 3.27 | 4.92 | 23.0 | 2.585 | 0.11 | +1.04 | 1 ✗ | 1000 ✗ | 0.1 ✗ | 0.1 ✗ |
| NGAS H4 (chart05) | 180 | 100 | 347.2 | 0.092688 | 0.092544 | 1.00 | 1.17 | 7.6 | 2.837 | 101 | +0.00 | 1000 ✗ | 1000 ✗ | 100 ✓ | 100 ✓ |

`B*` is the continuous value `0.25·O/ATR14²`, and `log10(B*/user)` is how many decades the user's choice sits from it. Snapping is correct when this is within ±0.5.

Readings:

- **FX and NGAS: the 45° step is about one bar's ATR.** Across the 5 FX charts and NGAS H4, the user's choices put the 45° step at **0.77 to 1.32 × ATR14**, and the 0°→360° span at 6 to 11 ATR.
- **GOLD D1 is the outlier.** Its 45° step is 3.3 ATR, and 0→360 is 23 ATR, about −46% of price. It is a macro Angle-144 view, not a setup chart for this strategy.
- **The fit holds for any k from 0.74 to 1.36** (`user2.py`). B10 reproduces all 6 non-GOLD charts across that range, and no k can reproduce GOLD D1 together with the others.
- **ATR14 is the best volatility input** (`volm.py`):

| Volatility measure | x per case (EUH4a, EUH4b, EUH1, GUH1a, GUH1b, NGH4, GOLD) | k=1 reproduces (of 6 non-GOLD) | worst margin to rounding boundary (decades of Space) | k range reproducing all 6 |
|---|---|---|---|---|
| ATR14 | +0.24, +0.23, -0.23, -0.20, -0.08, +0.00, +1.04 | 6/6 | +0.26 | 0.74–1.36 |
| ATR50 | +0.55, +0.42, -0.13, -0.26, -0.11, +0.20, +1.26 | 5/6 | -0.05 | 1.05–1.32 |
| ATR100 | +0.66, +0.50, -0.04, -0.23, -0.15, +0.14, +1.40 | 5/6 | -0.16 | 1.20–1.37 |
| SMA-TR100 | +0.65, +0.54, -0.14, -0.25, -0.09, +0.35, +1.27 | 4/6 | -0.15 | 1.19–1.34 |
| median TR100 | +0.88, +0.67, -0.03, -0.16, -0.03, +0.46, +1.38 | 4/6 | -0.38 | none |

ATR14 at the Origin bar fits best (largest margin, widest k range). Slower measures lose the EURUSD H4 chart01 case, whose Origin (2026-01-27) followed a volatility spike.

**Caveat:** this is 6 points from 3 instruments and 2 timeframes, so the fit shows the rule is *consistent* with the user's choices, not that it is uniquely right.

### 2.2 SQ9-36 source (`indcators/AbuHamzah Auto SQ9-36.mq4`, UTF-16LE, decoded)

- **Multiplier table by timeframe** (lines 42–50): M1 1e6, M5 1e5, M15 1e5, M30 1e4, H1 1e4, H4 1e3, D1 1e3, W1 100, MN1 10.
  - The `-00` variant (`AbuHamzah Auto SQ9-36-00.mq4`) is identical but 100× smaller: H1 100, H4 10, D1 10, W1 1, MN1 1.
- **No price-magnitude adjustment.** `GetMultiplier()` (lines 149–163) only switches on `Period()`. The source never reads `Digits` or `Point`.
- **`PriceMultiplier` is an `int`** (line 71, assigned at line 243), so a fractional multiplier such as 0.01 would truncate to 0. V2's Space accepts fractions (GOLD chart = 0.01), so V2 changed this.
- **Same formula as V2 in Overlay-only mode.** With `PivotStart = 0`, `SQ9 = Overlay·Multiplier` (line 281). Each step is `√SQ9 ± RotateEvery/2/180` (lines 80, 402–410), and the price is `SQ9Number/PriceMultiplier` (line 364). That is the V2 formula, with Multiplier ≡ Space.
- **A second mode in Pivot+Overlay.** The SQ9 number becomes the rounded distance `|round(P·M) − round(O·M)| + 1` (line 265), offset from the pivot (line 355). V2 shows no sign of this mode.
- **The table is the digits rule.** For a price with one integer digit (1.xxxxx), the table is exactly the tutorial's "digits per timeframe" rule in §2.3.

### 2.3 Primary sources online

- **AbuHamzah himself:** no first-party documentation found.
  - The source header names shoqi.net and an author email. `http://www.shoqi.net` returns HTTP 403.
  - The arabictrader threads about V2 ([t236499](https://forum.arabictrader.com/t236499.html), [t263982](https://forum.arabictrader.com/t263982.html)) contain user requests only, no author posts.
- **Closest primary source: the arabictrader workshop on V2.** "ورشة الزوايا السعرية والفواصل الزمنية" ([t242275](https://forum.arabictrader.com/t242275.html)) by `medo93`, Oct–Nov 2017. It is a long, illustrated tutorial on V2 (named "مؤشر ابو حمزة", "AbuHamzah's indicator") with a dedicated three-part Space lesson. Its claims:

  | Page | Claim (translated) |
  | --- | --- |
  | [p9](https://forum.arabictrader.com/t242275-9.html) | The Space button "controls the size of the price cycle". The panel buttons step it by powers of ten (10000 → 1000 → 100), and a smaller Space pushes 360° further away. |
  | [p65](https://forum.arabictrader.com/t242275-65.html), post #970 | Part 1. **Digits per timeframe:** MN 2, W1 3, D1 and H4 4, H1 and M30 5, M15 and M5 6, M1 7. Space is the power of ten that turns the price into an integer with that many digits. For EURUSD 1.1558 that gives MN 10, W1 100 … M1 10⁶. "That is why AbuHamzah's indicator sets EURUSD monthly Space to 10." The tutor adds: "these rules are not fixed … we add or remove a digit according to the case; Space is what we use to adjust the speeds." |
  | [p68](https://forum.arabictrader.com/t242275-68.html), post #1008 | Part 2, two-integer-digit JPY crosses (CADJPY 89.471): MN Space 1, W1 10. Then the **speed correction:** at Space 10 on W1, price "reached 450° in 6 candles, which is illogical", and on D1 at Space 100 it made "4 cycles in 27 candles". The fix is to use the higher timeframe's Space (÷10) to "slow the movement". "Space is not fixed and can be changed when necessary, usually when the movement is fast." |
  | [p74](https://forum.arabictrader.com/t242275-74.html) | Part 3, three-integer-digit JPY (USDJPY 113.464): "the indicator by itself multiplied 113.464 × 0.1" for MN, so MN Space 0.1, W1 1, H1 100. **All-decimal prices** (EURGBP 0.889) are "the most tiring group … two people may use different Space for the same frame … it has no fixed rule". On MN, all of EURGBP's history sat inside a quarter cycle, so the tutor **sped it up** (Space ×10). |
  | [p11](https://forum.arabictrader.com/t242275-11.html), [p28](https://forum.arabictrader.com/t242275-28.html) | "JPY pairs and gold have special treatment in Space." |
  | [p57](https://forum.arabictrader.com/t242275-57.html) | "The yen pairs take two digits fewer than the other pairs." |
  | [p50](https://forum.arabictrader.com/t242275-50.html) | "Space is not fixed; we change it according to the speed of the movement." |

  Reading these together, V2's default Space is the digits rule, `S₀ = 10^(D(tf) − max(1, integer digits of price))`, as the tutor describes it. The practitioner then moves it by whole decades by eye, according to "speed" (how many candles a cycle takes). B10 automates that second step with ATR. Its output is always a power of ten, so the EA's Space can be set on V2 with the panel's ×10 buttons, and the Reference Indicator can still draw the same levels.
- **Gann practice generally.** LuxAlgo's Square-of-9 note: "shift its decimal point to a workable magnitude (for example into the range 1 to 1000)"; "very low-priced or very high-priced instruments are commonly multiplied or divided by a power of ten before taking roots"; "Anchor choice and decimal scaling are discretionary, so published levels differ between practitioners" ([luxalgo.com](https://www.luxalgo.com/library/concept/gann-square-of-9.md)). Scaling by powers of ten is the norm, and there is no canonical rule.
- **Other SQ9 indicators.**
  - MM-Auto SQ9 V1.0 (a TradingView port of the same idea by Mohammad Murad) offers "manual Space (1..8) control, where each index maps to a fixed scale value (0.001 … 10000)". Its only guidance is "Tune Space Multiplier to align levels with historical reactions" ([tradingview](https://www.tradingview.com/script/aMa5vD0I-MM-Auto-SQ9-V1-0)).
  - XrayTrades Dynamic Gann Levels scales by `10^max(0, ceil(log10(high)) − 3)`, a magnitude-only rule ([tradingview](https://in.tradingview.com/script/xLn2wsFm-Dynamic-Gann-Levels-XrayTrades)).
  - No source found gives a volatility-based rule. Everyone either uses price magnitude or tunes by eye.

## 3. Candidate rules

| Id | Rule | User charts reproduced (of 7) | 45° step / ATR14 across 50 symbol×TF | Median bars to SL/TP |
| --- | --- | --- | --- | --- |
| **A**, digits (V2 default per tutorial) | `10^(D(tf) − max(1, intDigits(O)))`, D: MN2 W1 3 D1/H4 4 H1/M30 5 M15/M5 6 M1 7 | 0 (FX one decade low; NGAS one high; GOLD two high) | 0.07 – 13.6 | 1 – 776 |
| A+1 | A × 10 (the user's FX offset) | 5 (fails NGAS, GOLD) | 0.02 – 4.3 | similar spread to A |
| **C**, SQ9-36 table | fixed by TF only | 0 | 0.00 (GOLD/BTC H1) – 13.6 | 1 – 776 |
| B, continuous | `0.25·O/(k·ATR14)²`, k = 1 | 0 exactly (all within ±0.25 decade) | exactly k = 1.00 | ~15–20 |
| **B10**, recommended | B rounded to nearest power of ten | **6** (only GOLD D1 misses) | **0.58 – 1.74** | **10 – 32** (median 16) |

Notes:

- **Why A swings so much.** It ignores volatility. EURCHF H4 gets a 13.6-ATR step, so a trade takes hundreds of bars. OIL, SILVER and LINK on D1 get 0.07 ATR, so lines sit inside one candle. This is the tutor's "too fast / too slow" problem.
- **B10's range is guaranteed.** Because it rounds in log space, the step stays within `k·10^±0.25` ≈ 0.56k – 1.78k ATR whatever the instrument.
- **How "median bars to SL/TP" was simulated** (`cross.py`): from every 7th bar, both directions, enter at 90° with SL at 0° and TP at 360°, using the rule's Space at that bar. It reports bars until either level is touched. Trades unresolved within 3000 bars are dropped, which flatters A's slow cases.

## 4. Results across all symbols (rule B10 with k = 1, rule A for comparison)

There are 17 symbols in `history/XMGlobal-Demo` (the ticket said 14): AUDUSD, BTCUSD, EURCHF, EURGBP, EURUSD, GBPUSD, GOLD, LINKUSD, MATICUSD, NGAS-APR26, OIL-APR26, SILVER, US30-MAR26, USDCHF, USDJPY, USDNOK, USDSEK.

- MATICUSD has no H4 file and USDSEK no D1, giving 50 symbol×TF combinations.
- About 2,050 bars each, except EURUSD/GBPUSD/USDCHF/USDJPY H4, which were trimmed to the last 2,100 bars for comparability.
- The HST `spread` field is 0 everywhere, so spread cost cannot be measured from history.
- Columns: "price" is the last close, used as the Origin. "Points" means `10^-Digits`. "Decade flips" is how often B10's choice changes from bar to bar over the file if re-evaluated every bar; in use it is evaluated once per Origin.

| Symbol | TF | Digits | Price | ATR14 (pts) | **B10 Space** | 45° step (pts) | step / ATR14 | 0→360° / ATR14 | R:R bull / bear | median bars to SL/TP | A Space (digits rule) | A step / ATR14 | A median bars | B10 decade flips /1000 bars |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AUDUSD | H1 | 5 | 0.71066 | 195 | **100000** | 133 | 0.68 | 5.5 | 3.01 / 2.99 | 22 | 10000 | 2.16 | 230.5 | 30 |
| AUDUSD | H4 | 5 | 0.71233 | 254 | **10000** | 423 | 1.66 | 13.4 | 3.04 / 2.96 | 15 | 1000 | 5.27 | 426 | 49 |
| AUDUSD | D1 | 5 | 0.71233 | 625 | **10000** | 423 | 0.68 | 5.5 | 3.04 / 2.96 | 14 | 1000 | 2.15 | 76 | 19 |
| BTCUSD | H1 | 2 | 68453.6 | 62,302 | **0.1** | 41,431 | 0.66 | 5.4 | 3.04 / 2.96 | 15 | 1 | 0.21 | 2 | 34 |
| BTCUSD | H4 | 2 | 68468.1 | 115,369 | **0.01** | 131,457 | 1.14 | 9.4 | 3.11 / 2.88 | 20 | 0.1 | 0.36 | 13 | 33 |
| BTCUSD | D1 | 2 | 68455.2 | 338,314 | **0.001** | 419,938 | 1.24 | 11.0 | 3.35 / 2.63 | 17 | 0.1 | 0.12 | 2 | 27 |
| EURCHF | H1 | 5 | 0.90635 | 97 | **100000** | 151 | 1.55 | 12.4 | 3.01 / 2.99 | 12 | 10000 | 4.90 | 505 | 32 |
| EURCHF | H4 | 5 | 0.91222 | 112 | **100000** | 151 | 1.35 | 10.9 | 3.01 / 2.99 | 19 | 1000 | 13.59 | 776.5 | 4 |
| EURCHF | D1 | 5 | 0.91222 | 354 | **10000** | 478 | 1.35 | 10.9 | 3.03 / 2.97 | 24 | 1000 | 4.28 | 152 | 6 |
| EURGBP | H1 | 5 | 0.87139 | 57 | **1e+06** | 47 | 0.82 | 6.5 | 3.00 / 3.00 | 13 | 10000 | 8.19 | 542 | 39 |
| EURGBP | H4 | 5 | 0.87139 | 119 | **100000** | 148 | 1.24 | 10.0 | 3.01 / 2.99 | 19 | 1000 | 12.48 | 320.5 | 1 |
| EURGBP | D1 | 5 | 0.87139 | 324 | **10000** | 467 | 1.44 | 11.6 | 3.03 / 2.97 | 19 | 1000 | 4.57 | 138.5 | 13 |
| EURUSD | H1 | 5 | 1.16082 | 183 | **100000** | 170 | 0.93 | 7.5 | 3.01 / 2.99 | 23 | 10000 | 2.95 | 265 | 51 |
| EURUSD | H4 | 5 | 1.15092 | 314 | **10000** | 537 | 1.71 | 13.8 | 3.03 / 2.97 | 16 | 1000 | 5.42 | 251 | 42 |
| EURUSD | D1 | 5 | 1.18178 | 608 | **10000** | 544 | 0.89 | 7.2 | 3.03 / 2.97 | 14 | 1000 | 2.84 | 85.5 | 18 |
| GBPUSD | H1 | 5 | 1.32635 | 190 | **100000** | 182 | 0.96 | 7.7 | 3.01 / 2.99 | 20 | 10000 | 3.03 | 168 | 4 |
| GBPUSD | H4 | 5 | 1.34095 | 447 | **10000** | 580 | 1.30 | 10.5 | 3.03 / 2.97 | 18 | 1000 | 4.11 | 210.5 | 79 |
| GBPUSD | D1 | 5 | 1.35625 | 817 | **10000** | 583 | 0.71 | 5.7 | 3.03 / 2.97 | 15 | 1000 | 2.26 | 50 | 27 |
| GOLD | H1 | 2 | 5089.3 | 3,034 | **1** | 3,573 | 1.18 | 9.5 | 3.04 / 2.96 | 16 | 10 | 0.37 | 5 | 30 |
| GOLD | H4 | 2 | 5148.06 | 5,211 | **1** | 3,594 | 0.69 | 5.6 | 3.04 / 2.96 | 14 | 1 | 0.69 | 24 | 38 |
| GOLD | D1 | 2 | 4495.1 | 18,402 | **0.1** | 10,663 | 0.58 | 4.8 | 3.14 / 2.86 | 15 | 1 | 0.18 | 12 | 13 |
| LINKUSD | H1 | 2 | 8.56 | 11 | **100** | 15 | 1.36 | 11.2 | 3.10 / 2.90 | 23 | 10000 | 0.14 | 3 | 35 |
| LINKUSD | H4 | 2 | 8.56 | 24 | **100** | 15 | 0.60 | 5.0 | 3.10 / 2.90 | 18.5 | 1000 | 0.19 | 4 | 34 |
| LINKUSD | D1 | 2 | 8.56 | 59 | **10** | 47 | 0.79 | 6.9 | 3.32 / 2.67 | 15 | 1000 | 0.08 | 1 | 41 |
| MATICUSD | H1 | 5 | 0.1006 | 159 | **10000** | 159 | 1.00 | 8.2 | 3.09 / 2.90 | 17 | 10000 | 1.00 | 20 | 19 |
| MATICUSD | D1 | 5 | 0.1006 | 865 | **1000** | 508 | 0.59 | 5.1 | 3.29 / 2.69 | 16 | 1000 | 0.59 | 3 | 35 |
| NGAS-APR26 | H1 | 3 | 2.91 | 41 | **1000** | 27 | 0.66 | 5.3 | 3.06 / 2.94 | 13 | 10000 | 0.21 | 2 | 16 |
| NGAS-APR26 | H4 | 3 | 3.041 | 76 | **100** | 88 | 1.16 | 9.7 | 3.17 / 2.83 | 18 | 1000 | 0.36 | 4 | 49 |
| NGAS-APR26 | D1 | 3 | 2.91 | 199 | **10** | 276 | 1.39 | 12.9 | 3.53 / 2.42 | 13 | 1000 | 0.14 | 1 | 31 |
| OIL-APR26 | H1 | 2 | 115.24 | 354 | **1** | 543 | 1.54 | 13.3 | 3.27 / 2.71 | 21 | 100 | 0.15 | 4 | 28 |
| OIL-APR26 | H4 | 2 | 115.33 | 450 | **1** | 543 | 1.21 | 10.4 | 3.27 / 2.71 | 10 | 10 | 0.38 | 6 | 61 |
| OIL-APR26 | D1 | 2 | 87.44 | 665 | **1** | 474 | 0.71 | 6.2 | 3.31 / 2.67 | 15.5 | 100 | 0.07 | 1 | 33 |
| SILVER | H1 | 3 | 93.721 | 1,019 | **10** | 1,537 | 1.51 | 12.4 | 3.10 / 2.90 | 16 | 1000 | 0.15 | 1 | 22 |
| SILVER | H4 | 3 | 92.02 | 2,203 | **10** | 1,523 | 0.69 | 5.7 | 3.10 / 2.90 | 15 | 100 | 0.22 | 9 | 13 |
| SILVER | D1 | 3 | 92.348 | 6,963 | **1** | 4,867 | 0.70 | 6.1 | 3.30 / 2.68 | 18 | 100 | 0.07 | 3 | 10 |
| US30-MAR26 | H1 | 2 | 48453.4 | 14,886 | **1** | 11,012 | 0.74 | 5.9 | 3.01 / 2.99 | 15 | 1 | 0.74 | 17 | 24 |
| US30-MAR26 | H4 | 2 | 48453.4 | 26,332 | **0.1** | 34,867 | 1.32 | 10.7 | 3.04 / 2.96 | 14.5 | 0.1 | 1.32 | 39 | 44 |
| US30-MAR26 | D1 | 2 | 48451.9 | 63,841 | **0.01** | 110,684 | 1.73 | 14.4 | 3.13 / 2.86 | 16 | 0.1 | 0.55 | 8 | 31 |
| USDCHF | H1 | 5 | 0.77797 | 166 | **100000** | 140 | 0.84 | 6.8 | 3.01 / 2.99 | 26 | 10000 | 2.67 | 201 | 41 |
| USDCHF | H4 | 5 | 0.77895 | 299 | **10000** | 442 | 1.48 | 11.9 | 3.03 / 2.97 | 12 | 1000 | 4.69 | 298 | 37 |
| USDCHF | D1 | 5 | 0.77172 | 548 | **10000** | 440 | 0.80 | 6.5 | 3.03 / 2.97 | 14 | 1000 | 2.55 | 98 | 12 |
| USDJPY | H1 | 3 | 158.916 | 187 | **1000** | 199 | 1.07 | 8.5 | 3.01 / 2.99 | 17 | 100 | 3.37 | 112 | 6 |
| USDJPY | H4 | 3 | 158.205 | 486 | **100** | 630 | 1.29 | 10.4 | 3.02 / 2.98 | 24 | 10 | 4.10 | 173 | 12 |
| USDJPY | D1 | 3 | 155.911 | 1,302 | **10** | 1,981 | 1.52 | 12.4 | 3.08 / 2.92 | 19 | 10 | 1.52 | 55 | 13 |
| USDNOK | H1 | 5 | 9.59505 | 2,818 | **1000** | 4,904 | 1.74 | 14.0 | 3.03 / 2.97 | 16 | 10000 | 0.55 | 57 | 8 |
| USDNOK | H4 | 5 | 9.59495 | 5,261 | **1000** | 4,904 | 0.93 | 7.5 | 3.03 / 2.97 | 32 | 1000 | 0.93 | 137 | 16 |
| USDNOK | D1 | 5 | 9.59505 | 10,589 | **100** | 15,550 | 1.47 | 12.1 | 3.10 / 2.90 | 26 | 1000 | 0.46 | 11 | 7 |
| USDSEK | H1 | 5 | 9.14211 | 3,227 | **1000** | 4,787 | 1.48 | 12.0 | 3.03 / 2.97 | 19 | 10000 | 0.47 | 18 | 13 |
| USDSEK | H4 | 5 | 9.14211 | 5,869 | **1000** | 4,787 | 0.82 | 6.6 | 3.03 / 2.97 | 27 | 1000 | 0.82 | 56 | 30 |

Cross-checks against the tutorial:

- **JPY comes out two decades below EURUSD, as taught.** B10 gives USDJPY H1/H4 = 1e3/1e2 against EURUSD 1e5/1e4 ([p57](https://forum.arabictrader.com/t242275-57.html)), with no JPY special case.
- **Gold comes out "special" too.** GOLD gets 1–10 against A's 10, also without a special case.
- **Low-priced instruments are handled.** MATICUSD at 0.10 gets 1e4/1e3.
- **Indices and crypto stay sensible.** US30 gets 1 → 0.01 and BTC 0.1 → 0.001.

## 5. Failure cases and guards

1. **Rounding boundary.** When `log10(B*)` sits near x.5, a small change in ATR flips Space by a decade and the step by ×3.16. Re-evaluated every bar, ATR14 flips on 0.1–8% of bars (table). Guards:
   - Freeze Space at Origin confirmation, as recommended.
   - Optionally log `log10(B*) − log10(Space)` in the journal, so near-boundary setups can be studied.
   - A slower ATR is not a fix: it is steadier but fits the user's charts worse (§2.1).
2. **Lopsided or missing bearish levels at high ATR%.** Once snapped, `√N = O/(2·ATR) × 10^±0.5`. Below √N ≈ 10, the bearish R:R falls under 2.7: NGAS D1 2.42, BTC D1 2.63, LINK D1 2.67. At √N ≤ 2 the bearish 360° level is ≤ 0.
   - Guard: refuse setups with `√(O·S) < 10`, or let `MinimumRiskReward` (master plan §4.5) reject them.
3. **Step varies ×3 across symbols.** The ATR-normalised risk ranges over 1.16k–3.5k ATR (0→90 is two steps). Position sizing must use the actual SL distance, which the risk engine already does.
4. **GOLD D1 / macro charts.** B10 will not reproduce the user's large-scale Angle-144 gold view (0.01). If the user wants a bigger "gear" on some symbols, use a per-symbol override or k (e.g. k = 3 on GOLD D1 gives 0.01).
5. **Futures rolls** (NGAS-APR26, OIL-APR26, US30-MAR26). Roll gaps inflate TR, and the symbol name changes each contract. ATR must come from the active contract's bars.
6. **Weekend and news gaps.** These enter ATR14 through true range. ATR at the Origin bar can be inflated right after a gap; chart01's Origin is an example.
7. **Unverified: V2's own Space range and default.** The tutorial *says* V2 defaults to rule A. This was not observed: running V2 was out of scope. Whether V2's panel goes below 0.001 or above 10⁶ is also unknown. MM-Auto SQ9 spans 0.001–10000.
8. **Small sample.** The rule was fitted to 6 user choices (3 instruments, 2 TFs). k = 1 is a round number in the middle of the feasible range (0.74–1.36), not a fitted optimum.

## 6. Alternatives for the user

- **B10 with k = 1 (recommended).** A power-of-ten Space that keeps it settable on V2, with the step ≈ 1 ATR14 at the Origin.
- **B10 with a different k.** k is the only knob. k ∈ [0.74, 1.36] keeps all of the user's FX/NGAS choices. k ≈ 3 moves to a "macro gear", reproducing GOLD D1 0.01.
- **A + per-symbol decade offset table.** Faithful to the author's teaching and to V2's default. But it needs a hand-maintained offset for every symbol and timeframe, which is what the ticket wants to avoid. Its fixed offset of +1 reproduces only the FX choices (5/7).
- **B, continuous, no rounding.** Exact volatility normalisation, but V2's ×10 buttons cannot produce it, so the user could not check the EA's levels on the Reference Indicator unless V2 accepts a typed Space value.
- **C, SQ9-36 table.** Not viable outside 1.xxxxx FX: it gives a 0.01-ATR step on GOLD/BTC H1.
