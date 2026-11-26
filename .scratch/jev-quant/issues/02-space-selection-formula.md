# Space selection formula

Type: research
Status: resolved
Blocked by: 

## Question

What formula should the EA use to choose V2's **Space** for any symbol and signal timeframe, given that it scans many symbols on its own? The user wants a derived, tested formula, not a hand-filled table. Inputs: the user's own choices (EURUSD H4 10000, EURUSD H1 100000, GBPUSD H1 100000, GOLD D1 0.01, NGAS H4 100), SQ9-36's per-timeframe `Multiplier*` defaults, primary Square-of-Nine / AbuHamzah sources found online, and price history in `.hst` files. Test candidate rules (price magnitude / digits, ATR so the 45° step is k×ATR, a timeframe factor) against the user's choices and across all 14 symbols. Recommend one formula with evidence and failure cases. Note: the decision of which formula to adopt is the user's; this ticket gathers the evidence.

## Answer

Recommended rule (B10): `Space = 10^round(log10(Origin / (4·k²·ATR14²)))`, k = 1. ATR14 is read on the signal timeframe at the Origin bar, and Space is frozen per setup. In words: the power of ten that makes one 45° step ≈ 1 ATR14.

- **User's charts:** it reproduces 6/7 of the user's Space choices. The exception is GOLD D1, an Angle-144 macro chart. Any k from 0.74 to 1.36 gives the same 6/7.
- **Alternatives:** the author-school "digits per timeframe" rule (V2's default per the arabictrader tutorial, and identical to SQ9-36's Multiplier table) and SQ9-36's own table both reproduce 0/7.
- **Across 17 symbols × H1/H4/D1:** B10 keeps the 45° step at 0.58–1.74 ATR and trades resolving in 10–32 bars. The digits rule ranges over 0.07–13.6 ATR.
- **Caveats:** decade flips near the rounding boundary; the bearish R:R falls below 2.7 when √(O·S) < 10; the user's chart07 profile has Space 10000 saved, not 100000.

Evidence: [`docs/research/space-selection-formula.md`](../../../docs/research/space-selection-formula.md). Adoption is for the user to confirm.
