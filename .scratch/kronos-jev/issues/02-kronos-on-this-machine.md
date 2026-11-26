# Kronos install and speed on this machine

Type: task
Status: in progress
Blocked by:

## Question

Install Kronos in an isolated venv (scratchpad or `.venv`, never system-wide) and measure inference on the GTX 1650 4 GB and on CPU. Cover Kronos-mini, small and base, a 400-bar lookback, a 24-bar horizon, and N = 30 sample paths, for 12 symbols batched. Report seconds per bar-close cycle, peak VRAM, and whether results are reproducible with a fixed seed. Output: which model sizes are usable live (well under 1 h per cycle) and in backtest, i.e. the cost of a 6-year H1 walk-forward.
