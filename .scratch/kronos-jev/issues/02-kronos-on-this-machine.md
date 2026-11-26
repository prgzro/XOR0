# Kronos install and speed on this machine

Type: task
Status: resolved
Blocked by:

## Question

Install Kronos in an isolated venv (scratchpad or `.venv`, never system-wide) and measure inference on the GTX 1650 4 GB and on CPU. Cover Kronos-mini, small and base, a 400-bar lookback, a 24-bar horizon, and N = 30 sample paths, for 12 symbols batched. Report seconds per bar-close cycle, peak VRAM, and whether results are reproducible with a fixed seed. Output: which model sizes are usable live (well under 1 h per cycle) and in backtest, i.e. the cost of a 6-year H1 walk-forward.

## Answer

**2026-11-26.** Write-up: `docs/research/kronos-install-speed.md`. Code: `spikes/kronos/`.
- **Kronos-small, N = 30, runs at 8.6 Forecasts/s** on the GTX 1650 (2.1 GB VRAM). A 12-symbol cycle takes 1.4 s, and the full Edge test ≈1.7 days. **Base runs at 3.6/s (≈4 days, over budget)**, so the Edge test uses **small, N = 30**.
- The vendor loop is 68× slower (no KV cache, context re-run per path), averages the paths, and leaves dropout on. Our sampler returns every path, is bit-identical to the reference loop, and is reproducible independently of batching.
- Kronos forecasts reversion toward the window mean even on a pure random walk. The Edge test adds a "revert to the 400-bar mean" baseline for this.
