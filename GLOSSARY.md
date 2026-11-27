# JEV QUANT

An AI-assisted trading service that forecasts prices with Kronos, proposes trades from those forecasts, asks the Jev decision model to approve them, and lets only trades that pass independent risk checks reach Interactive Brokers.

(The v1 SQ9 vocabulary — Origin, Reference Indicator, Major Swing — is archived in `docs/archive/GLOSSARY_v1_SQ9.md`.)

## Forecasting

**Forecast**:
The set of possible future price paths Kronos generates for one symbol at one bar close, read as a distribution (share of paths up, median move, quantiles).
_Avoid_: prediction (suggests a single certain path), signal

**Horizon**:
How many bars ahead a Forecast looks (H). The Forecast says nothing about price beyond it.
_Avoid_: lookahead (means leakage in backtesting)

## Trading decisions

**Time exit**:
Closing a position at market when its Horizon ends with neither SL nor TP hit.
_Avoid_: timeout, expiry

**Candidate**:
A proposed trade (symbol, direction, entry, SL, TP) produced mechanically from a Forecast. Nothing is traded unless a Candidate is approved by Jev and passed by the Risk Gate.
_Avoid_: signal, setup, opportunity

**Decision**:
Jev's validated verdict on one Candidate: approve or no-trade, plus a critical-risk answer and a quality score. Jev can only reject or approve the Candidate's own direction.
_Avoid_: prediction, Jev signal

**Risk Gate**:
The independent, authoritative set of checks that sizes an approved Candidate or blocks it. It overrides any Decision and never moves SL or TP.
_Avoid_: risk engine, filter

## Validation

**Edge test**:
The pre-registered, walk-forward check of whether Kronos Forecasts, turned mechanically into Candidates, earn positive R after costs on bars Kronos never saw. It is the go/no-go for building execution.
_Avoid_: backtest (too general), validation
