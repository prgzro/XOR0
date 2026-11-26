"""Fast (KV-cached) sampler vs the reference sampler: same paths? how much faster?"""
import sys, time
from dataclasses import replace
from pathlib import Path
import numpy as np, torch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from spike.kronos_paths import SamplerConfig, load, sample_paths, sample_paths_fast
from scripts.bench import synthetic_windows

model = sys.argv[1] if len(sys.argv) > 1 else "small"
items = int(sys.argv[2]) if len(sys.argv) > 2 else 2
cfg = replace(SamplerConfig(), model=model, n_paths=30)
tok, mdl, ctx = load(model, "cuda")
ws, xt, yt = synthetic_windows(items, cfg.lookback, seed=5)
keys = [f"S{i}|t" for i in range(items)]
def timed(f):
    torch.cuda.synchronize(); t0 = time.perf_counter(); o = f(tok, mdl, ctx, ws, xt, yt, keys, cfg); torch.cuda.synchronize()
    return o, time.perf_counter() - t0
sample_paths_fast(tok, mdl, ctx, ws[:1], xt[:1], yt[:1], keys[:1], replace(cfg, n_paths=2))
ref, tr = timed(sample_paths)
fast, tf = timed(sample_paths_fast)
same = np.isclose(ref, fast, rtol=0, atol=1e-6 * np.abs(ref).max()).all(axis=(2, 3))
print(f"{model}: ref {tr:.2f}s, fast {tf:.2f}s ({tr / tf:.1f}x); identical paths {same.mean():.1%}; "
      f"max abs diff {np.abs(ref - fast).max():.3g}; p_up ref {(ref[:, :, -1, 3] > np.stack(ws)[:, None, -1, 3]).mean():.3f} "
      f"fast {(fast[:, :, -1, 3] > np.stack(ws)[:, None, -1, 3]).mean():.3f}")
