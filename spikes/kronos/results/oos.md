# Edge test: oos

Forecasts: `results/forecasts/small_n30_oos`. Window: 2025-07-01 → 2100-01-01.

## Primary: pooled, base costs, set P_MIN 0.55, MOVE_MIN 0.25

n=6813, win 0.398, mean -0.188 R [-0.243, -0.129], p(≤0) 1.000, PF 0.70, max DD 1331.6 R

**Verdict: NO-GO**

## Secondary

- gross (no costs): n=6813, win 0.400, mean -0.146 R [-0.200, -0.087], p(≤0) 1.000, PF 0.76, max DD 1053.3 R
- long: n=3712, win 0.400, mean -0.207 R [-0.269, -0.144], p(≤0) 1.000, PF 0.67, max DD 793.0 R
- short: n=3101, win 0.396, mean -0.167 R [-0.239, -0.090], p(≤0) 1.000, PF 0.74, max DD 560.8 R

| symbol | result | Holm p |
|---|---|---|
| EURUSD | n=1008, win 0.421, mean -0.170 R [-0.265, -0.067], p(≤0) 0.999, PF 0.72, max DD 214.6 R | 1.000 |
| GBPUSD | n=915, win 0.384, mean -0.185 R [-0.289, -0.077], p(≤0) 1.000, PF 0.72, max DD 183.1 R | 1.000 |
| USDJPY | n=1078, win 0.446, mean -0.045 R [-0.145, +0.060], p(≤0) 0.797, PF 0.92, max DD 106.2 R | 1.000 |
| USDCHF | n=1026, win 0.393, mean -0.208 R [-0.304, -0.102], p(≤0) 1.000, PF 0.68, max DD 225.0 R | 1.000 |
| AUDUSD | n=948, win 0.392, mean -0.193 R [-0.285, -0.101], p(≤0) 1.000, PF 0.70, max DD 203.2 R | 1.000 |
| USDCAD | n=985, win 0.379, mean -0.292 R [-0.381, -0.197], p(≤0) 1.000, PF 0.56, max DD 290.6 R | 1.000 |
| NZDUSD | n=853, win 0.362, mean -0.247 R [-0.338, -0.150], p(≤0) 1.000, PF 0.62, max DD 223.7 R | 1.000 |

## Sensitivities

- TP first: n=6813, win 0.401, mean -0.182 R [-0.236, -0.122], p(≤0) 1.000, PF 0.71, max DD 1284.9 R
- 2 ticks slippage: n=6825, win 0.395, mean -0.244 R [-0.298, -0.186], p(≤0) 1.000, PF 0.63, max DD 1704.9 R
- no financing: n=6813, win 0.400, mean -0.173 R [-0.228, -0.114], p(≤0) 1.000, PF 0.72, max DD 1233.2 R
- XM spread: n=6672, win 0.334, mean -0.316 R [-0.369, -0.260], p(≤0) 1.000, PF 0.55, max DD 2137.0 R

## Baselines (same entry bars, risk and reward distances, costs)

- momentum: n=6783, win 0.414, mean -0.189 R [-0.252, -0.124], p(≤0) 1.000, PF 0.70, max DD 1284.7 R
- mean reversion: n=6780, win 0.410, mean -0.173 R [-0.222, -0.119], p(≤0) 1.000, PF 0.72, max DD 1212.3 R
- revert to 400-bar mean: n=6802, win 0.415, mean -0.172 R [-0.225, -0.115], p(≤0) 1.000, PF 0.72, max DD 1224.3 R
- Kronos − revert to 400-bar mean, paired on 6802 of 6813 trades: n=6802, win 0.385, mean -0.016 R [-0.035, +0.003], p(≤0) 0.947, PF 0.88, max DD 129.3 R
- random direction (1,000 repeats): mean of means -0.179 R, Kronos beats 25.1% of repeats

## Calibration (every Forecast)

Hit rate (p_up>0.5 → up): 0.5083 on 61211 Forecasts. Brier 0.4352 vs 0.5-constant 0.2500.

| decile | mean p_up | realised up | n |
|---|---|---|---|
| 1 | 0.000 | 0.458 | 6122 |
| 2 | 0.000 | 0.530 | 6121 |
| 3 | 0.030 | 0.536 | 6121 |
| 4 | 0.265 | 0.504 | 6121 |
| 5 | 0.612 | 0.507 | 6121 |
| 6 | 0.873 | 0.529 | 6121 |
| 7 | 0.971 | 0.508 | 6121 |
| 8 | 1.000 | 0.523 | 6121 |
| 9 | 1.000 | 0.553 | 6121 |
| 10 | 1.000 | 0.486 | 6121 |

## Feature tests (out-of-sample, confirm only in-sample winners)

| feature | mean R above − below | p | Holm p |
|---|---|---|---|
| p_edge | -0.145 | 0.000 | 0.001 |
| move_abs | -0.094 | 0.011 | 0.044 |
| dispersion_atr | +0.073 | 0.044 | 0.098 |
| sl_atr | +0.170 | 0.000 | 0.000 |
| atr_pctile | +0.032 | 0.380 | 0.380 |
| hour | -0.079 | 0.033 | 0.098 |

## Target check (reported, never selected on)

- Monthly return at 1% risk: median -49.22%, 5th pct -81.29%, P(month ≥ 2%) 0.06 over 17 months.
- Trades per month: 400.8.
- Max DD (R): historical 1331.6; block bootstrap median 1298.0, p95 1656.0, p99 1821.6; simple p95 1490.8. Historical sits at the 57% percentile of the block distribution.
- Mean R ≤ 0: no risk level reaches the target.
