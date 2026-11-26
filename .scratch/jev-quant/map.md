# JEV QUANT (v1, SQ9/MT4): wayfinder map — CLOSED

**Closed 2026-11-26.** The user redrew the destination: Kronos + Jev on Interactive Brokers (plan v2). The SQ9 edge was a no-go (ticket 14). New map: `.scratch/kronos-jev/map.md`. Decisions below stay as the record of the route walked.

Label: `wayfinder:map`

## Destination

A buildable spec for JEV QUANT Phases 0–6 of `JEV_QUANT_MASTER_PLAN.md` (V2 maths reproduced, `SQ9_90_BREAKOUT_RETEST` state machine, Jev bridge, risk engine, SIGNAL_ONLY / PAPER / guarded BROKER, backtest + Jev replay), with no decision left open, ready for `/to-spec`.

## Notes

- Domain: MT4 / MQL4 trading on XM (XMGlobal-Demo), Node.js 18+ bridge, Jev decision API. Plan: `JEV_QUANT_MASTER_PLAN.md`. Jev reference: `docs/reference/jev-opencode-zen-guide.md`. V2 evidence: `docs/research/v2-live-observations.md`.
- Vocabulary: use `GLOSSARY.md` (e.g. **Origin**, **Reference Indicator**).
- Skills: `grilling` + `domain-modeling` for grilling tickets; `research` for research tickets.
- MT4 runs under Wine on this machine: `~/.wine/drive_c/Program Files (x86)/XM Global MT4/` (portable layout; `MQL4/`, `history/XMGlobal-Demo/*.hst`, `profiles/`). Deep history (ticket 15) lives in the isolated copy: `~/.wine-jevquant/drive_c/JevQuantMT4/history/XMGlobal-Demo 2/*.hst`. The agent may compile and run scripts and the Strategy Tester on **XMGlobal-Demo only**; never a live account, never an EA with trading enabled outside the Tester. The user's MT4 is usually already running: don't kill it or overwrite their profiles.
- Standing decisions from charting (2026-11-26):
  - The **Reference Indicator** is V2. It is reverse-engineered black-box only, never decompiled.
  - V2's price-level formula is confirmed (see the evidence doc).
  - The strategy uses V2 **Angle = 90** (lines every 45°), fixed, not a free input.
  - The EA scans a **configurable symbol list** (start: FX majors/crosses + GOLD) on **one configurable signal timeframe**.
  - **Origin** = the anchor; a low makes it bullish, a high bearish.
- **MT4 isolation rule (learned 2026-11-26):** agent MT4 runs happen ONLY in the separate Wine prefix `~/.wine-jevquant` (`WINEPREFIX=~/.wine-jevquant`). Never launch a terminal inside `~/.wine`: a copy there started LiveUpdate, which closed and upgraded the user's XM terminal (build 1470 → 1492). Never `wineserver -k` in `~/.wine`. Read the user's profiles only from a frozen copy, because the live ones change.
- Research outputs go to `docs/research/<slug>.md`, linked from the ticket (no git remote, so no `research/*` branches).

## Decisions so far

<!-- one line per resolved ticket -->

- [V2 Origin auto-detect rule](issues/01-v2-origin-auto-detect-rule.md): Origin = the **older** of the highest high and the lowest low over 270 bars of the Frame timeframe (window pinned by [Pin V2's auto-detect window by live attach](issues/13-pin-v2-window-live.md)). High vs low comes from Origin vs Close[0]. V2 persists Origins per symbol/TF in `MQL4/Files/AbuHamzah Auto SQ9/*.txt`. [write-up](../../docs/research/v2-origin-auto-detect.md)
- [Space selection formula](issues/02-space-selection-formula.md): candidate `Space = 10^round(log10(Origin / (4·k²·ATR14²)))`, making the 45° step about k ATR. It reproduces 5 of the user's 7 hand settings; the user's Space choices aren't fully consistent with each other. [write-up](../../docs/research/space-selection-formula.md)
- [Space validation on history](issues/12-space-validation-on-history.md): **adopted k = 1, power-of-ten snapped, frozen per Origin, per-symbol override allowed** (decision delegated to the agent by the user). No rule beat another out-of-sample. Real 45° levels were **not respected more than control lines**, and the mechanical strategy was ≈ 0 R out-of-sample (+0.04 R, CI −0.20…+0.30, 138 trades) with stand-in Origins, assumed spreads and ~4.5 months of H1. [write-up](../../docs/research/space-validation.md)
- [Does V2 repaint its Origin?](issues/03-v2-repaint-behaviour.md): **superseded in part by ticket 13: V2 itself does not repaint; it computes only at attach or Reset.** The numbers below are what a *rolling* rule would do, and still motivate the policy. About 70 changes per 1000 bars, 97% from the older extreme sliding off the 270-bar window (median 0.4-step level shift), 3% from 0° breaches (direction flip, about 8 steps). 83% of setups see a mid-setup change. **Confirmed-Origin policy:** rule on the 269 closed bars (`shift 1`), older wins, direction from `Close[1]` (matches V2 live on 99.9% of ticks, ≤ 1 bar lag). Anchor ID = (symbol, TF, bar time, price, H/L, N). Freeze Origin + Space per setup; invalidate on a 0° breach, never on drop-out. [write-up](../../docs/research/v2-repaint.md)
- [Backtest data source and quality](issues/11-backtest-data-source.md): the Strategy Tester runs end to end in the isolated copy (EURUSD H1, Every tick, 72.66% quality, 0 errors); start it with `terminal.exe /portable 'config\<ini>'`, not `/config:`. No external tick data needed: "Open prices only" for signal logic, Every tick to check fills, a **fixed per-symbol spread** (`.hst` spread is 0). The real gap is **history depth** (local H1 is only about 4 months), but the server serves older data when requested. [write-up](../../docs/research/backtest-data-source.md)
- [MT4 test harness under Wine](issues/04-mt4-test-harness-under-wine.md): headless compile works (`wine metaeditor.exe /compile: /log:`, exit code inverted, read the UTF-16 log). The Strategy Tester runs in the isolated `~/.wine-jevquant` copy but needs a one-time saved demo login (HITL). SQ9 maths gets mirrored in Node (`node:test`) with an MQL4 to Node parity check. [write-up](../../docs/research/mt4-test-harness.md)
- [Pull maximum XM history](issues/15-pull-max-history.md): XM serves a fixed bar count per TF: H1 ≈ 6.8 y (from 2020-02), H4 ≈ 7.7 y, D1 ≈ 17 y, M1 only a rolling ~10 weeks. All now in the isolated terminal. Specs captured (100k contract, 0.01 lots, stop level 0, USD, 1:1 leverage); commission unknown. [write-up](../../docs/research/xm-history-depth.md)
- [Pin V2's auto-detect window by live attach](issues/13-pin-v2-window-live.md): window = **shifts 0…269 (270 bars, open bar included)**, ties → older bar, Time setting irrelevant, Frame picks the scanned TF. **V2 never recomputes on its own**: only at attach or Reset. So the EA's rolling confirmed-Origin rule is our own policy, not a mirror of V2's screen. [write-up](../../docs/research/v2-origin-auto-detect.md#live-pinning-ticket-13)
- [Does the SQ9 edge exist under V2's real rules?](issues/14-edge-revalidation.md): **no edge.** 45° levels respected no more than control lines (688k touches, −0.0 pp). Strategy OOS 2023-07→2026-11: 119 trades, −0.10 R (CI −0.35…+0.17), PF 0.86; no symbol/TF survives correction; no entry observable a Jev filter could use. V2's older-extreme Origin is ~252 bars old when confirmed, so the setup rarely fits it. **Go/no-go decision pending with the user.** [write-up](../../docs/research/edge-revalidation.md)

## Not yet specified

- **Jev bridge internals:** decision-store persistence, request retention/expiry numbers, retry/backoff policy, concurrency limit. These become sharp once the Jev error shapes are known and the multi-symbol EA design is settled.
- **Journal & analytics:** JSONL schema, where MT4 writes vs where Node writes, and how both survive restarts. Plus which performance breakdowns the first cut needs.
- **PAPER simulation fidelity:** how spread, commission, slippage and swap are modelled for virtual fills.
- **BROKER guard:** exact startup refusal rules and the config needed to enable it.
- **Backtest methodology:** train / validation / out-of-sample split, walk-forward windows, and what counts as "credible" out-of-sample evidence.
- **Historical performance context for Jev:** which rolling stats go into the snapshot without leaking the future.

## Out of scope

- V2 Time cycles and Channel/Star tools: the strategy is price-levels only (user decision, 2026-11-26).
- Multi-timeframe signals per symbol.
- Phase 7 (running continuous paper trading, hardening in operation): that's operations, past the spec.
- Decompiling the V2 `.ex4`.
- Enabling live trading.
