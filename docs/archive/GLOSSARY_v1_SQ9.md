# JEV QUANT

An AI-assisted trading system that finds Square-of-Nine (SQ9) setups on MT4 charts, asks the Jev decision model to approve them, and executes only what independent risk checks allow.

## SQ9 levels

**Origin**:
The anchor price an SQ9 level set is built from, drawn as 0°. A swing low makes a bullish Origin (levels rise from it); a swing high makes a bearish Origin (levels fall from it).
_Avoid_: anchor, pivot, PivotStart, Overlay (these are indicator input/variable names, not the domain term)

**Reference Indicator**:
AbuHamzah Auto SQ9 V2, the compiled indicator whose drawn levels the system must reproduce exactly. Its source is unavailable, so its behaviour is learned black-box.
_Avoid_: the indicator (ambiguous with SQ9-36), V2 source

**Major Swing**:
A swing low or high that stands out at a glance on the chart, not a small wiggle. The last Major Swing before the current move is where a trader places the Origin.
_Avoid_: pivot, fractal, extreme (the 270-bar extreme is V2's automatic choice, which is not a Major Swing)
