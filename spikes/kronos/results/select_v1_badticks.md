# Edge test: select

Forecasts: `results/forecasts/small_n30`. Window: 2010-01-01 → 2020-01-01.

## In-sample grid (base costs)

| P_MIN | MOVE_MIN | result |
|---|---|---|
| 0.55 | 0.25 | n=45727, win 0.407, mean +0.420 R [-0.146, +1.552], p(≤0) 0.369, PF 1.68, max DD 5038.2 R |
| 0.55 | 0.5 | n=42925, win 0.377, mean +0.899 R [-0.150, +3.005], p(≤0) 0.373, PF 2.40, max DD 4877.2 R |
| 0.55 | 1.0 | n=38767, win 0.335, mean +0.510 R [-0.157, +1.841], p(≤0) 0.362, PF 1.74, max DD 4629.2 R |
| 0.6 | 0.25 | n=45520, win 0.405, mean +0.422 R [-0.146, +1.551], p(≤0) 0.355, PF 1.69, max DD 5030.1 R |
| 0.6 | 0.5 | n=42885, win 0.376, mean +0.901 R [-0.150, +3.006], p(≤0) 0.366, PF 2.40, max DD 4864.3 R |
| 0.6 | 1.0 | n=38760, win 0.335, mean +0.510 R [-0.157, +1.833], p(≤0) 0.366, PF 1.74, max DD 4629.4 R |
| 0.65 | 0.25 | n=44502, win 0.394, mean +0.434 R [-0.147, +1.604], p(≤0) 0.373, PF 1.69, max DD 4949.9 R |
| 0.65 | 0.5 | n=42531, win 0.373, mean +0.909 R [-0.150, +3.049], p(≤0) 0.371, PF 2.40, max DD 4848.9 R |
| 0.65 | 1.0 | n=38702, win 0.334, mean +0.511 R [-0.157, +1.844], p(≤0) 0.362, PF 1.74, max DD 4625.7 R |
| 0.7 | 0.25 | n=43789, win 0.387, mean +0.443 R [-0.147, +1.625], p(≤0) 0.377, PF 1.70, max DD 4888.6 R |
| 0.7 | 0.5 | n=42226, win 0.370, mean +0.917 R [-0.150, +3.069], p(≤0) 0.362, PF 2.41, max DD 4805.2 R |
| 0.7 | 1.0 | n=38632, win 0.333, mean +0.512 R [-0.158, +1.848], p(≤0) 0.362, PF 1.74, max DD 4633.5 R |

**Selected set: P_MIN 0.7, MOVE_MIN 0.5** (n=42226, win 0.370, mean +0.917 R [-0.150, +3.069], p(≤0) 0.362, PF 2.41, max DD 4805.2 R).
PBO (CSCV over 10 yearly blocks × 12 sets): 0.694
Deflated Sharpe (per trade, 12 trials): SR 0.004, SR0 0.000, DSR 0.917

## Feature tests (in-sample, selected set, median split, Holm over 6)

| feature | mean R above − below | p | Holm p |
|---|---|---|---|
| p_edge | +1.554 | 1.000 | 1.000 |
| move_abs | +2.067 | 0.991 | 1.000 |
| dispersion_atr | -2.059 | 0.998 | 1.000 |
| sl_atr | -2.020 | 1.000 | 1.000 |
| atr_pctile | -2.128 | 0.062 | 0.370 |
| hour | -2.026 | 0.625 | 1.000 |
