# Space validation on history

Type: research
Status: resolved
Blocked by: 02

## Question

Which Space rule gives V2 levels (Angle = 90, 45° steps) that price actually respects, and on which the mechanical `SQ9_90_BREAKOUT_RETEST` sequence holds up out-of-sample? Compare the ticket-02 formula `Space = 10^round(log10(Origin / (4·k²·ATR14²)))` for a few discrete k values, its ×10 / ÷10 neighbours, and the SQ9-36 digits rule. Settle the EURUSD H1 question (user's chart has 10000; the formula gives 100000). The user delegated the Space decision: "discover it and make all great". So this ticket's answer is the adopted rule, chosen on out-of-sample evidence, not in-sample fit.

## Answer

No Space rule is clearly better, so the safest default is adopted: **`Space = 10^round(log10(Origin / (4·ATR14²)))`** (ticket-02 B10, k = 1, ATR14 at the Origin bar, frozen per Origin, power of ten so V2 can show it).
Across 10 FX+GOLD symbols on H1/H4 and 2 non-repainting Origin rules, 45° levels are respected no more than half-step-shifted control lines (edges within ±1 pp, CIs span 0), and no candidate beat k=1 on in-sample+validation expectancy (every Δ CI spans 0).
Adopted rule out-of-sample: 138 trades, 34.8% wins, +0.04 R (95% CI −0.20 to +0.30), PF 1.06: zero within noise, not a profitability claim.
EURUSD H1: 10000 and 100000 are indistinguishable; the user's 10000 corresponds to k ≈ 4.6 (or the digits rule), so keep the formula and allow a per-symbol override if wanted.
Write-up: [docs/research/space-validation.md](../../../docs/research/space-validation.md)
