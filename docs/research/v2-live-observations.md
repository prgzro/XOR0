# V2 live observations (black-box)

Gathered 2026-11-26 from the user's saved MT4 chart profiles, where V2 was attached:
`~/.wine/drive_c/Program Files (x86)/XM Global MT4/profiles/default/chart0{1..8}.chr`.
The `.ex4` itself is encrypted; its only readable header is `Copyright © 2016, AbuHamzah`, version `2.00`.

## V2 inputs (as saved in `chart01.chr`)

```
AutoDetect=true          IsLow=true             RotationCount=2
ShowSubLine=true         ContinuousAngles=true  ShowControl=true
ChannelShowCross=false   ChannelShowAll=false
```

The SQ9-36 per-timeframe `RotateEvery*` / `Multiplier*` inputs are gone; V2 moves those to an on-chart **control panel**.

## Control panel (per chart, saved as `CP_*` objects)

| Field | Meaning (inferred) | Seen values |
| --- | --- | --- |
| Angle | Line spacing = Angle / 2 degrees | 90, 144, 180 |
| Space | Price scale (SQ9-36's `Multiplier`) | 0.01, 100, 10000, 100000 |
| Time | Time-cycle setting | 90 everywhere |
| Frame | Calculation timeframe, `Fix` = pinned | H1, H4, D1 |
| Tools | Channel / Star overlays | None everywhere |

## Price-level formula: confirmed

Every `Price_Line` on all 7 charts matches this formula to 6 decimal places (no rounding):

```
level(θ) = ( √(Origin × Space) + d × θ / 180 )² / Space
d = +1 when Origin is a low (levels rise), −1 when Origin is a high (levels fall)
```

| Chart | Origin | Space | Angle | Check |
| --- | --- | --- | --- | --- |
| GBPUSD H1 | 1.348087 (high) | 100000 | 90 | 45° → 1.346252 ✓, 360° → 1.333440 ✓ |
| GBPUSD H1 | 1.321750 (low) | 100000 | 90 | 45° → 1.323568 ✓ |
| EURUSD H4 | 1.208100 (high) | 10000 | 144 | 72° → 1.199323 ✓ |
| GOLD D1 | 5585.634821 (high) | 0.01 | 144 | 720° → 1206.666444 ✓ |
| NGAS H4 | 3.472187 (high) | 100 | 180 | 90° → 3.288349 ✓ |

## Correction: the profiles changed during research

The terminal restarted at 01:40:57 on 2026-11-26 and re-saved every chart. The **current** settings, read from the drawn lines plus the panel, differ from the first read above:

| Chart | Symbol / TF | Line step | Space | Origin |
| --- | --- | --- | --- | --- |
| chart01 | EURUSD H4 | 45° (Angle 90) | 10000 | 1.208100 |
| chart02 | GBPUSD H1 | 45° | 100000 | 1.348087 |
| chart03 | GOLD D1 | 72° (Angle 144) | 0.01 | 5585.634821 |
| chart04 | GBPUSD H1 | 45° | 100000 | 1.321750 |
| chart05 | NGAS-APR26 H4 | 90° (Angle 180) | 100 | 3.472187 |
| chart06 | EURUSD H4 | 45° | 10000 | 1.088010 |
| chart07 | EURUSD H1 | 45° | **10000** | 1.088010 |

The table below shows the older save. A frozen copy of the 01:40:57 profiles is in the session scratchpad (`profiles-snapshot-0149`). Line formula still fits exactly.

## Origin samples (for the auto-detect research)

`OverlayPrice` is a trend-line object; `time_0` is the Origin bar, `value_0` its price.

| Chart | Frame | Origin price | Origin bar time (server) |
| --- | --- | --- | --- |
| chart01 EURUSD | H4 | 1.208100 | 2026-01-27 20:00 |
| chart02 GBPUSD | H1 | 1.348087 | 2026-03-10 17:00 |
| chart03 GOLD | D1 | 5585.634821 | 2026-01-28 00:00 |
| chart04 GBPUSD | H1 | 1.321750 | 2026-03-13 22:00 |
| chart05 NGAS-APR26 | H4 | 3.472187 | 2026-03-09 00:00 |
| chart06 EURUSD | H4 | 1.150600 | 2026-03-09 00:00 |
| chart07 EURUSD | H1 | 1.150251 | 2026-03-09 02:00 |

GOLD's Origin has more decimals than a real quote; it may have been dragged by hand.
