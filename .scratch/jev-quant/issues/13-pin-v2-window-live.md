# Pin V2's auto-detect window by live attach

Type: task
Status: resolved
Blocked by: 11

## Question

In the isolated test terminal (`WINEPREFIX=~/.wine-jevquant` only), attach V2 fresh on chosen symbols and timeframes at noted times and read its state file. Use that to settle: (a) whether the window is 269 or 270 bars, (b) whether bar 0 is included, (c) whether the panel's Time setting drives the window (270 = 3 × 90), (d) whether Frame ≠ chart timeframe changes which bars are scanned. Drive it through templates, startup inis and V2's state file, with no GUI clicks. If a step truly needs a click, write the user a precise HITL checklist. AFK where possible.

## Answer

(a) **270 bars**, (b) **bar 0 included** (shifts 0…269). Of 141 auto rows from 22 fresh attaches in the Strategy Tester, this is the only window that fits all of them, and 39 rows need bar 0. Ties go to the **older** bar. Confidence high.
(c) **Time doesn't change the window.** Moving Time to 45…144 never moved the Origin, and Reset puts Time back to 90 before it recomputes. (d) **Frame picks the TF that is scanned and its state row, whatever the chart TF is.** On an H1 chart with Frame=H4, Reset gives the H4-bar Origin. Frame can't go below the chart TF.
New finding: V2 **doesn't repaint on its own**. It computes an Origin only at attach (for a TF with no stored row) or on Reset, and in the Tester it stayed fixed for 864 bars. All of this was driven AFK: Tester `iCustom` plus posted clicks on V2's panel buttons. No HITL needed.
[write-up](../../../docs/research/v2-origin-auto-detect.md#live-pinning-ticket-13)
