"""Pre-registered statistics for the Edge test (docs/research/kronos-edge-test.md)."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats as sps


def cluster_bootstrap_mean(r: np.ndarray, clusters: np.ndarray, reps: int = 5000, seed: int = 0):
    """Mean with a 95% CI from resampling whole clusters. Returns (mean, lo, hi, p(mean<=0))."""
    r = np.asarray(r, float)
    if len(r) == 0:
        return (np.nan,) * 4
    codes, uniq = pd.factorize(clusters)
    k = len(uniq)
    sums = np.bincount(codes, weights=r, minlength=k)
    cnts = np.bincount(codes, minlength=k)
    rng = np.random.default_rng(seed)
    draw = rng.integers(0, k, size=(reps, k))
    means = sums[draw].sum(1) / cnts[draw].sum(1)
    return float(r.mean()), float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975)), float((means <= 0).mean())


def profit_factor(r):
    w, l = r[r > 0].sum(), -r[r < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def max_drawdown(r):
    if len(r) == 0:
        return 0.0
    eq = np.cumsum(r)
    return float((np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max())


def holm(pvals):
    p = np.asarray(pvals, float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    m, run = len(p), 0.0
    for rank, i in enumerate(order):
        run = max(run, (m - rank) * p[i])
        adj[i] = min(1.0, run)
    return adj


def summary(r, clusters, seed=0):
    r = np.asarray(r, float)
    mean, lo, hi, p = cluster_bootstrap_mean(r, clusters, seed=seed)
    return {"n": int(len(r)), "win_rate": float((r > 0).mean()) if len(r) else np.nan, "mean_r": mean,
            "ci_lo": lo, "ci_hi": hi, "p_le_0": p, "pf": profit_factor(r) if len(r) else np.nan,
            "max_dd_r": max_drawdown(r)}


def deflated_sharpe(r: np.ndarray, n_trials: int, trial_sharpes: np.ndarray | None = None) -> dict:
    """Bailey & Lopez de Prado (2014), per-trade Sharpe. Variance of trial Sharpes from the
    trials if given, else the per-trade estimator variance."""
    r = np.asarray(r, float)
    n = len(r)
    if n < 3 or r.std(ddof=1) == 0:
        return {"sharpe": np.nan, "dsr": np.nan}
    sr = r.mean() / r.std(ddof=1)
    g3, g4 = sps.skew(r), sps.kurtosis(r, fisher=False)
    var_sr = np.var(trial_sharpes, ddof=1) if trial_sharpes is not None and len(trial_sharpes) > 1 else 1 / n
    e = 0.5772156649
    z = sps.norm.ppf
    sr0 = math.sqrt(var_sr) * ((1 - e) * z(1 - 1 / n_trials) + e * z(1 - 1 / (n_trials * math.e))) if n_trials > 1 else 0.0
    denom = math.sqrt(max(1e-12, 1 - g3 * sr + (g4 - 1) / 4 * sr**2))
    dsr = sps.norm.cdf((sr - sr0) * math.sqrt(n - 1) / denom)
    return {"sharpe": float(sr), "sr0": float(sr0), "dsr": float(dsr)}


def pbo_cscv(perf: np.ndarray) -> float:
    """Probability of backtest overfitting by CSCV. perf: (blocks, trials) mean R per block.
    Blocks are split into all half/half combinations; PBO = share where the in-sample-best
    trial ranks at or below the median out-of-sample."""
    from itertools import combinations

    s, n = perf.shape
    if s < 2 or n < 2:
        return np.nan
    logits = []
    for c in combinations(range(s), s // 2):
        ins = np.array(c)
        oos = np.setdiff1d(np.arange(s), ins)
        best = np.nanargmax(np.nanmean(perf[ins], 0))
        oos_perf = np.nanmean(perf[oos], 0)
        rank = (oos_perf < oos_perf[best]).sum() + 1
        w = rank / (n + 1)
        logits.append(math.log(w / (1 - w)))
    return float((np.array(logits) <= 0).mean())


def monte_carlo(r: np.ndarray, entry_days: np.ndarray, reps: int = 2000, block_days: int = 5, seed: int = 0):
    """Max-drawdown distribution (R) from simple and block-bootstrap resampled trade orders."""
    r = np.asarray(r, float)
    rng = np.random.default_rng(seed)
    simple = np.array([max_drawdown(rng.choice(r, len(r), replace=True)) for _ in range(reps)])
    days = pd.to_datetime(pd.Series(entry_days)).dt.floor("D")
    block = ((days - days.min()).dt.days // block_days).to_numpy()
    groups = [r[block == b] for b in np.unique(block)]
    blocked = []
    for _ in range(reps):
        seq, total = [], 0
        while total < len(r):
            g = groups[rng.integers(len(groups))]
            seq.append(g)
            total += len(g)
        blocked.append(max_drawdown(np.concatenate(seq)[: len(r)]))
    blocked = np.array(blocked)
    q = lambda a: {"median": float(np.median(a)), "p95": float(np.quantile(a, 0.95)), "p99": float(np.quantile(a, 0.99))}
    hist = max_drawdown(r)
    return {"historical": hist, "simple": q(simple), "block": q(blocked),
            "historical_pctile_block": float((blocked <= hist).mean())}


def monthly_returns(r: np.ndarray, exit_times: pd.Series, risk: float = 0.01) -> pd.Series:
    """Compounded monthly account return at a fixed fraction risked per trade."""
    s = pd.Series(np.asarray(r, float), index=pd.to_datetime(exit_times))
    return s.groupby(s.index.to_period("M")).apply(lambda x: float(np.prod(1 + risk * x) - 1))
