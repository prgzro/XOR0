# Kronos install and speed on this machine (research)

Ticket: `.scratch/kronos-jev/issues/02-kronos-on-this-machine.md`. Code: `spikes/kronos/`. Date: 2026-11-26.

## TL;DR

- **Kronos-small, N = 30, runs at 8.6 Forecasts/s on the GTX 1650** (12 Forecasts per batch, 2.1 GB VRAM). That's **1.4 s for one 12-symbol bar-close cycle**, so live speed is no concern. The full Edge test (≈1.26M Forecasts, 2010 → 2026) takes **≈1.7 days**.
- **Kronos-base runs at 3.6 Forecasts/s** (batch 8 is the most that fits in 4 GB). The full run would take ≈4.0 days, which is over the pre-registered ≈3-day budget. Under the rule, **the Edge test uses Kronos-small, N = 30.**
- Mini runs at 12.6/s. CPU (16 cores) manages 1.3/s on small.
- **The vendor inference loop is ~68× slower than it needs to be.** It has no KV cache, and it recomputes the shared 400-bar context for every path at every step. Our sampler caches keys and values, prefills the context once per Forecast and shares it across the N paths. Its output is **bit-identical** to the reference loop (100% of paths, max abs diff 0).
- **Reproducible:** reruns are bit-identical. A Forecast's paths are also identical whatever else is in its batch, because sampling uses Gumbel-max noise from one seeded generator per (symbol, bar).
- **Behaviour to know about:** on pure random-walk input, Kronos still forecasts a confident move back toward the 400-bar window mean (`p_up` of 1.00 or 0.00). That's the "drift back to the mean" from ticket 01, now confirmed. It's why the Edge test adds a "revert to the 400-bar mean" baseline.

## Install

- Path: `spikes/kronos/`, its own uv venv, Python 3.12.7. Packages: torch 2.8.0+cu128, numpy 2.5.5, pandas 2.2.2, scipy 1.18.1, einops 0.8.1, huggingface_hub 0.33.1, safetensors 0.6.2 (`uv.lock`).
- GPU: GTX 1650, compute capability 7.5, driver 595.99.02. CUDA is available in torch.
- Kronos source: `github.com/shiyu-coder/Kronos` at commit `67b630e67f6a18c9e9be918d9b4337c960db1e9a`, cloned to `spikes/kronos/vendor-Kronos/` (gitignored, not modified).
- Weights, pinned by revision in `spike/kronos_paths.py`:
  - `NeoQuasar/Kronos-small`: revision `901c26c1…`, safetensors SHA-256 `b082dfcb…3e020`.
  - `NeoQuasar/Kronos-Tokenizer-base`: revision `0e011738…`, SHA-256 `59d85f6a…6bee`.
- Small's config: d_model 512, 8 layers, 8 heads, s1/s2 = 10 bits. Dropout is 0.25 on residuals and FFN and 0.1 on attention and tokens. **`KronosPredictor` never calls `eval()`**, so the vendor predictor runs with dropout on. Our loader always calls `eval()`.

## Three problems in the vendor inference path, and what we do instead

| vendor (`model/kronos.py`) | effect | ours (`spike/kronos_paths.py`) |
|---|---|---|
| `auto_regressive_inference` averages the `sample_count` paths (line 467) | the path distribution, and with it `p_up` and the quantiles, is lost | returns all N paths |
| no `eval()` in `KronosPredictor` | dropout active during inference | `eval()` on load |
| `torch.multinomial` on the global RNG | a path depends on the batch it's in, so the truncation test can't pass | Gumbel-max with per-Forecast seeded noise; same distribution |
| no KV cache; the full context is re-run for every path at every step | ~11 s per Forecast (small, N = 30) | KV cache plus a shared prefix: ~0.12 s; output bit-identical to the reference |

The fast path is exact only while lookback + H ≤ max_context (400 + 24 ≤ 512), because then there's no sliding window. That's asserted in the code.

Two more facts from the code:
- The s2 cross-attention applies RoPE at position 0 to its query and keys, which is the identity, so those keys can be cached without rotation.
- Normalisation is per window: mean and std over the lookback only, clipped at ±5, so it carries no lookahead.

## Speed (N = 30, lookback 400, H = 24, synthetic EURUSD-like input)

| model | device | Forecasts/batch | s per batch | Forecasts/s | peak VRAM |
|---|---|--:|--:|--:|--:|
| small | cuda, vendor-style loop | 1 | 11.1 | 0.09 | 0.5 GB |
| small | cuda, vendor-style loop | 6 | 64.7 | 0.09 | 2.5 GB |
| mini | cuda, fast | 8 | 0.63 | 12.6 | 1.1 GB |
| small | cuda, fast | 8 | 1.09 | 7.3 | 1.4 GB |
| small | cuda, fast | 12 | 1.38 | **8.7** | 2.1 GB |
| small | cuda, fast | 16 | 1.88 | 8.5 | 2.8 GB |
| base | cuda, fast | 8 | 2.19 | 3.6 | 2.2 GB |
| base | cuda, fast, fp16 autocast | 8 | — | 0.9 | — (slower; only 51% of paths match fp32, rejected) |
| small | cpu, 16 threads, fast | 4 | 3.14 | 1.3 | — |

32 Forecasts per batch runs out of memory for every model, and so does base at 12. Real-data throughput in the lookahead audit was 7.7/s at batch 8.

## Cost of the Edge test

About 6,200 H1 bars per symbol-year:

| window | Forecasts | small @ 8.6/s | base @ 3.6/s |
|---|--:|--:|--:|
| in-sample 2010–2019 | ≈ 740k | 24 h | 57 h |
| contamination 2020 → 2025-06 | ≈ 410k | 13 h | 32 h |
| out-of-sample 2025-07 → 2026-11 | ≈ 105k | 3.4 h | 8 h |
| **total** | ≈ 1.26M | **≈ 1.7 days** | **≈ 4.0 days** |

## Checks

- **Lookahead audit (EURUSD, 2015-03-02 → 2015-03-16 cutoff, data to 03-30): PASS.**
  - Truncated data: 240 shared Forecasts, max stat diff 0, and all 12 grid sets' decisions identical. The 1 missing Forecast is the last pre-cutoff bar, which has no next bar to trade on.
  - Garbage after the cutoff: 241 Forecasts, max diff 0, decisions identical.
- **Future bar times** (`spike/calendar.py`): compared against real IBKR bars (3,000 random bars each for EURUSD and GBPUSD).
  - The next bar matches 100% of the time, and the full 24-bar sequence 98.9%.
  - The misses are holidays (Easter, Christmas, New Year). We accept these, since using the real calendar would leak the future.
