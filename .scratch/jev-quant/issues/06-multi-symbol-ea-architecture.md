# Multi-symbol EA architecture

Type: grilling
Status: wontfix
Blocked by: 04

## Question

One EA on one chart scanning the whole symbol list, or one EA instance per chart? Decide how bars are detected as closed per symbol, how per-symbol state (Origin, setup state machine) is stored and restored after a restart, how WebRequest polling of the bridge is shared, and what MT4 limits (one OnTimer, synchronous WebRequest, Strategy Tester being single-symbol) force. The Tester constraint matters most: backtests must still be possible.
