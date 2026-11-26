# Kronos training data and cutoff

Type: research
Status: resolved
Blocked by:

## Question

What data was Kronos pretrained on (markets, timeframes, and whether FX and gold H1 are included), and what is its **last training date** for each released model (mini, small, base)? From the paper (arXiv 2508.02739), the repo and the Hugging Face model cards. This sets the earliest bar that can count as out-of-sample. Also record the paper's reported forecasting benchmarks and any results on FX or trading.

## Answer

- **Cutoff to assume: bars before 2025-07-01 may have been seen in training, for every released model.**
  - The paper (App. D) says pretraining data "extends up to June 2024" and its tests start July 2024.
  - The lead author says train runs through Feb 2024, validation Mar–May 2024, OOS from Jun 2024 (GitHub issue #40).
  - The HF weights were uploaded 2025-06-30 (small/base) and 2025-07-01 (mini) and have never been replaced. Nobody has confirmed they are the paper checkpoints.
  - Kronos-mini isn't in the paper at all.
  - A window from 2024-07 to 2025-06 is only "paper-claimed OOS".
- **FX H1 was in pretraining**: 1,023 FX pairs at 5m/15m/30m/H1/D/W from 2020-01-31, 462M bars, upweighted in training (Table 13, App. C).
- **Gold is not named anywhere.** The futures data is China-only with no H1. Treat XAUUSD H1 as probably out-of-distribution.
- Benchmarks are zero-shot from July 2024, averaged over 5m–daily. Kronos's Forex price/return IC is about 0.02–0.05, ahead of the baselines. The only trading backtest is A-share daily (CSI300/800), with no FX or crypto trading result.
- Normalization: per-window z-score using the lookback window's own mean/std, then clip to ±5.
- Paper forecasting sampling: T=0.6, top_p=0.9, 10 samples averaged.

Full write-up with citations: [`docs/research/kronos-training-data.md`](../../../docs/research/kronos-training-data.md)
