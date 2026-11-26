# Does the SQ9 edge exist under V2's real rules?

Type: research
Status: resolved
Blocked by: 03, 11, 13, 15

## Question

Ticket 12 found no level-respect edge and ≈ 0 R out-of-sample, but it used stand-in Origin rules, assumed spreads and only ~4.5 months of H1. Re-run the level-respect-vs-null test and the mechanical strategy with V2's actual auto-detect rule (from tickets 01/13) under the confirmed-Origin policy (03), on the longest history ticket 11 finds (external data if needed), with realistic costs. Result: is there a mechanical edge worth putting Jev on top of, and on which symbols and timeframes? This is a go/no-go input for the spec, and doesn't by itself decide whether the effort continues.

## Answer

**No edge. This is a no-go for "Jev on top of a mechanical SQ9 edge".** The test used V2's real rule (older of the 270-bar extremes, ties to the older bar), the confirmed-Origin policy with a frozen B10 Space, 12 symbols × H1/H4/D1 on 6.8 / 7.7 / 17 years of XM history, and conservative fixed spreads plus slippage.

- **Level respect:** 688k touches. Real 45° lines are respected 55.4% of the time, the same as half-step and random-phase control lines (edge −0.0 pp, CI ±0.1). No cell survives Holm correction.
- **Strategy:** the tolerances were picked in-sample (before 2023-07), and all 16 sets were negative there. Out-of-sample: 119 trades, win rate 29%, **−0.10 R [−0.35, +0.17]**, PF 0.86, max DD 18 R. It's −0.04 R even without costs. A control grid shifted ±22.5° does no worse. The 2022–26 walk-forward gave −0.19 R. No symbol or TF stands out after correction.
- **Structure:** V2's Origin is a median 252 bars old when confirmed, and price is a median 489° away from it (past 360° in 68% of setups). So the 90/45/90/retest sequence has usually already played out. The strategy only fires about 30 times a year across all 36 series.
- **Jev filter:** no observable at entry (trend, volatility, setup age, distance metrics) separates winners from losers in-sample after correction and then holds up out-of-sample. Pullback depth is a weak hypothesis to log, not a filter.

Write-up: [`docs/research/edge-revalidation.md`](../../../docs/research/edge-revalidation.md)
