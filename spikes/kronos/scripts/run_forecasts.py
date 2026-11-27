"""Edge test, stage 1: Kronos Forecasts at every H1 close, saved as per-Forecast statistics.

    uv run python scripts/run_forecasts.py --model small --paths 30 --from 2010-01-01 --to 2020-01-01
    uv run python scripts/run_forecasts.py ... --from 2025-07-01 --unseal <pre-registration commit>

Output: results/forecasts/<model>_n<paths>/<SYMBOL>_<YYYY>.parquet, one row per Forecast bar t
(columns: ts, last_close, atr, p_up, median_close, sl_long, sl_short, q10_close, q90_close).
Resumable per (symbol, year). Batches are fixed: consecutive bars of one symbol in groups of
--batch, so a truncated rerun repeats identical batches.

The seal: any Forecast at or after 2025-07-01 needs --unseal with a commit hash that is an
ancestor of HEAD and whose docs/research/kronos-edge-test.md records that hash as the
pre-registration commit.
"""

import argparse
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from spike.data import OOS_START, SYMBOLS, load, session  # noqa: E402
from spike.kronos_paths import SamplerConfig, future_bar_times
from spike.kronos_paths import sample_paths_fast as sample_paths  # noqa: E402
from spike.kronos_paths import load as load_model  # noqa: E402
from spike.strategy import wilder_atr  # noqa: E402

REPO = ROOT.parents[1]


def check_seal(commit: str | None, to: pd.Timestamp):
    if to <= OOS_START:
        return
    if not commit:
        sys.exit("Refusing: the range reaches the sealed out-of-sample window (>= 2025-07-01). "
                 "Pass --unseal <pre-registration commit>.")
    ok = subprocess.run(["git", "-C", str(REPO), "merge-base", "--is-ancestor", commit, "HEAD"]).returncode == 0
    doc = subprocess.run(["git", "-C", str(REPO), "show", f"{commit}:docs/research/kronos-edge-test.md"],
                         capture_output=True, text=True).stdout
    head_doc = (REPO / "docs/research/kronos-edge-test.md").read_text()
    if not ok or "## Pre-registration" not in doc or commit[:7] not in head_doc:
        sys.exit("Refusing: the commit is not an ancestor of HEAD, has no pre-registration, "
                 "or is not recorded under 'Pre-registration commit'.")


def check_existing(path: Path, lo: pd.Timestamp, hi: pd.Timestamp):
    """Resume only a file from the same window; a file from another window (e.g. a contamination
    run's SYM_2025.parquet when the sealed run asks for 2025-07 onward) is an error, not a skip."""
    ts = pd.to_datetime(pd.read_parquet(path, columns=["ts"])["ts"], utc=True)
    if len(ts) and (ts.min() < lo or ts.max() >= hi):
        sys.exit(f"Refusing: {path} holds {ts.min()} .. {ts.max()}, outside the requested "
                 f"[{lo}, {hi}). Use a separate --out for each window.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="small")
    ap.add_argument("--paths", type=int, default=30)
    ap.add_argument("--from", dest="start", default="2010-01-01")
    ap.add_argument("--to", dest="end", default="2020-01-01")
    ap.add_argument("--symbols", default=",".join(SYMBOLS))
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--unseal", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--data-dir", default=None, help="override data/ibkr (audit only)")
    a = ap.parse_args()
    start, end = pd.Timestamp(a.start, tz="UTC"), pd.Timestamp(a.end, tz="UTC")
    check_seal(a.unseal, end)

    cfg = replace(SamplerConfig(), model=a.model, n_paths=a.paths)
    out_dir = Path(a.out) if a.out else ROOT / "results" / "forecasts" / f"{a.model}_n{a.paths}"
    out_dir.mkdir(parents=True, exist_ok=True)
    tok, mdl, ctx = load_model(a.model, a.device)

    for sym in a.symbols.split(","):
        bars, log = load(sym, Path(a.data_dir)) if a.data_dir else load(sym)
        for line in log:
            print("data:", line)
        atr = wilder_atr(bars.mid)
        for year in range(start.year, end.year + (1 if end > pd.Timestamp(f"{end.year}-01-01", tz="UTC") else 0)):
            path = out_dir / f"{sym}_{year}.parquet"
            lo = max(start, pd.Timestamp(f"{year}-01-01", tz="UTC"))
            hi = min(end, pd.Timestamp(f"{year + 1}-01-01", tz="UTC"))
            if path.exists():
                check_existing(path, lo, hi)
                continue
            ts = bars.ts
            idx = np.where((ts >= lo) & (ts < hi) & (np.arange(len(ts)) >= cfg.lookback - 1) & np.isfinite(atr))[0]
            idx = idx[idx + 1 < len(ts)]  # a Forecast needs a next bar to trade on
            rows, t0 = [], time.perf_counter()
            for b0 in range(0, len(idx), a.batch):
                ii = idx[b0:b0 + a.batch]
                ws = [bars.mid[i - cfg.lookback + 1:i + 1].astype(np.float32) for i in ii]
                xt = [ts[i - cfg.lookback + 1:i + 1] for i in ii]
                yt = [future_bar_times(ts[i], cfg.horizon, session(sym)) for i in ii]
                keys = [f"{sym}|{ts[i].isoformat()}" for i in ii]
                p = sample_paths(tok, mdl, ctx, ws, xt, yt, keys, cfg)
                for k, i in enumerate(ii):
                    close_h = p[k, :, -1, 3]
                    rows.append((ts[i], bars.mid[i, 3], atr[i], float((close_h > bars.mid[i, 3]).mean()),
                                 float(np.median(close_h)), float(np.quantile(p[k, :, :, 2].min(1), 0.10)),
                                 float(np.quantile(p[k, :, :, 1].max(1), 0.90)),
                                 float(np.quantile(close_h, 0.10)), float(np.quantile(close_h, 0.90))))
            df = pd.DataFrame(rows, columns=["ts", "last_close", "atr", "p_up", "median_close", "sl_long",
                                             "sl_short", "q10_close", "q90_close"])
            df.to_parquet(path, index=False)
            dt = time.perf_counter() - t0
            print(f"{sym} {year}: {len(df)} forecasts in {dt:.0f} s ({len(df) / max(dt, 1e-9):.2f}/s)", flush=True)
            if a.device == "cuda":
                torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
