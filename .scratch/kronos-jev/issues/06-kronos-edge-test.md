# Does Kronos have a zero-shot edge on FX + gold H1?

Type: research
Status: open
Blocked by: 01, 02

## Question

The go/no-go for v2 (plan §8). Pre-register the model size, N, H, sampling, the Candidate rule (`p_up`/`move` thresholds), the SL/TP rule, costs and the split, and write them down before any out-of-sample run. Out-of-sample = only bars after Kronos's training cutoff (ticket 01). Run a walk-forward on the XM H1 history for 12 symbols. Report directional hit rate and calibration, strategy mean R with a CI, PF, max DD and per-symbol results with multiple-comparison correction, against random-entry and momentum baselines. Also report whether any Forecast feature separates winners from losers out-of-sample, which is what Jev could use.

**Inputs from ticket 01:** the true out-of-sample window is **2025-07-01 → 2026-11** only (~17 months H1 × 12 symbols). Earlier bars may be in training, so use them only for choosing thresholds, and expect them to look flattering. Run inference with `model.eval()`, and check that Kronos is doing more than drifting back toward the window mean (compare against a mean-reversion baseline). Report gold separately, since it's the one symbol probably not seen in training.

**Costs from ticket 03 (IBKR):** commission 0.20 bp of notional with a USD 2 minimum per order, charged on entry and exit. Assume orders under USD 25k (IDEAL odd lots) get an extra ~1.5 bp of slippage. Spread comes from the XM measurements, padded. For gold, assume 1.5 bp with a USD 2 minimum (spot) as the base case. Express everything in R. **Account: USD 1,000,000 paper, 1% risk per trade** (user, 2026-11-26). Positions are then far above USD 25k, so they go to IDEALPRO: commission 0.20 bp, the USD 2 minimum rarely binds, and no odd-lot penalty applies. Gold is **spot XAUUSD** (the user is resident in Egypt, which isn't on the exclusion list).

**Inputs from ticket 05:** IBKR quotes are tighter than XM's (EURUSD 0.3 pip vs XM ~2 pip at rollover). Base the spread cost on IBKR snapshots, padded, and show XM-level spread as a sensitivity. XM H1 bars are bid, 1.1 pip below the IBKR mid. Convert XM time (UTC+2/+3) to UTC. IBKR MIDPOINT H1 history (to 2005) can replace or confirm the XM data.
