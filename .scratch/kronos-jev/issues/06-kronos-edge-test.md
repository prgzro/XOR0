# Does Kronos have a zero-shot edge on FX + gold H1?

Type: research
Status: open
Blocked by: 01, 02

## Question

The go/no-go for v2 (plan §8). Pre-register the model size, N, H, sampling, the Candidate rule (`p_up`/`move` thresholds), the SL/TP rule, costs and the split, and write them down before any out-of-sample run. Out-of-sample = only bars after Kronos's training cutoff (ticket 01). Run a walk-forward on IBKR H1 history (MIDPOINT into Kronos, BID/ASK for fills) for 12 symbols; XM H1 is a cross-check only. Report directional hit rate and calibration, strategy mean R with a CI, PF, max DD and per-symbol results with multiple-comparison correction, against random-entry and momentum baselines. Also report whether any Forecast feature separates winners from losers out-of-sample, which is what Jev could use.

**Inputs from ticket 01:** the true out-of-sample window is **2025-07-01 → 2026-11** only (~17 months H1 × 12 symbols). Earlier bars may be in training, so use them only for choosing thresholds, and expect them to look flattering. Run inference with `model.eval()`, and check that Kronos is doing more than drifting back toward the window mean (compare against a mean-reversion baseline). Report gold separately, since it's the one symbol probably not seen in training.

**Costs from ticket 03 (IBKR):** commission 0.20 bp of notional with a USD 2 minimum per order, charged on entry and exit. Assume orders under USD 25k (IDEAL odd lots) get an extra ~1.5 bp of slippage. Spread comes from the XM measurements, padded. For gold, assume 1.5 bp with a USD 2 minimum (spot) as the base case. Express everything in R. **Account: USD 1,000,000 paper, 1% risk per trade** (user, 2026-11-26). Positions are then far above USD 25k, so they go to IDEALPRO: commission 0.20 bp, the USD 2 minimum rarely binds, and no odd-lot penalty applies. Gold is **spot XAUUSD** (the user is resident in Egypt, which isn't on the exclusion list).

**Inputs from ticket 05:** IBKR quotes are tighter than XM's (EURUSD 0.3 pip vs XM ~2 pip at rollover). Base the spread cost on IBKR snapshots, padded, and show XM-level spread as a sensitivity. XM H1 bars are bid, 1.1 pip below the IBKR mid. Convert XM time (UTC+2/+3) to UTC. IBKR MIDPOINT H1 history (to 2005) can replace or confirm the XM data.

## Comments

**2026-11-26, pre-registration agreed in grilling (user: "yes to all").** Full rules: `docs/research/kronos-edge-test.md`. Supersedes the cost and data notes above where they differ:
- Data: IBKR MIDPOINT into Kronos, BID/ASK fills; XM cross-check only.
- Windows: select on 2010–2019 (before FX pretraining), report 2020 → 2025-06 as a contamination check, out-of-sample 2025-07-01 → the commit, run once.
- Spread comes from the historical bid/ask fills, so the padded IBKR snapshot spread is dropped. Added: 1 tick of slippage, 0.5 bp per rollover crossed.
- Verdict: Go needs mean R > 0, CI lower bound > 0 and n ≥ 100. n < 100 is inconclusive. Beating the baselines at ≤ 0 R is a no-go.
- User goal of 2–6%/month is reported as a target check, never selected on.
- Model size and N are still open: rule = largest model with N ≥ 30 whose full run fits ≈3 GPU-days, from ticket 02's numbers.

**2026-11-26, universe narrowed (user): the 7 FX majors only.** EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD; the crosses are out. Gold follows as its own test once the majors pass, with the frozen rules and set, pre-registered before any gold result. Decided before any result was seen. Expected time: in-sample ≈14 h, out-of-sample ≈2 h, contamination ≈7.5 h.
