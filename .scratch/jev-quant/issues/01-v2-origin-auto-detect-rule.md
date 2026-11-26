# V2 Origin auto-detect rule

Type: research
Status: resolved
Blocked by: 

## Question

With `AutoDetect=true`, how does V2 choose the **Origin** bar and price, and how does it decide high vs low? Black-box it: compare the 7 Origin samples in `docs/research/v2-live-observations.md` with price history from `history/XMGlobal-Demo/*.hst` (e.g. highest high / lowest low over N bars, whichever is more recent, as in SQ9-36's 225-bar rule). Find N, whether bar 0 (the still-open bar) is included, and whether the Frame setting changes which timeframe's bars are scanned. Flag any samples that look hand-dragged. If the existing samples can't settle it, say exactly which extra live observations are needed (HITL).

## Answer

V2 auto-detect works like SQ9-36 with a longer window. It finds the highest high and the lowest low over about **270 bars of that timeframe's own series, bar 0 included** (best fit 269–270; every symbol tested allows only 265–270), and the **older** of the two becomes the Origin. N = 225 and "newer extreme wins" both fail.
High vs low follows `Origin > Close[0]` ⇒ high (falling levels), else low. Origins are kept per symbol and timeframe in V2's state file (`MQL4/Files/AbuHamzah Auto SQ9/*.txt`, flag 1 = auto, 0 = edited). Samples chart02/03/05/07-old are hand-dragged. chart06 (old and new) and chart07-new are real lows but don't fit the rule, so they were probably dragged with the magnet.
Still open (HITL): 269 vs 270 / bar 0 in or out, whether Time = 90 sets N, and whether Frame ≠ chart TF changes the series scanned.
Details: [docs/research/v2-origin-auto-detect.md](../../../docs/research/v2-origin-auto-detect.md)
