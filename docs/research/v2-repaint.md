# Does V2 repaint its Origin? (replay study + confirmed-Origin policy)

Researched 2026-11-26 for ticket `.scratch/jev-quant/issues/03-v2-repaint-behaviour.md`.
Method: pure-Python replay (`python3 -I`) of the ticket-01 rule over read-only XM history. No MT4/Wine was run and the `.ex4` was not opened.
Scripts and outputs are in the session scratchpad (ephemeral): `/tmp/claude-1000/-home-prgzro-Projects-XOR0/205c3630-a6e9-485f-b79e-e22a252b80f3/scratchpad/repaint/`

| File | What it does |
| --- | --- |
| `replay.py` (+ `replay_N270.txt`, `replay_N269.txt`) | bar-by-bar replay: change counts, causes, flips, lifetimes, level shifts, live-vs-confirmed lag |
| `check.py` | brute-force `iHighest/iLowest(…,270,1)` emulation on 3000 random bars: **0 mismatches** with the replay |
| `survival.py` (+ `.txt`) | parameter-free: P(V2's Origin unchanged k bars later), Origin age, level drift vs a frozen Origin |
| `lifetimes.py` (+ `.txt`) | lifetimes split into "edge-born" vs other Origins; crawl episodes |
| `setup.py` (+ `.txt`) | toy `SQ9_90_BREAKOUT_RETEST` state machine; freeze vs strict policy; agreement of two closed-bar policies with V2 live |

## Answer

1. **If V2 re-applies its rule as bars arrive, its Origin is unstable.** The Origin changes about **70 times per 1000 bars** on both H1 and H4. **97–98 %** of those changes are **drop-outs**. The Origin is the *older* extreme, so its median age is about **232 bars** (p75 ≈ 260). It often sits at the left edge of the 270-bar window and then "crawls": each new bar pushes it out, and the next-oldest extreme takes over. A drop-out usually moves the 90° level only a little (median **0.4 steps of 45°**). Over a setup's life the moves add up: after 50 bars V2's 90° level is a median **0.95 steps** away from a frozen Origin's, and **4.3–4.6 steps** away after 100 bars.
2. **The other 2–3 % of changes are breaches, and every one flips direction.** A wick beyond the Origin (a new extreme of the *same* kind) makes the *other*, older extreme the Origin. The levels jump about **8 steps** and switch between bull and bear. This is the subtle effect the ticket asked about, and it is confirmed. A drop-out flips direction only about 4 % of the time.
3. **During a bar V2 changes only in one direction and never reverts.** There is no flicker. A change on the forming bar can only come from a breach, and the bar's running high and low only expand, so the change sticks. Only 11 of 86 474 bars showed a live Origin that was never confirmed.
4. **Mid-setup changes are common, and hindsight differs.** Starting from any bar, V2's Origin is unchanged after 20 bars only **62 %** of the time, and after 50 bars only **38–39 %**. A setup traded off V2's live chart will usually look different when the chart is reloaded later. Within 270 bars it **always** does.
5. **Proposed policy (closed bars only).** Evaluate the rule at each new bar over **shifts 1..269**, the 269 closed bars. Take direction from `Close[1]`. Give each Origin an identity. **Freeze** the Origin and its Space at setup start. Invalidate on a breach of 0° (to be decided: close only, or wick too), never on a drop-out. This policy matches V2's live identity on **99.9 %** of intrabar points. It lags V2 by at most one bar, and only on breach bars. It is deterministic for any given bar history.

A large caveat sits under all of this. Ticket 01 found that V2 **stores** its Origin and does not recompute it on every tick. Whether V2 *actually* crawls live, or only recomputes on load, reset or TF switch, is **not measured** (see HITL). Points 1–4 describe the rule if it is re-applied each bar. That is also exactly what a reload at any later time shows.

## 1. Data and set-up (facts)

- **Data:** history from `history/XMGlobal-Demo/<SYM><60|240>.hst` (HST v401).
  - Symbols: AUDUSD, EURCHF, EURGBP, EURUSD, GBPUSD, USDCHF, USDJPY, USDNOK, USDSEK, GOLD, on H1 and H4.
  - Spans: H1 runs Oct 2025 → Mar 2026, about 2 000–2 600 bars each. H4 runs Oct/Nov 2024 → Mar 2026, about 2 050 bars each; EURUSD, GBPUSD, USDCHF and USDJPY H4 go back to Dec 2009 (about 14 300 bars).
  - Evaluated bars (after the 269-bar warm-up): **19 413 on H1 and 67 041 on H4**.
- **Rule:** from ticket 01, with N = 270 and bar 0 included.
  - Ties go to the newest bar, as `iHighest` scanning from shift 0 would give.
  - Ties are rare: 56 bars in total had a tied window extreme.
  - Space is B10 from ticket 02, computed once per Origin from ATR14 at the Origin bar.
- **Simulating bar 0 live:** each bar is played as four ticks: open → nearer extreme → farther extreme → close.
  - At every tick, V2 is taken to see the 269 closed bars plus the forming bar's running high, low and price.
  - This is the "V2 recomputes continuously" assumption.
- **Confirmed value `CONF(t)`:** the rule applied after bar t closes. This equals `iHighest/iLowest(…, 270, 1)` evaluated during bar t+1.
  - `CONF(t)` is identical to V2's live value on bar t's last tick: same window, final high and low, and the close.

## 2. How often and why the Origin changes (facts, `replay_N270.txt`, `lifetimes.txt`)

Measured on the closed-bar series (`CONF`):

| | H1 | H4 |
| --- | --- | --- |
| Bars | 19 413 | 67 041 |
| Origin changes | 1 353 (**69.7 / 1000 bars**) | 4 892 (**73.0 / 1000 bars**) |
| … drop-out (Origin left the 270-bar window) | 1 326 (98.0 %) | 4 767 (97.4 %) |
| … new extreme beyond the Origin (breach) | 27 (2.0 %) | 125 (2.6 %) |
| … other | 0 | 0 |
| Direction flips (high↔low), total | 79 (5.8 % of changes) | 288 (5.9 %) |
| … flips among drop-outs | 52 / 1 326 (3.9 %) | 163 / 4 767 (3.4 %) |
| … flips among breaches | **27 / 27 (100 %)** | **125 / 125 (100 %)** |
| Age of the new Origin: drop-out / breach (median bars) | 269 / 125 | 269 / 110 |

Per symbol, changes per 1000 bars range from 46 (EURCHF H4) to 124 (GOLD H4, which trended strongly in 2025–26). The full table is in `replay_N270.txt`. With **N = 269** the figures are essentially the same (`replay_N269.txt`: 1 357 and 4 900 changes, the same split), so this result does not depend on the 269/270 question.

**Level shift when the Origin changes.** Shifts are in ATR14 at the change and in 45° steps of the old Origin. Pooled H1 / H4:

| Cause | \|ΔOrigin\| ATR, median (p90) | \|Δ90° level\| ATR, median (p90) | \|Δ90° level\| in 45° steps, median (p90) |
| --- | --- | --- | --- |
| Drop-out | 0.3 (1.3) / 0.3 (1.3) | 0.4 (2.0) / 0.4 (2.0) | 0.4 (1.6) / 0.3 (1.5) |
| Breach (always flips) | 12.2 (17.4) / 11.9 (16.8) | 6.7 (12.2) / 7.6 (12.2) | 8.1 (18.4) / 8.4 (20.5) |

**Lifetime of an Origin identity** (closed bars):

| | H1 | H4 |
| --- | --- | --- |
| All identities: p25 / median / p75 / p90 | 1 / 1 / 8 / 40 | 1 / 1 / 6 / 35 |
| Born at the window edge (age ≥ 260), n | 1 065: median 1, p90 5 | 3 938: median 1, p90 5 |
| Born elsewhere, n | 278: p25 16, **median 34**, p75 86, p90 144 | 944: p25 19, **median 37**, p75 93, p90 145 |
| Crawl episodes (drop-outs on consecutive bars) | 604, median 2 bars, max 10 | 2 196, median 2, max 18 |

How old the Origin is: H1 p10 143, median 234, p90 267. H4 p10 136, median 231, p90 268. **24.6 %** of all bars have an Origin aged ≥ 260 bars, which is edge-riding (`check.py`).

**Within the forming bar** (`replay_N270.txt`, columns `intrabar`, `unconf`):

- On about 1.5 per 1000 bars, V2's identity changes during the bar after the open tick. All of these are breaches by a wick.
- Such a change never reverts before the close.
- Only **11** live identities in 86 474 bars were shown and then never confirmed. Each came from an open-tick drop-out followed by a breach within the same bar.

## 3. The "older wins" breach effect (fact + derivation)

Take a bullish Origin, the low L at shift a, with the window high H at a newer shift b < a. Two things can happen:

- **Price makes a new high.** That only renews the newer extreme. The Origin stays the same.
- **Price wicks below L.** The new low sits at shift 0, so the high at shift b is now the *older* extreme. The Origin becomes H, the levels turn **bearish**, and the new Origin sits roughly a whole swing away.

The mirror image holds for a bearish Origin. The data confirms that every breach-caused change flipped (152/152). A wick through 0° is therefore the only way the Origin changes on the forming bar. It is also the strategy's stop level.

On the bull/bear label:

- In the replay, the `Origin > Close[0]` test always agreed with the extreme's kind (high ⇒ bearish).
- This follows from the maths: a window high is ≥ every close in the window. Equality is a measure-zero edge case.
- So "direction flip" and "kind change" are the same event.

## 4. Repaint risk for `SQ9_90_BREAKOUT_RETEST` (facts from `survival.py`, `setup.py`)

### 4a. Parameter-free survival

Pick any bar. Is V2's live Origin unchanged at every tick for the next k bars?

| k bars | H1 unchanged | H4 unchanged | Median (p90) gap between V2's 90° level and a frozen Origin's, in 45° steps | Direction flipped |
| --- | --- | --- | --- | --- |
| 5 | 82.6 % | 82.2 % | 0.00 (0.71–0.74) | 2.0 % |
| 10 | 73.7 % | 74.1 % | 0.00 (1.8–1.9) | 4.0–4.2 % |
| 20 | 61.6 % | 62.1 % | 0.00 (4.9); p75 1.0–1.1 | 7.8–8.3 % |
| 50 | 38.0 % | 39.2 % | 0.95 (10.4–11.3) | 18.5–18.9 % |
| 100 | 15.9 % | 16.4 % | 4.3–4.6 (15.0–17.6) | 32–33 % |

The same survival split by the Origin's age at the start (H1 / H4):

| Age at start | k = 10 | k = 20 | k = 50 | k = 100 |
| --- | --- | --- | --- | --- |
| < 135 bars | 100 / 99 % | 100 / 98 % | 99 / 94 % | 97 / 85 % |
| 135–259 | 98 / 98 % | 80 / 80 % | 45 / 46 % | 12 / 12 % |
| ≥ 260 (edge) | 0 / 0 % | 0 / 0 % | 0 / 0 % | 0 / 0 % |

Survival is set mostly by **remaining window life = 270 − age**. Breaches are rare by comparison.

### 4b. Toy state machine

`setup.py` uses assumed, not decided, parameters:

- tolerances in 45° steps: pullback ±0.15, breakout buffer 0.05, retest 0.10;
- "initial move" means the price reached 67.5°;
- timeouts: setup 120 bars, retest 20 bars;
- one setup per new confirmed Origin, at most one active at a time per symbol/TF.

It found **735** setups and **26** entries. With the Origin frozen:

| | H1 | H4 |
| --- | --- | --- |
| Setups where V2's live Origin changed mid-setup | 135 / 163 (**83 %**); 129 drop-out, 6 breach; median 18 bars in | 473 / 572 (**83 %**); 437 drop-out, 36 breach; median 19 bars in |
| Entries where it changed before entry | 8 / 9 | 13 / 17 |
| V2 still shows the setup's Origin 10 / 50 / 270 bars after the setup ends | 14 % / 6 % / 0 % | 14 % / 6 % / 0 % |
| … for entries only | 0 % / 0 % / 0 % | 0 % / 0 % / 0 % |
| Setups that started on an edge-riding Origin (all of them changed) | 52 / 163 | 190 / 572 |

The **strict** policy invalidates a setup whenever the confirmed identity changes. It invalidated **3 875 of 4 151** setups with reason `anchor_changed`. It produced 18 entries, against 26 under freeze. A strict policy is therefore mostly a drop-out detector. The absolute entry counts depend on the made-up parameters. The change rates do not, and they agree with table 4a.

## 5. Confirmed-Origin policy (proposal)

**Evaluation.** At the first tick of each new signal-TF bar (`Time[0]` changed), compute:

```
Hi = iHighest(sym, tf, MODE_HIGH, AnchorWindowClosed, 1)   // AnchorWindowClosed = N-1 = 269
Lo = iLowest (sym, tf, MODE_LOW,  AnchorWindowClosed, 1)
Origin = (Hi > Lo) ? High[Hi] : Low[Lo]       // older wins; ties -> newest bar
bearish = Origin > Close[1]
```

- Only closed bars are read. The forming bar is never used.
- **Agreement with V2 live** (`setup.py`), at all four intrabar points of every bar:

| Closed-bar policy | H1 points | H4 points | Bars matching at every point |
| --- | --- | --- | --- |
| A: shifts 1..270 (the naive "use bar 1" of the N-bar rule) | 93.10 % | 92.79 % | 93.0 / 92.7 % |
| **B: shifts 1..269 (recommended)** | **99.92 %** | **99.89 %** | **99.84 / 99.80 %** |

- **Why A is worse.** V2's window counts bar 0. At each bar's open, V2 has already dropped the 270th-oldest bar. Policy A still holds it, so A lags V2 by one bar on **every** drop-out, which is 93 % agreement.
- **How B behaves.** B drops the same bar at the same open. It differs from V2 only when the forming bar breaches the Origin, and then it catches up at the next open (lag ≤ 1 bar).
- **Lag measured** for policy A (`replay.py`): every one of the 6 245 identities was adopted exactly 1 bar after V2 first showed it.

**Origin identity (anchor id).** `(symbol, tf, originBarTime, originPrice, kind H|L, window N)`. Direction follows from `kind`. The journal stores this tuple together with the frozen Space and the derived 0/45/90/360 levels. This satisfies §4.3, "a current anchor identifier".

**Per-setup freeze.**

- When a setup leaves `WAIT_ORIGIN`, it binds the current identity, Space and levels. These are never recomputed for that setup.
- A later change of the EA-level Origin (a drop-out crawl) does **not** invalidate a running setup. It only means new setups use the new Origin.
- Breach handling is **open for the user**, against §4.4 "origin becomes invalid":
  - **(i)** invalidate on a completed close beyond 0°. This fits the strategy's own "completed candle" style.
  - **(ii)** also invalidate when a wick trades beyond 0°. That is exactly when V2's identity flips (§3).
  - Either way it is a 0° event, which is the stop level. It is never a drop-out.

**Optional guard (inference, user decision).** Require `age = Hi/Lo shift ≤ AnchorWindowClosed − MaximumSetupBars` before starting a setup. V2's chart would then still show the same Origin for the whole setup, under the assumption of continuous recompute. Example: from table 4a, Origins younger than 135 bars survive 20 bars ≥ 98 % of the time. The cost is fewer setups.

**Determinism in backtests (inference from the construction, not tested in MT4).**

- Policy B is a pure function of the last 269 closed bars, plus ATR14 at the Origin bar for Space.
- For the same bar history, the Strategy Tester, a Node replay and live trading give the same identities. Tick modelling cannot change them, because bar 0 is never read.
- What can still break determinism:
  1. A different bar history. For example, the `XMGlobal-Demo` and `XMGlobal-Demo 2` histories differ, and so can gaps and server-time shifts.
  2. The 269-bar warm-up at the start of the test, plus 14 bars for ATR.
  3. The tie-break convention. This replay uses newest-wins, and ties are rare: 56 of 86 474 bars.
  4. Whether V2's true window is 269 or 270 (ticket 01 HITL). Make `AnchorWindowClosed` an input.
- A backtest must compute the Origin **as of each bar**. It must never take V2's (or the rule's) current Origin and apply it to past bars: by table 4a, that Origin did not exist at decision time in most cases.

## 6. Facts vs inference

**Measured facts** (on this XM history, under the ticket-01 rule):

- the change rates, the causes, the 100 % breach-flip rate, the lifetimes and age distribution;
- the level shifts, the survival curves, and the agreement of policies A and B;
- the brute-force cross-check (0/3000 mismatches);
- the N = 269 robustness check.

**Inference or assumption:**

- **V2 recomputes continuously.** That V2 recomputes its auto Origin on every bar or tick is assumed, not observed. Ticket 01 saw that V2 persists Origins in its state file and recomputes per TF on load. If V2 only recomputes on load, reset or TF switch, then:
  - its *on-screen* Origin is stable while a chart stays open;
  - it jumps to the rule's current value on any reload, restart or TF switch, which is the "different after refresh" case in plan §2.3;
  - either way, a past setup cannot be recovered from V2's later drawing.
- **The intrabar path** follows the MT4-tester heuristic: the nearer extreme comes first.
- **The setup machine's parameters** are made up for measurement. They are not the user's strategy.
- **The policy-B determinism claim** comes from its construction. It has not been run in the Tester.

## Open points (HITL)

1. **Does V2 recompute live?** Keep a V2 chart in auto mode (`flag=1`) open across a predicted drop-out, without touching it.
   - Pick a symbol/TF whose Origin age is ≥ 265. `replay.py` / `check.py` can print the bar at which the current Origin drops out.
   - Note whether the drawn 0° line moves at that bar's open, or only after a reload.
   - At the same time, re-read the state file's row and its mtime.
2. **Wick breach live:** does V2 flip direction during the bar, or only at the close or on reload? Same set-up, on an Origin that price is approaching.
3. **User decision:** breach rule (i) or (ii) above, and whether to add the age guard.
