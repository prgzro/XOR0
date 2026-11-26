# Kronos training data, cutoff and benchmarks

Research for ticket `.scratch/kronos-jev/issues/01-kronos-training-cutoff.md`. Sources read on 2026-11-26: the full PDF of arXiv 2508.02739v1 (36 pages, including the appendix), the GitHub repo `shiyu-coder/Kronos` at commit `67b630e` (README, `model/kronos.py`, maintainer replies in issues), and the Hugging Face model cards plus the Hub API commit history for `NeoQuasar/Kronos-mini`, `Kronos-small`, `Kronos-base`, `Kronos-Tokenizer-base` and `Kronos-Tokenizer-2k`.

## TL;DR

- **Cutoff to assume: treat every bar before 2025-07-01 as possibly seen in training.** That is the safe bound for all three released models. The paper bound is earlier: bars from 2024-07-01 on are out-of-sample for the paper's small/base checkpoints. Nobody has confirmed that the Hugging Face weights are those checkpoints.
  - Paper: "The pre-training data for Kronos extends up to June 2024. Consequently, our test period for all tasks begins in July 2024" (App. D).
  - Lead author on GitHub (2025-08-29) gives a slightly different split: train through **Feb 2024** inclusive, validation **Mar–May 2024**, out-of-sample from **Jun 2024**.
  - The released weights were uploaded on **2025-06-30** (small, base, Tokenizer-base) and **2025-07-01** (mini, Tokenizer-2k). They have never been replaced. Every later commit only edits the README.
  - **Kronos-mini is not in the paper at all**, so no cutoff is stated for it. A user asking whether the HF weights match the June 2024 cutoff (issue #265, still open) has had no answer from a maintainer.
- **FX was in pretraining, including H1.** Table 13 lists a "Foreign Exchange" row with **1,023 pairs**, timeframes **5T, 15T, 30T, H, D, W**, 462.4M observations, starting **2020-01-31**. The paper doesn't name the FX data vendor. FX is about 3.8% of the 12.11B records, and it was upweighted during training.
- **Gold is not explicitly included.** Neither XAUUSD nor gold appears anywhere in the paper or the model cards. The only commodity-like row is "China / Future" (75 contracts, T/5T/15T/D, from 2010-01-01), which has **no H1**. Whether the 1,023 "FX pairs" include XAU is not stated. Treat gold H1 as **probably out-of-distribution** and unconfirmed either way.
- **Corpus:** 12.11B K-line records, 96,569 assets, 45 exchanges/venues. It covers stocks/ETFs, Binance crypto spot and perpetuals, FX, Chinese futures and stock indices. The frequencies run from 1-min to weekly. 1-hour bars are part of the corpus for the intraday exchanges, crypto and FX.
- **Benchmarks:** all evaluation starts July 2024. On Forex, averaged over 5min–daily, Kronos beats the full-shot baselines on price-series IC, and Kronos-base leads Forex return IC. On Forex volatility, Kronos has about half GARCH's MAE (0.0069–0.0097 vs 0.0185). The **only trading backtest** is Chinese A-shares daily (CSI300/CSI800, Qlib). There is **no FX or crypto trading result**.
- **Normalization:** each input window is z-scored per feature using that window's own mean/std, then clipped to **[−5, 5]** (`clip=5`). Forecasts are de-normalized with the same stats.
- **Sampling:** for forecasting, the paper used **T=0.6, top_p=0.9, N=10 samples** (averaged). For volatility it used T=0.9, top_p=0.9, N=1. The README/`predict()` defaults are T=1.0, top_p=0.9, sample_count=1.

## 1. Pretraining corpus

| Fact | Source |
|---|---|
| "over 12 billion K-line records from 45 global exchanges" | arXiv 2508.02739v1, Abstract |
| "Our dataset spans over 12 billion observations across 7 sampling frequencies, encompassing a broad spectrum of asset classes drawn from 45 global exchanges." | §3 "Model Pre-training → Dataset" |
| "aggregated from over 40 exchanges across more than 30 countries, comprising a diverse range of asset classes at multiple temporal frequencies (1-minute to weekly)" | App. B "Dataset Details" |
| Totals: **96,569 assets, 12.11B observations** | App. B, Table 13 "Approximate Totals" |
| Timeframe codes: "T (1-min), H (1-hour), D (1-day), W (1-week)" | Table 13 caption |
| The cleaning-filter table (Table 4) has per-frequency thresholds for 1min, 5min, 10min, 15min, 20min, 30min, 40min, **60min**, 2H, 4H, Daily, Weekly | App. B, Table 4 |
| "equities being more prevalent than cryptocurrencies, futures, and foreign exchange (forex) assets ... we increase the sampling weights for data from crypto, futures, and forex markets" | App. C "Pre-training Data Rebalancing" |
| Timestamps use "the local timezone of each exchange". Pre- and post-market bars may be "filtered out by our data cleaning pipeline" | Maintainer reply, https://github.com/shiyu-coder/Kronos/issues/88 |

Selected Table 13 rows (App. B):

| Venue | Asset types | Timeframes | # Assets | # Obs | Start |
|---|---|---|---|---|---|
| Binance | Crypto, Perpetual Swap | T, 5T, 15T, 30T, **H**, D, W | 997 | 1,237,002,843 | 2021-01-31 |
| (unnamed, "\\") | **Foreign Exchange** | 5T, 15T, 30T, **H**, D, W | **1,023** | 462,434,562 | 2020-01-31 |
| China | Future | T, 5T, 15T, D | 75 | 63,318,960 | 2010-01-01 |
| NASDAQ | Stock, ETF | T, 5T, 15T, 30T, H, D, W | 8,725 | 2,478,662,459 | 2000-01-01 |
| NYSE | Stock, ETF | T, 5T, 15T, 30T, H, D, W | 7,073 | 2,133,143,549 | 2000-01-01 |
| Shanghai SE | Stock, ETF | T, 5T, 15T, 30T, H, D, W | 3,064 | 1,967,996,343 | 1990-12-19 |
| Shenzhen SE | Stock, ETF | T, 5T, 15T, 30T, H, D, W | 3,519 | 1,754,519,331 | 1990-12-19 |
| America | Stock Index | 5T, 15T, 30T, H, D, W | 670 | 37,887,535 | 2020-01-31 |

Most other exchanges start on 2020-01-31. Table 13 gives start dates only. **It has no end-date column.**

**Gold.** A full-text search of the paper for "gold" finds only the CPU model ("Intel Xeon Gold 6330", App. C hardware). No XAU instrument is named. The futures row is China-only and has no H1 bars.

**Volume for FX/crypto.** In evaluation, "For cryptocurrency and forex assets, we intentionally exclude volume and amount fields, providing only the OHLC price series" (App. D, "Assets"). The paper doesn't say whether FX volume was present in pretraining.

## 2. Training date range and cutoff

| Fact | Source |
|---|---|
| "The pre-training data for Kronos extends up to June 2024. Consequently, our test period for all tasks begins in July 2024 to ensure a strict temporal separation between training and evaluation." | App. D, "Task Implementation Details → Forecasting Task Setup" |
| "The cut-off date for the training set is February 2024 (inclusive). The validation set spans from March to May 2024 (inclusive), and the out-of-sample period begins in June 2024." (lead author `shiyu-coder`, 2025-08-29) | https://github.com/shiyu-coder/Kronos/issues/40#issuecomment-3235620068 (repeated verbatim in https://github.com/shiyu-coder/Kronos/issues/14#issuecomment-3211317408) |
| Earliest data: 1990-12-19 (Shanghai/Shenzhen), 2000-01-01 (NASDAQ/NYSE). FX from 2020-01-31, Binance from 2021-01-31 | Table 13 |
| Paper submitted 2 Aug 2025 (v1 only) | https://arxiv.org/abs/2508.02739 |
| The paper's model family is small (24.7M), base (102.3M) and large (499.2M). **Mini is not mentioned** | §3 Table 1 |
| The README model zoo lists Kronos-mini (4.1M, Tokenizer-2k, context 2048), small (24.7M, 512), base (102.3M, 512), and large (499.2M, not released) | https://github.com/shiyu-coder/Kronos README, "Model Zoo" |
| Weight upload commits ("add model"): small 2025-06-30T16:44Z, base 2025-06-30T17:20Z, mini 2025-07-01T13:29Z. Later commits (2025-08-07, 08-17, 09-09) are all "Update README.md" / model-card edits. The repos hold only `config.json` + `model.safetensors` | `https://huggingface.co/api/models/NeoQuasar/<model>/commits/main` |
| No per-model cutoff appears on any HF model card | https://huggingface.co/NeoQuasar/Kronos-small (same text for mini/base) |
| An open question to maintainers asks whether the HF weights are "the same checkpoint family trained with that June 2024 cutoff". There is no maintainer reply | https://github.com/shiyu-coder/Kronos/issues/265 |

**What to assume.**
- The two primary statements agree that nothing after June 2024 was used for training or model selection in the paper. They disagree only on whether Mar–Jun 2024 was training, validation or test. Either way, bars up to 2024-06-30 influenced the paper checkpoints.
- The released weights date from 2025-06-30/07-01. No primary source says they are the paper checkpoints. Kronos-mini has no documented training run at all.
- Conservative rule: **OOS = bars from 2025-07-01 onward for all released models.** If a test window starts in 2024-07 … 2025-06, label it "paper-claimed OOS, unconfirmed for released weights".

## 3. Reported benchmarks

All five tasks are zero-shot for Kronos. The test period begins July 2024 (App. D). The paper doesn't give an explicit test end date.

**Headline numbers** (Abstract): "boosts price series forecasting RankIC by 93% over the leading TSFM and 87% over the best non-pre-trained baseline ... 9% lower MAE in volatility forecasting and a 22% improvement in generative fidelity".

**Forecasting setup** (App. D, Table 8; lookback → horizon):

| Frequency | 5min | 10min | 15min | 20min | 40min | **1-hour** | 2-hour | 4-hour | Daily |
|---|---|---|---|---|---|---|---|---|---|
| Lookback | 480 | 240 | 160 | 120 | 90 | **80** | 60 | 90 | 40 |
| Horizon | 96 | 48 | 32 | 24 | 24 | **12** | 12 | 18 | 12 |

Assets (App. D): stocks from 6 in-distribution exchanges (XSHG, XNAS, XJPX, XNSE, XKRX, XHKG) and 3 out-of-distribution ones (XIDX, XKLS, XTAI); "All spot trading pairs available on the Binance exchange"; and "over 1,000 foreign exchange pairs". All results are "for each asset, averaged over all tested frequencies" (App. F). **No per-frequency (e.g. H1-only) FX number is published.**

**Forex and crypto rows from the appendix tables** (Kronos small / base / large; one strong full-shot baseline for scale):

| Task (table) | Metric | Forex S / B / L | Crypto S / B / L | Example baseline (Forex) |
|---|---|---|---|---|
| Price series (Table 14) | IC | 0.0279 / 0.0292 / 0.0244 | 0.0247 / 0.0209 / 0.0211 | TimeXer 0.0124 |
| Price series (Table 14) | RankIC | 0.0177 / 0.0141 / 0.0137 | 0.0138 / 0.0135 / 0.0129 | TimeXer 0.0134 |
| Return (Table 16) | IC | 0.0398 / 0.0555 / 0.0441 | 0.0373 / 0.0376 / 0.0368 | TimeXer 0.0079 |
| Return (Table 16) | RankIC | 0.0289 / 0.0343 / 0.0274 | 0.0332 / 0.0336 / 0.0333 | TimeMixer 0.0322 |
| Realized vol (Table 18) | MAE ↓ | 0.0097 / 0.0074 / 0.0069 | 0.0147 / 0.0148 / 0.0145 | GARCH 0.0185, ARCH 0.0219 |
| Realized vol (Table 18) | R² | 0.1301 / 0.1235 / 0.1277 | 0.1772 / 0.2179 / 0.2658 | ARCH 0.1169, GARCH 0.1141 |

The tables are pdftotext extractions of the PDF. Each row label sits between its first and second metric lines (IC/RankIC, or MAE/R²). I checked the reading against the "Average" row: the mean of the per-asset Kronos-small MAEs is 0.0384, which matches the published average. These ICs are small in absolute terms (about 0.02–0.05).

**Synthetic K-line generation** (App. D): XSHG, XTAI, crypto and forex at 15-minute (lookback 120 → 96) and daily (96 → 35), 6,000 sequences each. Fidelity is scored with a discriminative score (LSTM classifier; 0.5 is best) and usefulness with TSTR IC/RankIC (Tables 20–21, Figs. 13–14).

**Trading / backtest** (App. D "Investment Simulation Setup", Table 10): "an investment simulation on the Chinese A-share market", daily Qlib data, top-k/drop-n long-only equal-weight portfolio, minimum 5-day hold. The signal is the H-day mean forecast close vs the current close. AER / IR on CSI300 and CSI800:

| Model | CSI300 AER | CSI300 IR | CSI800 AER | CSI800 IR |
|---|---|---|---|---|
| Kronos-small | 0.1805 | 1.2394 | 0.1772 | 1.6050 |
| Kronos-base | 0.1911 | 1.3782 | 0.1867 | 1.6652 |
| Kronos-large | 0.2193 | 1.4177 | 0.1974 | 1.8805 |
| Moment-large (best baseline avg.) | 0.1655 | 1.1993 | 0.1707 | 1.5361 |

**There is no FX, gold or crypto trading backtest, and no intraday backtest.**

## 4. Limitations, normalization and sampling

**Normalization**
- Paper: "we apply z-score normalization independently to each of the D feature dimensions (e.g., Open, High, Low, Close, Volume and Amount). Second, to mitigate the potential impact of extreme outliers on training stability, the normalized values are clipped to the range [−5, 5]." (App. C "Input Preprocessing")
- Code, `KronosPredictor.predict()` (https://github.com/shiyu-coder/Kronos/blob/67b630e67f6a18c9e9be918d9b4337c960db1e9a/model/kronos.py, lines 544–556):
  - `x_mean, x_std = np.mean(x, axis=0), np.std(x, axis=0)` is computed over the **whole lookback window you pass**.
  - Then `x = (x - x_mean) / (x_std + 1e-5)` and `x = np.clip(x, -self.clip, self.clip)` with default `clip=5` (constructor, line 484).
  - Predictions are de-normalized with `preds * (x_std + 1e-5) + x_mean`.
  - So `clip` caps any input value more than 5 window-standard-deviations from the window mean. It is a per-window outlier cap, not a price limit.
- If `volume` is missing, volume and amount are filled with 0. If only volume is given, `amount = volume × mean(OHLC)` (lines 527–532). Required columns: `open, high, low, close` (README "Prepare Input Data").
- Context: "The `max_context` for `Kronos-small` and `Kronos-base` is **512** ... The `KronosPredictor` will automatically handle truncation for longer contexts." Mini's context is 2048. (README "Making Forecasts", "Model Zoo")
- `sample_count` paths are generated and **averaged** (`np.mean(preds, axis=1)`, line 467). The default `predict()` therefore returns a mean path, not quantiles.

**Sampling settings**

| Task | T | top_p | N samples | Source |
|---|---|---|---|---|
| Price series forecasting | 0.6 | 0.90 | 10 | App. C, Table 6 |
| Return forecasting | 0.6 | 0.90 | 10 | Table 6 |
| Realized volatility | 0.9 | 0.90 | 1 | Table 6 |
| Synthetic generation | 1.0 | 0.95 | 1 | Table 6 |
| Investment simulation | 0.6 | 0.90 | 10 | Table 6 |
| README / `predict()` default | 1.0 | 0.9 | 1 | README; `kronos.py` line 519 |

- Sensitivity (App. E): "forecasting tasks (price and return), which demand precision, lower temperatures" work best. Volatility and generation prefer temperatures "closer to 1.0".
- "temperature scaling generally offers more effective and nuanced control" than top-p.
- Averaging Monte Carlo rollouts "consistently improves forecast quality" (§3 "Inference").

**Stated limitations** (first-party)
- README fine-tuning disclaimer: "a simplified example and not a production-ready quantitative trading system. A robust quantitative strategy requires more sophisticated techniques, such as portfolio optimization and risk factor neutralization".
- The paper has no limitations section. Its conclusion (§5) states only strengths.
- The training data is not released (issue #100 "release training data"; https://github.com/shiyu-coder/Kronos/issues/265, comment of 2026-04-16).

**Third-party reports, open and unconfirmed by maintainers** (worth testing before we trust outputs):
- https://github.com/shiyu-coder/Kronos/issues/422: daily forecasts are pulled toward the input-window mean. On drifted random walks, Kronos-small predicted −10.4% where +2.1% was expected. The report links this to normalization that used future bars in the fine-tune code (see #84).
- https://github.com/shiyu-coder/Kronos/issues/415: with `huggingface_hub` < 2.0 (requirements pin 0.33.1), `from_pretrained` leaves the models in training mode, so dropout stays active at inference. The fix is to call `.eval()` on the tokenizer and model.
- https://github.com/shiyu-coder/Kronos/issues/354: Kronos-mini lost to a persistence baseline on AAPL daily from 2024-07 to 2026-07.
