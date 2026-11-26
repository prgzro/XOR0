# Backtest data source and quality

Type: research
Status: resolved
Blocked by: 04

## Question

What historical data is available and good enough for the SQ9 backtests and the Jev replay: XM `.hst` depth per symbol/timeframe, tick data for modelling (Tester "every tick" quality), spread history, and whether external data (e.g. Dukascopy tick data imported into MT4) is needed. Report coverage per symbol and the gaps.

## Answer

- **Coverage:** local XM `.hst` is cache depth, about 2,048 bars per series: about 4 months of H1, days of M1. H4 majors reach 2009 but with holes from 2013-10 to 2017-05 and from 2021-05 to 2024/25, and the pre-2021 block probably isn't XM data. The `.hst` spread field is 0 everywhere. The server backfills on demand (the tester pulled M1 back to 2026-09-18).
- **The tester works end to end** in `~/.wine-jevquant`: Every tick, EURUSD H1, 2026.08.03–11.20 → **72.66% quality, 0 mismatched chart errors**. MT4 needs the ini as a **positional** arg (`terminal.exe /portable config\jq_everytick.ini`). `/config:` is silently ignored, so the harness doc needs fixing.
- **No external tick data needed** for Phases 0–6. Use "Open prices only" for closed-candle SQ9 logic, and Every tick with M1 (90% ceiling) for SL/TP checks. Use an explicit fixed `TestSpread` per symbol, never `0`. The open item is multi-year **depth** (a backfill step), not ticks.
- Write-up: [docs/research/backtest-data-source.md](../../../docs/research/backtest-data-source.md)
