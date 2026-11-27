"""Authenticity audit, step 1 (lookahead): truncation and future-corruption tests.

    uv run python scripts/audit_lookahead.py --model small --paths 30 --symbol EURUSD \
        --from 2015-03-02 --cutoff 2015-03-16 --to 2015-03-30

Runs the Forecast stage three times on [from, to):
  full      on the real data;
  truncated on data with every bar at or after the cutoff removed;
  corrupted on data with every bar at or after the cutoff replaced by random garbage.
Pass: every Forecast with ts < cutoff is identical (all statistics) in all three runs, and
the Candidate decisions (direction on each bar, for every grid set) are identical too.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from spike.data import DATA, load  # noqa: E402
from spike.strategy import ForecastStats, candidate_direction, cost_atr  # noqa: E402

GRID = [(p, m) for p in (0.55, 0.60, 0.65, 0.70) for m in (0.25, 0.5, 1.0)]


def variant(src: Path, dst: Path, sym: str, cutoff, mode: str):
    dst.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(123)
    for s in ("MIDPOINT", "BID", "ASK"):
        df = pd.read_parquet(src / f"{sym}_{s}.parquet")
        after = df["ts"] >= cutoff
        if mode == "truncated":
            df = df[~after]
        elif mode == "corrupted":
            k = int(after.sum())
            base = rng.uniform(0.5, 2.0, k) * df.loc[after, "close"].to_numpy()
            df.loc[after, "open"] = base
            df.loc[after, "close"] = base * rng.uniform(0.98, 1.02, k)
            df.loc[after, "high"] = np.maximum(df.loc[after, "open"], df.loc[after, "close"]) * 1.01
            df.loc[after, "low"] = np.minimum(df.loc[after, "open"], df.loc[after, "close"]) * 0.99
        df.to_parquet(dst / f"{sym}_{s}.parquet", index=False)


def forecasts(args, data_dir, out_dir):
    cmd = [sys.executable, str(ROOT / "scripts/run_forecasts.py"), "--model", args.model, "--paths",
           str(args.paths), "--symbols", args.symbol, "--from", args.start, "--to", args.end,
           "--out", str(out_dir), "--data-dir", str(data_dir), "--device", args.device]
    subprocess.run(cmd, check=True)
    return pd.concat(pd.read_parquet(f) for f in sorted(out_dir.glob("*.parquet"))).reset_index(drop=True)


def decisions(fc, data_dir, sym):
    bars, _ = load(sym, data_dir)
    pos = {ts: i for i, ts in enumerate(bars.ts)}
    out = []
    for r in fc.itertuples():
        t = pos[pd.Timestamp(r.ts)]
        fs = ForecastStats(r.p_up, (r.median_close - r.last_close) / r.atr, r.sl_long, r.sl_short,
                           r.median_close, (r.q90_close - r.q10_close) / r.atr)
        c = cost_atr(bars, t, r.atr)
        out.append(tuple(candidate_direction(fs, c, p, m) for p, m in GRID))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="small")
    ap.add_argument("--paths", type=int, default=30)
    ap.add_argument("--symbol", default="EURUSD")
    ap.add_argument("--from", dest="start", default="2015-03-02")
    ap.add_argument("--cutoff", default="2015-03-16")
    ap.add_argument("--to", dest="end", default="2015-03-30")
    ap.add_argument("--device", default="cuda")
    a = ap.parse_args()
    cutoff = pd.Timestamp(a.cutoff, tz="UTC")
    tmp = Path(tempfile.mkdtemp(prefix="audit_", dir=ROOT / "results"))
    try:
        runs = {}
        for mode in ("full", "truncated", "corrupted"):
            d = tmp / f"data_{mode}"
            variant(DATA, d, a.symbol, cutoff, mode)
            fc = forecasts(a, d, tmp / f"fc_{mode}")
            fc["ts"] = pd.to_datetime(fc["ts"], utc=True)
            fc = fc[fc["ts"] < cutoff].reset_index(drop=True)
            runs[mode] = (fc, decisions(fc, d, a.symbol))
        full_fc, full_dec = runs["full"]
        report = [f"Lookahead audit: {a.symbol}, {a.model} N={a.paths}, Forecasts {a.start} → {a.cutoff} "
                  f"(cutoff), data to {a.end}. {len(full_fc)} Forecasts before the cutoff."]
        ok = True
        for mode in ("truncated", "corrupted"):
            fc, dec = runs[mode]
            common = np.intersect1d(fc["ts"].to_numpy(), full_fc["ts"].to_numpy())
            # Truncation legitimately drops the last pre-cutoff bar (it has no next bar to trade on).
            missing = len(full_fc) - len(common)
            same_rows = missing <= (1 if mode == "truncated" else 0) and len(common) == len(fc)
            a_ = full_fc[full_fc["ts"].isin(common)].reset_index(drop=True)
            b_ = fc[fc["ts"].isin(common)].reset_index(drop=True)
            cols = [c for c in full_fc.columns if c != "ts"]
            max_diff = float(np.abs(a_[cols].to_numpy() - b_[cols].to_numpy()).max())
            keep = full_fc["ts"].isin(common).to_numpy()
            dec_same = [d for d, k in zip(full_dec, keep) if k] == [d for d, k in zip(dec, fc["ts"].isin(common)) if k]
            passed = same_rows and max_diff == 0.0 and dec_same
            ok &= passed
            report.append(f"- {mode}: {len(common)} shared Forecast bars ({missing} missing), max abs stat diff "
                          f"{max_diff:.3g}, decisions identical {dec_same} → {'PASS' if passed else 'FAIL'}")
        report.append(f"Overall: {'PASS' if ok else 'FAIL'}")
        print("\n".join(report))
        with open(ROOT / "results" / "audit_lookahead.md", "a") as f:
            f.write("\n".join(report) + "\n\n")
        sys.exit(0 if ok else 1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
