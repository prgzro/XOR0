"""Ticket kronos-jev/02: Kronos speed, VRAM and reproducibility on this machine.

Usage: python scripts/bench.py --model small --device cuda --paths 30 --items 12
Times one bar-close cycle (items Forecasts x N paths x H=24, lookback 400), reports
peak VRAM, and checks the paths are identical (a) on a rerun and (b) when the same
Forecast is sampled inside a different batch.
"""

import argparse
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from spike.kronos_paths import SamplerConfig, future_bar_times, load
from spike.kronos_paths import sample_paths_fast as sample_paths  # noqa: E402


def synthetic_windows(items, lookback, seed=0):
    rng = np.random.default_rng(seed)
    end = pd.Timestamp("2025-07-01 12:00", tz="UTC")
    times = pd.date_range(end=end, periods=lookback, freq="h")
    ws = []
    for _ in range(items):
        c = 1.1 * np.exp(np.cumsum(rng.normal(0, 0.001, lookback)))
        o = np.r_[c[0], c[:-1]]
        hi = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.0005, lookback)))
        lo = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.0005, lookback)))
        ws.append(np.stack([o, hi, lo, c], 1).astype(np.float32))
    return ws, [times] * items, [future_bar_times(times[-1], 24)] * items


def run(tok, mdl, ctx, ws, xt, yt, keys, cfg, device):
    if device == "cuda":
        torch.cuda.synchronize()
    t0 = time.perf_counter()
    out = sample_paths(tok, mdl, ctx, ws, xt, yt, keys, cfg)
    if device == "cuda":
        torch.cuda.synchronize()
    return out, time.perf_counter() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="small")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--paths", type=int, default=30)
    ap.add_argument("--items", type=int, default=12)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--threads", type=int, default=16)
    a = ap.parse_args()
    torch.set_num_threads(a.threads)

    cfg = replace(SamplerConfig(), model=a.model, n_paths=a.paths)
    tok, mdl, ctx = load(a.model, a.device)
    ws, xt, yt = synthetic_windows(a.items, cfg.lookback)
    keys = [f"SYM{i}|2025-07-01T12:00Z" for i in range(a.items)]

    run(tok, mdl, ctx, ws[:1], xt[:1], yt[:1], keys[:1], replace(cfg, n_paths=2), a.device)  # warm-up
    if a.device == "cuda":
        torch.cuda.reset_peak_memory_stats()
    times, outs = [], []
    for _ in range(a.reps):
        o, dt = run(tok, mdl, ctx, ws, xt, yt, keys, cfg, a.device)
        times.append(dt)
        outs.append(o)
    vram = torch.cuda.max_memory_allocated() / 2**20 if a.device == "cuda" else None

    rerun_identical = all(np.array_equal(outs[0], o) for o in outs[1:])
    # Same Forecast (item 0) inside a different, smaller batch.
    solo, _ = run(tok, mdl, ctx, ws[:1], xt[:1], yt[:1], keys[:1], cfg, a.device)
    batch_max_abs = float(np.abs(solo[0] - outs[0][0]).max())

    res = {
        "model": a.model,
        "device": a.device,
        "items": a.items,
        "paths": a.paths,
        "seconds_per_cycle": round(float(np.median(times)), 3),
        "forecasts_per_second": round(a.items / float(np.median(times)), 3),
        "peak_vram_mib": round(vram, 1) if vram else None,
        "rerun_identical": rerun_identical,
        "batch_independent_max_abs_diff": batch_max_abs,
        "p_up_item0": float((outs[0][0, :, -1, 3] > ws[0][-1, 3]).mean()),
    }
    print(json.dumps(res))


if __name__ == "__main__":
    main()
