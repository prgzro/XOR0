"""Edge test, stage 2: Candidates, trades and the pre-registered statistics from saved Forecasts.

    uv run python scripts/evaluate.py --forecasts results/forecasts/small_n30 --stage select
    uv run python scripts/evaluate.py --forecasts ... --stage contamination --set 0.60,0.5
    uv run python scripts/evaluate.py --forecasts ... --stage oos --set 0.60,0.5

select:        in-sample 2010-2019, the 12-set grid, the selection rule, PBO, the feature tests.
contamination: 2020-01-01 -> 2025-06-30 with the selected set (reported only).
oos:           2025-07-01 -> end, the selected set: the verdict, baselines, sensitivities,
               calibration, Monte Carlo and the monthly target check.
Writes results/<stage>.md and results/<stage>_trades.parquet.
"""

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from spike.data import MAJORS, load  # noqa: E402
from spike.stats import (deflated_sharpe, holm, monte_carlo, monthly_returns, pbo_cscv,  # noqa: E402
                         summary)
from spike.strategy import Bars, ForecastStats, candidate_direction, cost_atr, simulate  # noqa: E402

P_MINS = [0.55, 0.60, 0.65, 0.70]
MOVE_MINS = [0.25, 0.5, 1.0]
GRID = [(p, m) for p in P_MINS for m in MOVE_MINS]
WINDOWS = {
    "select": ("2010-01-01", "2020-01-01"),
    "contamination": ("2020-01-01", "2025-07-01"),
    "oos": ("2025-07-01", "2100-01-01"),
}
# XM fixed spreads in points (docs/research/edge-revalidation.md), for the XM-spread sensitivity.
XM_POINTS = {"EURUSD": 24, "GBPUSD": 28, "USDJPY": 31, "USDCHF": 32, "AUDUSD": 27, "USDCAD": 35,
             "NZDUSD": 35, "EURGBP": 28, "EURJPY": 37, "GBPJPY": 47, "EURCHF": 40, "XAUUSD": 77}
FEATURES = ["p_edge", "move_abs", "dispersion_atr", "sl_atr", "atr_pctile", "hour"]


def point(sym):
    return 0.01 if sym == "XAUUSD" else (0.001 if sym.endswith("JPY") else 0.00001)


def xm_spread_bars(b: Bars, sym: str) -> Bars:
    half = XM_POINTS[sym] * point(sym) / 2
    m = b.mid
    return replace(b, bid=m - half, ask=m + half)


def load_forecasts(fdir: Path, sym: str, lo, hi) -> pd.DataFrame:
    files = sorted(fdir.glob(f"{sym}_*.parquet"))
    if not files:
        return pd.DataFrame()
    df = pd.concat(pd.read_parquet(f) for f in files)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    return df[(df["ts"] >= lo) & (df["ts"] < hi)].sort_values("ts").reset_index(drop=True)


def stats_row(r) -> ForecastStats:
    return ForecastStats(r.p_up, (r.median_close - r.last_close) / r.atr, r.sl_long, r.sl_short,
                         r.median_close, (r.q90_close - r.q10_close) / r.atr)


def run_symbol(sym, bars, fc, p_min, move_min, tp_first=False, slip_ticks=1, financing=True,
               direction_fn=None, geometry=None):
    """Sequential walk: one open position per symbol. direction_fn(t, fs) overrides Kronos's
    direction (baselines); geometry maps this symbol's Kronos entry ts -> (risk, reward)
    distances to mirror."""
    pos = {ts: i for i, ts in enumerate(bars.ts)}
    out, busy_until = [], -1
    for r in fc.itertuples(index=False):
        t = pos.get(r.ts)
        if t is None:
            continue
        if direction_fn is not None:
            if r.ts not in geometry:  # baselines trade exactly the Kronos entry bars
                continue
        elif t <= busy_until:
            continue
        fs = stats_row(r)
        cost = cost_atr(bars, t, r.atr)
        d = candidate_direction(fs, cost, p_min, move_min) if direction_fn is None else 1
        if d == 0:
            continue
        if direction_fn is not None:
            d = direction_fn(t, fs)
            if d == 0:
                continue
            risk, reward = geometry[r.ts]
            entry_ref = bars.mid[t, 3]
            fs = replace(fs, sl_long=entry_ref - risk, sl_short=entry_ref + risk,
                         tp=entry_ref + d * reward)
        tr = simulate(bars, t, d, fs, r.atr, tp_first=tp_first, slip_ticks=slip_ticks)
        if tr is None:
            continue
        r_net = tr.r_net
        if not financing:
            r_net += 0.5e-4 * tr.entry * tr.rollovers / abs(tr.entry - tr.sl)
        out.append({"symbol": sym, "ts": r.ts, "entry_ts": bars.ts[tr.entry_i],
                    "exit_ts": bars.ts[tr.exit_i] + pd.Timedelta(hours=1), "direction": d,
                    "reason": tr.reason, "r_gross": tr.r_gross, "r": r_net, "risk": abs(tr.entry - tr.sl),
                    "reward": abs(tr.tp - tr.entry), "p_edge": abs(fs.p_up - 0.5), "move_abs": abs(fs.move_atr),
                    "dispersion_atr": fs.dispersion_atr, "sl_atr": abs(tr.entry - tr.sl) / r.atr,
                    "hour": bars.ts[t].hour, "atr": r.atr})
        busy_until = tr.exit_i - 1  # a new Candidate may fire on the exit bar's close
    return out


def atr_percentile(df_trades, bars_by_sym):
    vals = []
    for row in df_trades.itertuples():
        b, atrs = bars_by_sym[row.symbol]
        i = b.ts.get_loc(row.ts)
        w = atrs[max(0, i - 399):i + 1]
        vals.append(float((w <= w[-1]).mean()))
    return vals


def trades_df(rows):
    df = pd.DataFrame(rows)
    if len(df):
        df = df.sort_values("entry_ts").reset_index(drop=True)
        df["day"] = df["entry_ts"].dt.floor("D")
    return df


def fmt(s):
    return (f"n={s['n']}, win {s['win_rate']:.3f}, mean {s['mean_r']:+.3f} R "
            f"[{s['ci_lo']:+.3f}, {s['ci_hi']:+.3f}], p(≤0) {s['p_le_0']:.3f}, PF {s['pf']:.2f}, "
            f"max DD {s['max_dd_r']:.1f} R") if s["n"] else "n=0"


def median_split(x):
    """D4: x > median; if ties leave a side empty, x >= median; None if still one-sided."""
    med = np.median(x)
    for hi in (x > med, x >= med):
        if 0 < hi.sum() < len(x):
            return hi
    return None


def feature_row(f, d, pv, ad):
    return f"| {f} | not testable (ties) | – | – |" if np.isnan(d) else f"| {f} | {d:+.3f} | {pv:.3f} | {ad:.3f} |"


def feature_tests(df):
    """Median split on each pre-registered feature: mean R above vs below the median.
    A feature that cannot be split (D4) reports d = nan, p = 1 ('not testable (ties)')."""
    res = []
    rng = np.random.default_rng(0)
    for f in FEATURES:
        x = df[f].to_numpy(float)
        hi = median_split(x)
        if hi is None:
            res.append((f, float("nan"), 1.0))
            continue
        d = df.r[hi].mean() - df.r[~hi].mean()
        r = df.r.to_numpy()
        perm = np.array([r[p].mean() - r[~p].mean() for p in (rng.permutation(hi) for _ in range(5000))])
        res.append((f, float(d), float((np.abs(perm) >= abs(d)).mean())))
    adj = holm([p for _, _, p in res])
    return [(f, d, p, a) for (f, d, p), a in zip(res, adj)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--forecasts", required=True)
    ap.add_argument("--stage", choices=list(WINDOWS), required=True)
    ap.add_argument("--set", default=None, help="p_min,move_min (contamination, oos)")
    ap.add_argument("--symbols", default=",".join(MAJORS))
    a = ap.parse_args()
    fdir = Path(a.forecasts)
    lo, hi = (pd.Timestamp(x, tz="UTC") for x in WINDOWS[a.stage])
    syms = a.symbols.split(",")
    bars, fcs = {}, {}
    from spike.strategy import wilder_atr
    for s in syms:
        b, _ = load(s)
        bars[s] = (b, wilder_atr(b.mid))
        fcs[s] = load_forecasts(fdir, s, lo, hi)
    lines = [f"# Edge test: {a.stage}", "", f"Forecasts: `{fdir}`. Window: {lo.date()} → {hi.date()}.", ""]
    out = ROOT / "results"
    out.mkdir(exist_ok=True)

    if a.stage == "select":
        table, per_set, yearly = [], {}, {}
        for p, m in GRID:
            rows = [x for s in syms for x in run_symbol(s, bars[s][0], fcs[s], p, m)]
            df = trades_df(rows)
            per_set[(p, m)] = df
            s_ = summary(df.r.to_numpy(), df.day.to_numpy()) if len(df) else {"n": 0}
            table.append((p, m, s_))
            yearly[(p, m)] = df.groupby(df.entry_ts.dt.year).r.mean() if len(df) else pd.Series(dtype=float)
        lines += ["## In-sample grid (base costs)", "", "| P_MIN | MOVE_MIN | result |", "|---|---|---|"]
        lines += [f"| {p} | {m} | {fmt(s_)} |" for p, m, s_ in table]
        eligible = [(p, m, s_) for p, m, s_ in table if s_["n"] >= 100]
        if not eligible:
            lines += ["", "**No set has ≥ 100 in-sample trades: no-go at selection.**"]
        else:
            p, m, best = max(eligible, key=lambda x: x[2]["mean_r"])
            lines += ["", f"**Selected set: P_MIN {p}, MOVE_MIN {m}** ({fmt(best)})."]
            years = sorted(set().union(*[set(v.index) for v in yearly.values()]))
            perf = np.array([[yearly[k].get(y, np.nan) for k in GRID] for y in years])
            lines += [f"PBO (CSCV over {len(years)} yearly blocks × {len(GRID)} sets): {pbo_cscv(perf):.3f}"]
            sharpes = np.array([per_set[k].r.mean() / per_set[k].r.std(ddof=1) for k in GRID if len(per_set[k]) > 2])
            ds = deflated_sharpe(per_set[(p, m)].r.to_numpy(), len(GRID), sharpes)
            lines += [f"Deflated Sharpe (per trade, {len(GRID)} trials): SR {ds['sharpe']:.3f}, "
                      f"SR0 {ds['sr0']:.3f}, DSR {ds['dsr']:.3f}"]
            df = per_set[(p, m)].copy()
            df["atr_pctile"] = atr_percentile(df, bars)
            lines += ["", "## Feature tests (in-sample, selected set, median split, Holm over 6)", "",
                      "| feature | mean R above − below | p | Holm p |", "|---|---|---|---|"]
            lines += [feature_row(*t) for t in feature_tests(df)]
            df.to_parquet(out / "select_trades.parquet")
            (out / "selected_set.json").write_text(json.dumps({"p_min": p, "move_min": m}))
    else:
        p, m = (float(x) for x in a.set.split(","))
        rows = [x for s in syms for x in run_symbol(s, bars[s][0], fcs[s], p, m)]
        df = trades_df(rows)
        if not len(df):
            lines += ["No trades."]
        else:
            df["atr_pctile"] = atr_percentile(df, bars)
            base = summary(df.r.to_numpy(), df.day.to_numpy())
            lines += [f"## Primary: pooled, base costs, set P_MIN {p}, MOVE_MIN {m}", "", fmt(base), ""]
            verdict_at = len(lines)  # the OOS verdict goes here once the revert baseline has run (D3)
            lines += ["## Secondary", "", f"- gross (no costs): {fmt(summary(df.r_gross.to_numpy(), df.day.to_numpy()))}"]
            for d, name in ((1, "long"), (-1, "short")):
                sub = df[df.direction == d]
                lines.append(f"- {name}: {fmt(summary(sub.r.to_numpy(), sub.day.to_numpy()))}")
            per = []
            for s in syms:
                sub = df[df.symbol == s]
                per.append((s, summary(sub.r.to_numpy(), sub.day.to_numpy()) if len(sub) else {"n": 0, "p_le_0": 1.0}))
            adj = holm([x[1]["p_le_0"] for x in per])
            lines += ["", "| symbol | result | Holm p |", "|---|---|---|"]
            lines += [f"| {s} | {fmt(r)} | {h:.3f} |" for (s, r), h in zip(per, adj)]

            # Sensitivities
            sens = {
                "TP first": [x for s in syms for x in run_symbol(s, bars[s][0], fcs[s], p, m, tp_first=True)],
                "2 ticks slippage": [x for s in syms for x in run_symbol(s, bars[s][0], fcs[s], p, m, slip_ticks=2)],
                "no financing": [x for s in syms for x in run_symbol(s, bars[s][0], fcs[s], p, m, financing=False)],
                "XM spread": [x for s in syms for x in run_symbol(s, xm_spread_bars(bars[s][0], s), fcs[s], p, m)],
            }
            lines += ["", "## Sensitivities", ""]
            for k, rws in sens.items():
                d_ = trades_df(rws)
                lines.append(f"- {k}: {fmt(summary(d_.r.to_numpy(), d_.day.to_numpy())) if len(d_) else 'n=0'}")

            # Baselines: same entry bars, same risk and reward distances, own direction.
            # Keyed by symbol, then ts: each baseline mirrors its own symbol's Kronos trades only.
            geom = {s: {r.ts: (r.risk, r.reward) for r in df[df.symbol == s].itertuples()} for s in syms}
            closes = {s: bars[s][0].mid[:, 3] for s in syms}
            lines += ["", "## Baselines (same entry bars, risk and reward distances, costs)", ""]
            d_rev = pd.DataFrame()
            for name, fn_factory in {
                "momentum": lambda s: (lambda t, fs: int(np.sign(closes[s][t] - closes[s][t - 24]))),
                "mean reversion": lambda s: (lambda t, fs: -int(np.sign(closes[s][t] - closes[s][t - 24]))),
                "revert to 400-bar mean": lambda s: (lambda t, fs: int(np.sign(closes[s][t - 399:t + 1].mean() - closes[s][t]))),
            }.items():
                rws = [x for s in syms for x in run_symbol(s, bars[s][0], fcs[s], p, m, direction_fn=fn_factory(s), geometry=geom[s])]
                d_ = trades_df(rws)
                lines.append(f"- {name}: {fmt(summary(d_.r.to_numpy(), d_.day.to_numpy())) if len(d_) else 'n=0'}")
                if name == "revert to 400-bar mean":
                    d_rev = d_
            # D3: Kronos must beat revert-to-400-bar-mean on the same (symbol, entry bar), paired.
            pair = (df.merge(d_rev[["symbol", "ts", "r"]], on=["symbol", "ts"], suffixes=("", "_rev"))
                    if len(d_rev) else df.iloc[:0].assign(r_rev=[]))
            vs_rev = summary((pair.r - pair.r_rev).to_numpy(), pair.day.to_numpy()) if len(pair) else {"n": 0}
            beats_rev = vs_rev["n"] > 0 and vs_rev["mean_r"] > 0 and vs_rev["ci_lo"] > 0
            lines.append(f"- Kronos − revert to 400-bar mean, paired on {vs_rev['n']} of {len(df)} trades: {fmt(vs_rev)}")
            if a.stage == "oos":
                go = base["n"] >= 100 and base["mean_r"] > 0 and base["ci_lo"] > 0
                verdict = ("INCONCLUSIVE (n < 100)" if base["n"] < 100 else
                           "NO-GO" if not go else
                           "GO" if beats_rev else "NO-GO (not better than revert-to-mean)")
                lines[verdict_at:verdict_at] = [f"**Verdict: {verdict}**", ""]
            rng = np.random.default_rng(7)
            means = []
            for _ in range(1000):
                rws = [x for s in syms for x in run_symbol(s, bars[s][0], fcs[s], p, m,
                                                             direction_fn=lambda t, fs: int(rng.choice([-1, 1])), geometry=geom[s])]
                means.append(np.mean([x["r"] for x in rws]) if rws else np.nan)
            means = np.array(means)
            lines.append(f"- random direction (1,000 repeats): mean of means {np.nanmean(means):+.3f} R, "
                         f"Kronos beats {np.mean(base['mean_r'] > means):.1%} of repeats")

            if a.stage == "oos":
                # Calibration on every Forecast.
                cal = []
                for s in syms:
                    b = bars[s][0]
                    pos = {ts: i for i, ts in enumerate(b.ts)}
                    for r in fcs[s].itertuples():
                        i = pos.get(r.ts)
                        if i is not None and i + 24 < len(b.ts):
                            cal.append((r.p_up, float(b.mid[i + 24, 3] > b.mid[i, 3])))
                cal = pd.DataFrame(cal, columns=["p", "up"])
                cal["dec"] = pd.qcut(cal.p.rank(method="first"), 10, labels=False)
                lines += ["", "## Calibration (every Forecast)", "",
                          f"Hit rate (p_up>0.5 → up): {((cal.p > 0.5) == (cal.up == 1)).mean():.4f} on {len(cal)} Forecasts. "
                          f"Brier {((cal.p - cal.up) ** 2).mean():.4f} vs 0.5-constant {((0.5 - cal.up) ** 2).mean():.4f}.", "",
                          "| decile | mean p_up | realised up | n |", "|---|---|---|---|"]
                for d, g in cal.groupby("dec"):
                    lines.append(f"| {d + 1} | {g.p.mean():.3f} | {g.up.mean():.3f} | {len(g)} |")

                # Feature confirmation
                lines += ["", "## Feature tests (out-of-sample, confirm only in-sample winners)", "",
                          "| feature | mean R above − below | p | Holm p |", "|---|---|---|---|"]
                lines += [feature_row(*t) for t in feature_tests(df)]

                # Monte Carlo and the monthly target check
                mc = monte_carlo(df.r.to_numpy(), df.entry_ts.to_numpy())
                mon = monthly_returns(df.r.to_numpy(), df.exit_ts)
                lines += ["", "## Target check (reported, never selected on)", "",
                          f"- Monthly return at 1% risk: median {mon.median():+.2%}, 5th pct {mon.quantile(0.05):+.2%}, "
                          f"P(month ≥ 2%) {(mon >= 0.02).mean():.2f} over {len(mon)} months.",
                          f"- Trades per month: {len(df) / max(len(mon), 1):.1f}.",
                          f"- Max DD (R): historical {mc['historical']:.1f}; block bootstrap median {mc['block']['median']:.1f}, "
                          f"p95 {mc['block']['p95']:.1f}, p99 {mc['block']['p99']:.1f}; simple p95 {mc['simple']['p95']:.1f}. "
                          f"Historical sits at the {mc['historical_pctile_block']:.0%} percentile of the block distribution."]
                per_month_r = df.r.sum() / max(len(mon), 1)
                if per_month_r > 0:
                    risk_needed = 0.02 / per_month_r
                    lines.append(f"- Risk per trade for a 2% average month: {risk_needed:.2%}, "
                                 f"with a p95 drawdown of about {risk_needed * mc['block']['p95']:.1%} of the account.")
                else:
                    lines.append("- Mean R ≤ 0: no risk level reaches the target.")
        df.to_parquet(out / f"{a.stage}_trades.parquet")
    (out / f"{a.stage}.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
