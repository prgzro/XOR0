# How the user picks the Origin and Space by hand

Type: grilling
Status: wontfix
Blocked by: 14

## Question

Ticket 14 found no edge with V2's automatic Origin. The user doesn't trade from it: they drag the Origin to a swing low or high of their choosing and set Space by eye. Capture that choice as a mechanical rule the EA can apply on many symbols (which swing, how far back, low vs high, which Space), from a live show-and-tell session plus the Origins and Spaces the user places on their own charts (read only from a frozen copy of their files). Then re-run ticket 14's test once with that rule, fixed in advance; if it fails too, SQ9 is dropped as an edge (user decision, 2026-11-26).

## Grilling notes (round 1, 2026-11-26)

- Origin = the **start of the current move**: the last major low before price went up, or the last major high before it fell.
- Only a **major swing** counts: one that stands out at a glance (several days of movement on H1), not a small wiggle.
- The expected direction sets the side: a low for up, a high for down.
- Space is set by eye so that one 45° step ≈ one normal swing between lines. This matches the adopted k=1 rule, to be checked against the user's charts.
- The Origin is kept until 0° breaks or a clearly bigger swing forms.

Draft mechanical rule (to be calibrated on the user's charts, then fixed before the test):
- Find major swings with an ATR-scaled zigzag: a pivot is confirmed once price reverses ≥ X·ATR14 from it.
- The Origin is the latest confirmed pivot that started the current leg.
- Replace it only on a 0° breach or a larger confirmed swing.
- X is the only free parameter. Calibrate it to the user's hand-placed Origins, then freeze it before the in-sample/out-of-sample run.

Closed 2026-11-26: the user replaced SQ9 with Kronos (plan v2); no show-me session needed.
