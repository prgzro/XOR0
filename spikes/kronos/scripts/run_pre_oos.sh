#!/usr/bin/env bash
# Forecasts for the in-sample and contamination windows (2010-01-01 -> 2025-07-01), per symbol,
# as soon as that symbol's MIDPOINT/BID/ASK files exist. Never touches the sealed window.
set -euo pipefail
FROM=${FROM:-2010-01-01}
TO=${TO:-2020-01-01}  # in-sample first; contamination later with FROM=2020-01-01 TO=2025-07-01
cd "$(dirname "$0")/.."
SYMBOLS=${SYMBOLS:-"EURUSD GBPUSD USDJPY USDCHF AUDUSD USDCAD NZDUSD"}  # majors (user, 2026-11-26); gold is a later test
for s in $SYMBOLS; do
  until [[ -f data/ibkr/${s}_MIDPOINT.parquet && -f data/ibkr/${s}_BID.parquet && -f data/ibkr/${s}_ASK.parquet ]]; do sleep 60; done
  .venv/bin/python -W ignore scripts/run_forecasts.py --model small --paths 30 --batch 12 \
      --from "$FROM" --to "$TO" --symbols "$s"
done
echo "forecasts $FROM -> $TO done"
