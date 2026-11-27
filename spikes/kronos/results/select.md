# Edge test: select

Forecasts: `results/forecasts/small_n30`. Window: 2010-01-01 → 2020-01-01.

## In-sample grid (base costs)

| P_MIN | MOVE_MIN | result |
|---|---|---|
| 0.55 | 0.25 | n=45666, win 0.408, mean -0.126 R [-0.145, -0.107], p(≤0) 1.000, PF 0.79, max DD 5800.7 R |
| 0.55 | 0.5 | n=42862, win 0.378, mean -0.130 R [-0.150, -0.110], p(≤0) 1.000, PF 0.80, max DD 5593.6 R |
| 0.55 | 1.0 | n=38707, win 0.336, mean -0.134 R [-0.156, -0.112], p(≤0) 1.000, PF 0.80, max DD 5230.0 R |
| 0.6 | 0.25 | n=45458, win 0.406, mean -0.126 R [-0.145, -0.107], p(≤0) 1.000, PF 0.79, max DD 5777.5 R |
| 0.6 | 0.5 | n=42822, win 0.378, mean -0.129 R [-0.149, -0.109], p(≤0) 1.000, PF 0.80, max DD 5576.4 R |
| 0.6 | 1.0 | n=38700, win 0.336, mean -0.134 R [-0.156, -0.112], p(≤0) 1.000, PF 0.80, max DD 5232.0 R |
| 0.65 | 0.25 | n=44437, win 0.396, mean -0.127 R [-0.146, -0.107], p(≤0) 1.000, PF 0.80, max DD 5672.4 R |
| 0.65 | 0.5 | n=42467, win 0.374, mean -0.130 R [-0.149, -0.109], p(≤0) 1.000, PF 0.80, max DD 5537.0 R |
| 0.65 | 1.0 | n=38642, win 0.336, mean -0.134 R [-0.156, -0.112], p(≤0) 1.000, PF 0.80, max DD 5221.3 R |
| 0.7 | 0.25 | n=43723, win 0.388, mean -0.127 R [-0.146, -0.107], p(≤0) 1.000, PF 0.80, max DD 5584.1 R |
| 0.7 | 0.5 | n=42159, win 0.371, mean -0.129 R [-0.149, -0.109], p(≤0) 1.000, PF 0.80, max DD 5479.4 R |
| 0.7 | 1.0 | n=38572, win 0.335, mean -0.135 R [-0.156, -0.113], p(≤0) 1.000, PF 0.80, max DD 5229.8 R |

**Selected set: P_MIN 0.55, MOVE_MIN 0.25** (n=45666, win 0.408, mean -0.126 R [-0.145, -0.107], p(≤0) 1.000, PF 0.79, max DD 5800.7 R).
PBO (CSCV over 10 yearly blocks × 12 sets): 0.000
Deflated Sharpe (per trade, 12 trials): SR -0.083, SR0 0.001, DSR 0.000

## Feature tests (in-sample, selected set, median split, Holm over 6)

| feature | mean R above − below | p | Holm p |
|---|---|---|---|
| p_edge | -0.053 | 0.000 | 0.000 |
| move_abs | -0.027 | 0.057 | 0.146 |
| dispersion_atr | +0.039 | 0.006 | 0.024 |
| sl_atr | +0.087 | 0.000 | 0.000 |
| atr_pctile | -0.028 | 0.049 | 0.146 |
| hour | -0.002 | 0.915 | 0.915 |
