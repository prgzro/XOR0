# Backtest data source and quality

Research for ticket `.scratch/jev-quant/issues/11-backtest-data-source.md`. Probed on 2026-11-26 (server time EET, GMT+2). The user's terminal and the isolated copy are both MT4 build 1492. The account is demo `79273043` on `XMGlobal-Demo 2`.

## TL;DR

- **The Strategy Tester works end to end** in the isolated prefix now that the demo login is saved. One Every tick pass on EURUSD H1 from 2026.08.03 to 2026.11.20 gave **modelling quality 72.66%** with **0 mismatched chart errors**, 2025 bars and 4,961,169 ticks modelled, and spread "Current (19)". It took 1 min 39 s, mostly spent downloading M1 and M5 history. The report and the EA's CSV both came back.
- **Correction to the harness write-up:** MT4 takes the ini as a **positional argument** (`terminal.exe /portable config\jq_everytick.ini`). `/config:<file>` is MT5 syntax, and MT4 silently ignores it: the terminal logs in and just sits there. The harness doc's `/config:` recipe never starts a test. See Q2.
- **Coverage:** the local `.hst` files are mostly about 2,048 bars per symbol and timeframe, which is just what charts happened to cache. On the current server that means about 4 months of H1 and a few days of M1. H4 for the majors goes back to 2009 but has **two multi-year holes** (2013-10 → 2017-05 and 2021-05 → 2024/25). **The `.hst` spread field is 0 in every file.** There's no spread history.
- **The server can backfill on demand.** The tester itself pulled EURUSD M1 back to 2026-09-18 (about 70k bars) and M5 back to 2026-07-31.
- **Recommendation:** XM's own history is **enough** for the SQ9 backtests and the Jev replay, because the strategy acts on closed candles. Use "Open prices only" for signal logic, and Every tick with M1 (≤ 90%) when stop/target fills inside a bar matter. Model spread explicitly as a fixed, conservative `TestSpread`. **External tick data (Dukascopy via Tickstory or Tick Data Suite) isn't needed** for Phases 0–6. It would only buy "99%" plus variable spread, its tooling is Windows-only (TDS explicitly doesn't support Linux), and the ticks would be someone else's feed, not XM's. The real gap is **depth**: multi-year H1 needs a deliberate backfill step (see the HITL list).

## Q1. Coverage

Method: `hst_coverage.py` (read-only) parses the MT4 `.hst` v401 format: a 148-byte header, then 60-byte records of `time int64, open, high, low, close double, tick_volume int64, spread int32, real_volume int64`. That layout matches `MqlRates`, which has an `int spread` field ([MQL4 docs, MqlRates](https://docs.mql4.com/constants/structures/mqlrates)). A "weekday gap" is a run of missing bar slots that fall Monday to Friday in server time, so the Fri→Mon weekend is excluded and public holidays are not. W1 and MN are not gap-checked.

How to read the gaps:
- **Majors, H1:** the only real gaps are Christmas and New Year (`36 h @ 2025-12-24 19:00`) and **one hour on Fri 2026-10-30 22:00**. That's the week Europe left DST before the US did, so XM's GMT+2/+3 server clock closes an hour earlier. No data holes.
- **GOLD, SILVER, OIL, NGAS, US30, H1 (about 90 one-bar "gaps"):** this is the daily trading break around 00:00 server time. GOLD H1 has 5 bars at hour 0 against 89 at every other hour. It's a session break, not missing data.
- **M1 (262 short gaps in the isolated copy):** MT4 only forms an M1 bar when a tick arrives, so quiet minutes, mostly around rollover, have no bar. This is normal.
- **H4 majors (14k bars from 2009):** these carry the **same 2009-12-21 → 2021-05-06 block that sits in `history/default/`**: an identical 12,077 bars for EURUSD, GBPUSD, USDCHF and USDJPY. That block contains the 2013-10-18 → 2017-05-16 hole (1,306 days). XM data then resumes in 2024-09 (`XMGlobal-Demo`) or 2025-07 (`XMGlobal-Demo 2`). I can't tell where that older block came from. It predates this account, and it may be a History Center download from MetaQuotes' history server, which MT4 warns "can differ from historical data stored on the broker's trade server" ([MT4 help, History Center](https://www.metatrader4.com/en/trading-platform/help/service/history_center)). **Don't use pre-2024 H4 as XM data.**
- **Spread field:** zero in **every** file, every bar. `real_volume` is also 0. So XM history gives no spread history at all.
- **Depth is cache, not server limit.** About 2,048 bars per file means that's what charts loaded. When the tester asked for more, the server sent M1 back about 10 weeks and M5 back about 4 months (see the isolated table and Q2). The tester only requests enough to cover the test range, so the server's maximum M1 and H1 depth is **not yet measured**.

### Coverage tables

#### User terminal, `history/XMGlobal-Demo 2/` (current account server)

| Symbol | TF | Bars | First bar | Last bar | Weekday gaps (events / missing bars) | Largest weekday gap | Spread field non-zero |
|---|---|--:|---|---|--:|---|--:|
| EURUSD | M1 | 2188 | 2026-11-24 12:54 | 2026-11-26 01:39 | 11 / 18 | 0.1 h @ 2026-11-25 00:00 | 0 |
| EURUSD | M5 | 2078 | 2026-11-16 20:30 | 2026-11-26 01:35 | 0 / 0 |  | 0 |
| EURUSD | M15 | 2058 | 2026-10-27 14:15 | 2026-11-26 01:30 | 1 / 4 | 1.0 h @ 2026-10-30 22:45 | 0 |
| EURUSD | M30 | 2053 | 2026-09-28 07:30 | 2026-11-26 01:30 | 1 / 2 | 1.0 h @ 2026-10-30 22:30 | 0 |
| EURUSD | H1 | 2122 | 2026-07-24 16:00 | 2026-11-26 01:00 | 1 / 1 | 1.0 h @ 2026-10-30 22:00 | 0 |
| EURUSD | H4 | 14144 | 2009-12-21 00:00 | 2026-11-26 00:00 | 227 / 12576 | 26464.0 h @ 2021-05-06 16:00 | 0 |
| EURUSD | D1 | 2049 | 2019-02-14 00:00 | 2026-11-26 00:00 | 11 / 11 | 24.0 h @ 2019-12-24 00:00 | 0 |
| EURUSD | W1 | 1025 | 2007-04-08 00:00 | 2026-11-22 00:00 | n/a (W1/MN) |  | 0 |
| EURUSD | MN | 256 | 2005-10-01 00:00 | 2026-11-01 00:00 | n/a (W1/MN) |  | 0 |
| GBPUSD | H1 | 2050 | 2026-07-29 16:00 | 2026-11-26 01:00 | 1 / 1 | 1.0 h @ 2026-10-30 22:00 | 0 |
| GOLD | M30 | 2051 | 2026-09-24 11:30 | 2026-11-26 01:30 | 44 / 90 | 2.0 h @ 2026-10-30 22:30 | 0 |
| GOLD | H1 | 2048 | 2026-07-23 21:00 | 2026-11-25 23:00 | 88 / 91 | 3.0 h @ 2026-09-07 21:00 | 0 |
| GOLD | D1 | 2052 | 2018-12-14 00:00 | 2026-11-26 00:00 | 23 / 23 | 24.0 h @ 2018-12-24 00:00 | 0 |


#### Isolated copy `C:\JevQuantMT4\history\XMGlobal-Demo 2\`, after the tester run (the tester downloaded M1 and M5)

| Symbol | TF | Bars | First bar | Last bar | Weekday gaps (events / missing bars) | Largest weekday gap | Spread field non-zero |
|---|---|--:|---|---|--:|---|--:|
| EURUSD | M1 | 69958 | 2026-09-18 05:39 | 2026-11-26 02:04 | 262 / 446 | 1.1 h @ 2026-10-30 22:57 | 0 |
| EURUSD | M5 | 24064 | 2026-07-31 12:30 | 2026-11-26 02:00 | 3 / 15 | 1.1 h @ 2026-10-30 22:55 | 0 |
| EURUSD | H1 | 2123 | 2026-07-24 16:00 | 2026-11-26 02:00 | 1 / 1 | 1.0 h @ 2026-10-30 22:00 | 0 |

The isolated `history/XMGlobal-Demo/` holds only `EURUSD60.hst`, a copy of the user file listed below.

#### User terminal, `history/default/`

| Symbol | TF | Bars | First bar | Last bar | Weekday gaps (events / missing bars) | Largest weekday gap | Spread field non-zero |
|---|---|--:|---|---|--:|---|--:|
| EURUSD | H4 | 12077 | 2009-12-21 00:00 | 2021-05-06 16:00 | 224 / 5942 | 22360.0 h @ 2013-10-18 20:00 | 0 |
| GBPUSD | H4 | 12077 | 2009-12-21 00:00 | 2021-05-06 16:00 | 224 / 5942 | 22360.0 h @ 2013-10-18 20:00 | 0 |
| USDCHF | H4 | 12077 | 2009-12-21 00:00 | 2021-05-06 16:00 | 224 / 5942 | 22360.0 h @ 2013-10-18 20:00 | 0 |
| USDJPY | H4 | 12077 | 2009-12-21 00:00 | 2021-05-06 16:00 | 224 / 5942 | 22360.0 h @ 2013-10-18 20:00 | 0 |

<details><summary>User terminal, <code>history/XMGlobal-Demo/</code> (older account, files last written Feb–Mar 2026): 129 series</summary>

| Symbol | TF | Bars | First bar | Last bar | Weekday gaps (events / missing bars) | Largest weekday gap | Spread field non-zero |
|---|---|--:|---|---|--:|---|--:|
| AUDUSD | M1 | 2052 | 2026-02-24 19:05 | 2026-02-26 05:23 | 7 / 7 | 0.0 h @ 2026-02-25 00:14 | 0 |
| AUDUSD | M5 | 2049 | 2026-02-17 02:40 | 2026-02-26 05:20 | 0 / 0 |  | 0 |
| AUDUSD | M15 | 2048 | 2026-01-27 21:30 | 2026-02-26 05:15 | 0 / 0 |  | 0 |
| AUDUSD | M30 | 2048 | 2025-12-24 13:30 | 2026-02-26 05:00 | 2 / 144 | 36.0 h @ 2025-12-24 19:30 | 0 |
| AUDUSD | H1 | 2095 | 2025-10-24 22:00 | 2026-03-02 04:00 | 3 / 73 | 36.0 h @ 2025-12-24 19:00 | 0 |
| AUDUSD | H4 | 2048 | 2024-10-30 00:00 | 2026-02-26 04:00 | 4 / 34 | 36.0 h @ 2025-12-24 16:00 | 0 |
| AUDUSD | D1 | 2048 | 2018-05-11 00:00 | 2026-02-26 00:00 | 13 / 13 | 24.0 h @ 2018-12-24 00:00 | 0 |
| AUDUSD | W1 | 1028 | 2006-06-18 00:00 | 2026-02-22 00:00 | n/a (W1/MN) |  | 0 |
| AUDUSD | MN | 257 | 2004-10-01 00:00 | 2026-02-01 00:00 | n/a (W1/MN) |  | 0 |
| BTCUSD | M1 | 12357 | 2026-03-01 06:21 | 2026-03-09 21:04 | 0 / 0 |  | 0 |
| BTCUSD | M5 | 4113 | 2026-02-23 13:20 | 2026-03-09 21:00 | 0 / 0 |  | 0 |
| BTCUSD | M15 | 2738 | 2026-02-09 07:45 | 2026-03-09 21:00 | 0 / 0 |  | 0 |
| BTCUSD | M30 | 2394 | 2026-01-19 00:30 | 2026-03-09 21:00 | 0 / 0 |  | 0 |
| BTCUSD | H1 | 2222 | 2025-12-07 08:00 | 2026-03-09 21:00 | 0 / 0 |  | 0 |
| BTCUSD | H4 | 2092 | 2025-03-26 08:00 | 2026-03-09 20:00 | 0 / 0 |  | 0 |
| BTCUSD | D1 | 2055 | 2019-12-05 00:00 | 2026-03-09 00:00 | 4 / 4 | 24.0 h @ 2019-12-24 00:00 | 0 |
| BTCUSD | W1 | 670 | 2012-12-30 00:00 | 2026-03-08 00:00 | n/a (W1/MN) |  | 0 |
| BTCUSD | MN | 156 | 2013-01-01 00:00 | 2026-03-01 00:00 | n/a (W1/MN) |  | 0 |
| EURCHF | M1 | 2054 | 2026-02-24 19:15 | 2026-02-26 05:31 | 3 / 3 | 0.0 h @ 2026-02-25 00:00 | 0 |
| EURCHF | M5 | 2049 | 2026-02-17 02:45 | 2026-02-26 05:30 | 1 / 1 | 0.1 h @ 2026-02-20 23:55 | 0 |
| EURCHF | M15 | 2049 | 2026-01-27 21:30 | 2026-02-26 05:30 | 0 / 0 |  | 0 |
| EURCHF | M30 | 2049 | 2025-12-24 13:30 | 2026-02-26 05:30 | 2 / 144 | 36.0 h @ 2025-12-24 19:30 | 0 |
| EURCHF | H1 | 2146 | 2025-10-24 22:00 | 2026-03-04 07:00 | 3 / 73 | 36.0 h @ 2025-12-24 19:00 | 0 |
| EURCHF | H4 | 2048 | 2024-10-30 00:00 | 2026-02-26 04:00 | 4 / 34 | 36.0 h @ 2025-12-24 16:00 | 0 |
| EURCHF | D1 | 2048 | 2018-05-11 00:00 | 2026-02-26 00:00 | 13 / 13 | 24.0 h @ 2018-12-24 00:00 | 0 |
| EURCHF | W1 | 1028 | 2006-06-18 00:00 | 2026-02-22 00:00 | n/a (W1/MN) |  | 0 |
| EURCHF | MN | 257 | 2004-10-01 00:00 | 2026-02-01 00:00 | n/a (W1/MN) |  | 0 |
| EURGBP | M1 | 2050 | 2026-02-24 19:19 | 2026-02-26 05:31 | 3 / 3 | 0.0 h @ 2026-02-25 00:03 | 0 |
| EURGBP | M5 | 2049 | 2026-02-17 02:50 | 2026-02-26 05:30 | 0 / 0 |  | 0 |
| EURGBP | M15 | 2049 | 2026-01-27 21:30 | 2026-02-26 05:30 | 0 / 0 |  | 0 |
| EURGBP | M30 | 2049 | 2025-12-24 13:30 | 2026-02-26 05:30 | 2 / 144 | 36.0 h @ 2025-12-24 19:30 | 0 |
| EURGBP | H1 | 2048 | 2025-10-24 22:00 | 2026-02-26 05:00 | 3 / 73 | 36.0 h @ 2025-12-24 19:00 | 0 |
| EURGBP | H4 | 2048 | 2024-10-30 00:00 | 2026-02-26 04:00 | 4 / 34 | 36.0 h @ 2025-12-24 16:00 | 0 |
| EURGBP | D1 | 2048 | 2018-05-11 00:00 | 2026-02-26 00:00 | 13 / 13 | 24.0 h @ 2018-12-24 00:00 | 0 |
| EURGBP | W1 | 1028 | 2006-06-18 00:00 | 2026-02-22 00:00 | n/a (W1/MN) |  | 0 |
| EURGBP | MN | 257 | 2004-10-01 00:00 | 2026-02-01 00:00 | n/a (W1/MN) |  | 0 |
| EURUSD | M1 | 2049 | 2026-02-24 18:45 | 2026-02-26 05:12 | 17 / 19 | 0.0 h @ 2026-02-26 00:36 | 0 |
| EURUSD | M5 | 2048 | 2026-02-17 02:35 | 2026-02-26 05:10 | 0 / 0 |  | 0 |
| EURUSD | M15 | 2048 | 2026-01-27 21:15 | 2026-02-26 05:00 | 0 / 0 |  | 0 |
| EURUSD | M30 | 2048 | 2025-12-24 13:30 | 2026-02-26 05:00 | 2 / 144 | 36.0 h @ 2025-12-24 19:30 | 0 |
| EURUSD | H1 | 2260 | 2025-10-24 22:00 | 2026-03-11 00:00 | 3 / 73 | 36.0 h @ 2025-12-24 19:00 | 0 |
| EURUSD | H4 | 14428 | 2009-12-21 00:00 | 2026-03-27 20:00 | 229 / 11256 | 22360.0 h @ 2013-10-18 20:00 | 0 |
| EURUSD | D1 | 2048 | 2018-05-11 00:00 | 2026-02-26 00:00 | 13 / 13 | 24.0 h @ 2018-12-24 00:00 | 0 |
| EURUSD | W1 | 1028 | 2006-06-18 00:00 | 2026-02-22 00:00 | n/a (W1/MN) |  | 0 |
| EURUSD | MN | 257 | 2004-12-01 00:00 | 2026-02-01 00:00 | n/a (W1/MN) |  | 0 |
| GBPUSD | M1 | 2066 | 2026-02-24 18:56 | 2026-02-26 05:31 | 7 / 10 | 0.1 h @ 2026-02-26 00:05 | 0 |
| GBPUSD | M5 | 2052 | 2026-02-17 02:35 | 2026-02-26 05:30 | 0 / 0 |  | 0 |
| GBPUSD | M15 | 2050 | 2026-01-27 21:15 | 2026-02-26 05:30 | 0 / 0 |  | 0 |
| GBPUSD | M30 | 2049 | 2025-12-24 13:30 | 2026-02-26 05:30 | 2 / 144 | 36.0 h @ 2025-12-24 19:30 | 0 |
| GBPUSD | H1 | 2594 | 2025-10-23 22:00 | 2026-03-27 22:00 | 5 / 75 | 36.0 h @ 2025-12-24 19:00 | 0 |
| GBPUSD | H4 | 14312 | 2009-12-21 00:00 | 2026-03-03 00:00 | 229 / 11256 | 22360.0 h @ 2013-10-18 20:00 | 0 |
| GBPUSD | D1 | 2048 | 2018-05-11 00:00 | 2026-02-26 00:00 | 13 / 13 | 24.0 h @ 2018-12-24 00:00 | 0 |
| GBPUSD | W1 | 1028 | 2006-06-18 00:00 | 2026-02-22 00:00 | n/a (W1/MN) |  | 0 |
| GBPUSD | MN | 257 | 2004-10-01 00:00 | 2026-02-01 00:00 | n/a (W1/MN) |  | 0 |
| GOLD | M1 | 2048 | 2026-02-26 12:49 | 2026-02-27 23:57 | 1 / 61 | 1.0 h @ 2026-02-26 23:58 | 0 |
| GOLD | M5 | 2048 | 2026-02-18 14:20 | 2026-02-27 23:55 | 7 / 84 | 1.0 h @ 2026-02-18 23:55 | 0 |
| GOLD | M15 | 2048 | 2026-01-28 15:30 | 2026-02-27 23:45 | 22 / 98 | 3.5 h @ 2026-02-16 21:15 | 0 |
| GOLD | M30 | 2048 | 2025-12-24 08:00 | 2026-02-27 23:30 | 45 / 240 | 36.0 h @ 2025-12-24 19:30 | 0 |
| GOLD | H1 | 2141 | 2025-10-22 16:00 | 2026-03-06 01:00 | 94 / 173 | 36.0 h @ 2025-12-24 19:00 | 0 |
| GOLD | H4 | 2097 | 2024-10-30 04:00 | 2026-03-12 00:00 | 10 / 43 | 32.0 h @ 2024-12-24 17:00 | 0 |
| GOLD | D1 | 2068 | 2018-03-23 00:00 | 2026-03-27 00:00 | 23 / 23 | 24.0 h @ 2018-03-29 00:00 | 0 |
| GOLD | W1 | 1030 | 2006-06-18 00:00 | 2026-03-08 00:00 | n/a (W1/MN) |  | 0 |
| GOLD | MN | 309 | 2001-01-01 00:00 | 2026-03-01 00:00 | n/a (W1/MN) |  | 0 |
| LINKUSD | M1 | 2050 | 2026-02-28 22:58 | 2026-03-02 15:57 | 107 / 151 | 0.1 h @ 2026-03-02 07:30 | 0 |
| LINKUSD | M5 | 2048 | 2026-02-23 11:30 | 2026-03-02 15:55 | 10 / 11 | 0.2 h @ 2026-02-24 10:40 | 0 |
| LINKUSD | M15 | 2048 | 2026-02-09 07:00 | 2026-03-02 15:45 | 0 / 0 |  | 0 |
| LINKUSD | M30 | 2048 | 2026-01-18 23:30 | 2026-03-02 15:30 | 0 / 0 |  | 0 |
| LINKUSD | H1 | 2048 | 2025-12-07 08:00 | 2026-03-02 15:00 | 0 / 0 |  | 0 |
| LINKUSD | H4 | 2048 | 2025-03-26 08:00 | 2026-03-02 12:00 | 0 / 0 |  | 0 |
| LINKUSD | D1 | 1655 | 2021-07-13 00:00 | 2026-03-02 00:00 | 2 / 18 | 336.0 h @ 2021-09-07 00:00 | 0 |
| LINKUSD | W1 | 241 | 2021-07-11 00:00 | 2026-03-01 00:00 | n/a (W1/MN) |  | 0 |
| LINKUSD | MN | 57 | 2021-07-01 00:00 | 2026-03-01 00:00 | n/a (W1/MN) |  | 0 |
| MATICUSD | H1 | 2048 | 2025-12-07 08:00 | 2026-03-02 15:00 | 0 / 0 |  | 0 |
| MATICUSD | D1 | 1607 | 2021-10-04 00:00 | 2026-03-02 00:00 | 1 / 4 | 96.0 h @ 2022-03-21 00:00 | 0 |
| NGAS-APR26 | M1 | 2048 | 2026-03-03 11:23 | 2026-03-04 23:34 | 52 / 124 | 1.0 h @ 2026-03-03 23:59 | 0 |
| NGAS-APR26 | M5 | 2048 | 2026-02-23 11:15 | 2026-03-04 23:30 | 21 / 116 | 1.8 h @ 2026-02-27 23:10 | 0 |
| NGAS-APR26 | M15 | 2048 | 2026-02-02 11:45 | 2026-03-04 23:30 | 23 / 112 | 3.5 h @ 2026-02-16 21:15 | 0 |
| NGAS-APR26 | M30 | 2048 | 2025-12-30 14:30 | 2026-03-04 23:30 | 45 / 179 | 36.0 h @ 2025-12-31 19:30 | 0 |
| NGAS-APR26 | H1 | 2048 | 2025-10-24 13:00 | 2026-03-04 23:00 | 92 / 195 | 36.0 h @ 2025-12-24 19:00 | 0 |
| NGAS-APR26 | H4 | 2122 | 2024-11-04 17:00 | 2026-03-23 04:00 | 17 / 50 | 32.0 h @ 2024-12-24 17:00 | 0 |
| NGAS-APR26 | D1 | 2048 | 2018-03-26 00:00 | 2026-03-04 00:00 | 24 / 25 | 48.0 h @ 2023-11-01 00:00 | 0 |
| NGAS-APR26 | W1 | 1026 | 2006-07-09 00:00 | 2026-03-01 00:00 | n/a (W1/MN) |  | 0 |
| NGAS-APR26 | MN | 257 | 2004-11-01 00:00 | 2026-03-01 00:00 | n/a (W1/MN) |  | 0 |
| OIL-APR26 | M1 | 5164 | 2026-03-03 12:26 | 2026-03-09 06:14 | 4 / 225 | 1.0 h @ 2026-03-03 23:59 | 0 |
| OIL-APR26 | M5 | 2671 | 2026-02-23 13:10 | 2026-03-09 06:10 | 10 / 126 | 1.8 h @ 2026-02-27 23:10 | 0 |
| OIL-APR26 | M15 | 2255 | 2026-02-02 12:15 | 2026-03-09 06:00 | 25 / 121 | 3.5 h @ 2026-02-16 21:15 | 0 |
| OIL-APR26 | M30 | 2434 | 2025-12-30 14:30 | 2026-03-17 09:30 | 54 / 197 | 36.0 h @ 2025-12-31 19:30 | 0 |
| OIL-APR26 | H1 | 2155 | 2025-10-22 23:00 | 2026-03-09 06:00 | 95 / 181 | 36.0 h @ 2025-12-24 19:00 | 0 |
| OIL-APR26 | H4 | 2062 | 2024-11-04 13:00 | 2026-03-09 04:00 | 9 / 42 | 32.0 h @ 2024-12-24 17:00 | 0 |
| OIL-APR26 | D1 | 2053 | 2018-03-28 00:00 | 2026-03-11 00:00 | 23 / 23 | 24.0 h @ 2018-03-29 00:00 | 0 |
| OIL-APR26 | W1 | 1027 | 2007-07-22 00:00 | 2026-03-08 00:00 | n/a (W1/MN) |  | 0 |
| OIL-APR26 | MN | 257 | 2004-11-01 00:00 | 2026-03-01 00:00 | n/a (W1/MN) |  | 0 |
| SILVER | M1 | 2048 | 2026-02-26 12:49 | 2026-02-27 23:57 | 1 / 61 | 1.0 h @ 2026-02-26 23:58 | 0 |
| SILVER | M5 | 2048 | 2026-02-18 14:20 | 2026-02-27 23:55 | 7 / 84 | 1.0 h @ 2026-02-18 23:55 | 0 |
| SILVER | M15 | 2048 | 2026-01-28 15:30 | 2026-02-27 23:45 | 22 / 98 | 3.5 h @ 2026-02-16 21:15 | 0 |
| SILVER | M30 | 2048 | 2025-12-24 08:00 | 2026-02-27 23:30 | 45 / 240 | 36.0 h @ 2025-12-24 19:30 | 0 |
| SILVER | H1 | 2384 | 2025-10-02 02:00 | 2026-02-27 23:00 | 103 / 182 | 36.0 h @ 2025-12-24 19:00 | 0 |
| SILVER | H4 | 2049 | 2024-10-30 04:00 | 2026-03-02 01:00 | 10 / 43 | 32.0 h @ 2024-12-24 17:00 | 0 |
| SILVER | D1 | 2049 | 2018-03-23 00:00 | 2026-03-02 00:00 | 23 / 23 | 24.0 h @ 2018-03-29 00:00 | 0 |
| SILVER | W1 | 1028 | 2006-06-18 00:00 | 2026-02-22 00:00 | n/a (W1/MN) |  | 0 |
| SILVER | MN | 246 | 2005-09-01 00:00 | 2026-02-01 00:00 | n/a (W1/MN) |  | 0 |
| US30-MAR26 | H1 | 2048 | 2025-10-22 15:00 | 2026-03-02 15:00 | 92 / 185 | 36.0 h @ 2025-12-24 19:00 | 0 |
| US30-MAR26 | H4 | 2048 | 2024-10-28 08:00 | 2026-03-02 13:00 | 24 / 58 | 32.0 h @ 2024-12-24 17:00 | 0 |
| US30-MAR26 | D1 | 2048 | 2018-03-28 00:00 | 2026-03-02 00:00 | 21 / 21 | 24.0 h @ 2018-03-29 00:00 | 0 |
| USDCHF | M1 | 2064 | 2026-02-24 18:58 | 2026-02-26 05:31 | 8 / 10 | 0.1 h @ 2026-02-26 00:01 | 0 |
| USDCHF | M5 | 2051 | 2026-02-17 02:35 | 2026-02-26 05:30 | 1 / 1 | 0.1 h @ 2026-02-20 23:55 | 0 |
| USDCHF | M15 | 2049 | 2026-01-27 21:30 | 2026-02-26 05:30 | 0 / 0 |  | 0 |
| USDCHF | M30 | 2049 | 2025-12-24 13:30 | 2026-02-26 05:30 | 2 / 144 | 36.0 h @ 2025-12-24 19:30 | 0 |
| USDCHF | H1 | 2435 | 2025-10-07 05:00 | 2026-03-02 15:00 | 3 / 73 | 36.0 h @ 2025-12-24 19:00 | 0 |
| USDCHF | H4 | 14323 | 2009-12-21 00:00 | 2026-03-04 20:00 | 229 / 11256 | 22360.0 h @ 2013-10-18 20:00 | 0 |
| USDCHF | D1 | 2048 | 2018-05-11 00:00 | 2026-02-26 00:00 | 13 / 13 | 24.0 h @ 2018-12-24 00:00 | 0 |
| USDCHF | W1 | 1028 | 2006-06-18 00:00 | 2026-02-22 00:00 | n/a (W1/MN) |  | 0 |
| USDCHF | MN | 257 | 2004-10-01 00:00 | 2026-02-01 00:00 | n/a (W1/MN) |  | 0 |
| USDJPY | M1 | 2048 | 2026-02-24 18:52 | 2026-02-26 05:06 | 5 / 7 | 0.0 h @ 2026-02-26 00:19 | 0 |
| USDJPY | M5 | 2048 | 2026-02-17 02:30 | 2026-02-26 05:05 | 0 / 0 |  | 0 |
| USDJPY | M15 | 2048 | 2026-01-27 21:15 | 2026-02-26 05:00 | 0 / 0 |  | 0 |
| USDJPY | M30 | 2048 | 2025-12-24 13:30 | 2026-02-26 05:00 | 2 / 144 | 36.0 h @ 2025-12-24 19:30 | 0 |
| USDJPY | H1 | 2298 | 2025-10-24 06:00 | 2026-03-11 22:00 | 3 / 73 | 36.0 h @ 2025-12-24 19:00 | 0 |
| USDJPY | H4 | 14341 | 2009-12-21 00:00 | 2026-03-09 16:00 | 229 / 11256 | 22360.0 h @ 2013-10-18 20:00 | 0 |
| USDJPY | D1 | 2049 | 2018-05-10 00:00 | 2026-02-26 00:00 | 13 / 13 | 24.0 h @ 2018-12-24 00:00 | 0 |
| USDJPY | W1 | 1028 | 2006-06-18 00:00 | 2026-02-22 00:00 | n/a (W1/MN) |  | 0 |
| USDJPY | MN | 257 | 2004-10-01 00:00 | 2026-02-01 00:00 | n/a (W1/MN) |  | 0 |
| USDNOK | H1 | 2048 | 2025-11-05 15:00 | 2026-03-09 22:00 | 3 / 73 | 36.0 h @ 2025-12-24 19:00 | 0 |
| USDNOK | H4 | 2048 | 2024-11-08 20:00 | 2026-03-09 20:00 | 4 / 34 | 36.0 h @ 2025-12-24 16:00 | 0 |
| USDNOK | D1 | 2048 | 2018-05-22 00:00 | 2026-03-09 00:00 | 13 / 13 | 24.0 h @ 2018-12-24 00:00 | 0 |
| USDSEK | H1 | 2048 | 2025-11-05 14:00 | 2026-03-09 22:00 | 4 / 74 | 36.0 h @ 2025-12-24 19:00 | 0 |
| USDSEK | H4 | 2048 | 2024-11-08 20:00 | 2026-03-09 20:00 | 4 / 34 | 36.0 h @ 2025-12-24 16:00 | 0 |

</details>

## Q2. Strategy Tester, Every tick, EURUSD H1

### Exact working setup

`C:\JevQuantMT4\config\jq_everytick.ini` (CRLF; copy in the scratchpad `backtest-data/jq_everytick.ini`):

```ini
; JevQuant backtest-data probe: every tick
TestExpert=JevQuantProbe\ProbeTesterEA
TestSymbol=EURUSD
TestPeriod=H1
TestModel=0
TestSpread=0
TestOptimization=false
TestDateEnable=true
TestFromDate=2026.08.03
TestToDate=2026.11.20
TestReport=tester\jq_everytick
TestReplaceReport=true
TestShutdownTerminal=true
TestVisualEnable=false
ExpertsEnable=false
ExpertsTrades=false
EnableNews=false
```

```bash
export WINEPREFIX=/home/prgzro/.wine-jevquant            # never ~/.wine
cd "$WINEPREFIX/drive_c/JevQuantMT4"
timeout 900 wine terminal.exe /portable 'config\jq_everytick.ini'   # positional, NOT /config:
WINEPREFIX=/home/prgzro/.wine-jevquant wineserver -k     # this prefix only
```

- **First attempt failed silently** with `terminal.exe /portable /config:C:\JevQuantMT4\config\jq_everytick.ini`. The terminal logged in (Market Watch live, balance 1,000 USD), but the tester never opened, and nothing was written until the timeout. The MT4 docs only show the positional form: `terminal.exe config\start.ini`, or a full path. A relative path is "searched for in the client terminal's data folder" ([MT4 help, Configuration at Startup](https://www.metatrader4.com/en/trading-platform/help/service/start_conf_file)). With the positional path, the tester journal logged `Tester: start with configuration file` at once. **`docs/research/mt4-test-harness.md` §(b) needs this fix.** (I didn't edit it, because it's outside this ticket.)
- Exit: `TestShutdownTerminal=true` closed the terminal when the test finished, so `timeout` returned with exit 0.
- `TestSpread=0` means "use the current spread of a symbol at the beginning of testing" ([same page](https://www.metatrader4.com/en/trading-platform/help/service/start_conf_file)). The journal logged `TestGenerator: current spread 19 used`, which is 1.9 pips at 02:03 EET, around rollover.
- The deposit came from `tester\ProbeTesterEA.ini` (`deposit=10000`), not from the account's 1,000 USD.

### Results

| Field | Value |
| --- | --- |
| Report | `C:\JevQuantMT4\tester\jq_everytick.htm` (+ `.gif`). Copied to the scratchpad `backtest-data/` |
| Server / build | XMGlobal-Demo 2 (Build 1492) |
| Period | 1 Hour (H1) 2026.08.03 00:00 – 2026.11.19 23:00 |
| Model | Every tick (the most precise method based on all available least timeframes) |
| Bars in test | 2025 |
| Ticks modelled | 4,961,169 |
| **Modelling quality** | **72.66%** |
| **Mismatched charts errors** | **0** |
| Spread | Current (19) |
| Trades | 0 (the probe EA only counts ticks) |
| EA output `tester\files\JevQuantProbe\tester_out.csv` | `EURUSD,60,4961041,2024,2026.07.24 16:00,1.09653,true,true,0` |
| Tester journal | `tester\logs\20261126.log`: 1 min 37 s of `History: download EURUSD,M1 [...]` back to `2026.09.18 05:39`, then `EURUSD,M5` back to `2026.07.31 12:30`, then the test itself took 0.245 s |
| FXT | `tester\history\EURUSD60_0.fxt`, 278 MB, regenerated per run |

**Why 72.66%:** MetaQuotes' formula weights each stretch by the finest data behind it: 0.25 for nearest-timeframe generation, 0.5 for the stretch modelled from M5 and other intermediate timeframes, and 0.9 for the stretch modelled from M1. That is `((0.25·(StartGen−StartBar) + 0.5·(StartGenM1−StartGen) + 0.9·(HistoryTotal−StartGenM1)) / (HistoryTotal−StartBar))·100%` ([MetaQuotes, "What the Numbers in the Expert Testing Report Mean", 2006](https://www.mql5.com/en/articles/1486)). Here about 45% of the range (Aug 3 → Sep 18) only had M5, and the rest had M1: 0.5·0.45 + 0.9·0.55 ≈ 72%. **With M1 covering the whole range, the ceiling is 90%.** That's the factor-0.9 term, and it's the best possible from bar history alone.

**Safety notes:**
- **LiveUpdate:** neither the terminal journal nor the tester journal logged any LiveUpdate activity in either run. The only `LiveUpdate:` lines are the routine `update C:\JevQuantMT4\MQL4 folder` from first start. The copy is already on the latest build (1492), so nothing triggers it. The previous agent did **not** add a block, and none exists: `/skipupdate:<token>` is an internal token the updater passes to the restarted terminal, not a documented switch. **Residual risk:** when MetaQuotes ships a build newer than 1492, the isolated copy will self-update and restart **inside `~/.wine-jevquant`**. That prefix has its own wineserver and its own `AppData\...\WebInstall`, so the user's terminal can't be hit. The harness should still grep `logs\*.log` for `LiveUpdate` after each run and fail loudly, so an unexpected restart doesn't pass as a finished test.
- `ExpertsTrades=false` is set, the account is demo, and nothing ran outside the Tester. The tester does print `IsTradeAllowed()=true`, which is normal: trades inside the Tester are simulated.

## Q3. Is external tick data needed?

**What the primary sources say:**
- MT4 history is bars only, and the tester builds ticks from them. "Every tick" is "the most accurate method of modeling prices within a bar". It uses all available smaller timeframes, and "one-minute data are highly desirable to be available that would cover the entire testing range". Also, "it is not recommended to launch testing on every tick if there are no available less timeframes that completely cover the period under test." "Control points" uses the nearest smaller timeframe. "Open prices only" models only each bar's open. If history is missing, "the tester will download the last 512 history bars automatically" ([MT4 help, Strategy Tester setup](https://www.metatrader4.com/en/trading-platform/help/autotrading/tester/tester_parameters); [MetaQuotes, "Strategy Tester: Modes of Modeling during Testing", 2005](https://www.mql5.com/en/articles/1511)). In practice, build 1492 downloaded far more than 512 bars here, enough to cover the requested range down to M5.
- The quality formula above caps bar-based modelling at 90%. The tester reads a generated `.FXT` "with generated succession of bars", whose header carries `int spread` and `double modelquality` ([MT4 help, History Files in FXT Format](https://www.metatrader4.com/en/trading-platform/help/autotrading/tester/tester_fxt)). **99% is only reachable by substituting your own FXT built from real ticks.**
- MetaQuotes' own MT4 tester help page now promotes the MT5 tester's "Every tick based on real ticks" mode, saying "The trade servers of the new platform store the entire real tick history" ([MT4 help, Strategy Tester](https://www.metatrader4.com/en/trading-platform/help/autotrading/tester)). There's no first-party real-tick path for MT4.
- **Tickstory** says MT4 data "only contains 1-minute data with fixed spread information", and its export "embeds the bid/ask spread information for every tick". A correct run "should read 99.9% modeling quality". `MODE_SPREAD` "will always give you the fixed spread", so EAs must use Ask−Bid ([Tickstory, How to test with variable spread](https://tickstory.com/help/advancedtester/how-to-test-with-variable-spre.htm)). Third parties report that launching MT4 outside Tickstory shows "n/a" quality.
- **Tick Data Suite** claims "99% modeling quality", "the actual, variable spread that is recorded in the tick data", slippage and commission settings, and sources including Dukascopy. It is licensed per machine, and "Any non-Windows OS, such as OS X or any other OS derived from Linux…" is **not supported** ([eareview.net, Tick Data Suite](https://eareview.net/tick-data-suite)).
- **StrategyQuant QDM** generates FXT and HST from tick data. MetaTrader must be closed during the export, and the files are set read-only because "MT4 tries to rewrite the file". Mismatched errors usually mean the exported symbol properties don't match the broker's ([StrategyQuant, Test strategy in MT4 with tick precision](https://strategyquant.com/doc/quantdatamanager/test-strategy-metatrader-4-tick-precision/)).

**What 99% would take here:** a Windows tool (Tickstory, TDS or QDM) running under Wine, which is unsupported or unverified. Dukascopy ticks, which are **not XM's prices or spreads**. A symbol-properties export from XM. Read-only FXT files in `C:\JevQuantMT4\tester\history`. And for Tickstory and TDS, launching MT4 through their launcher, which bypasses our scripted `timeout … terminal.exe … ini` harness. That's a lot of machinery and an unsupported platform, for a strategy that doesn't need tick paths.

**Recommendation:**
1. **SQ9 backtests (closed candles only):** evaluate signals on bar close or the next bar's open with **"Open prices only" (`TestModel=2`)**. For logic that only reads completed bars, this is exact, needs no tick data, and modelling quality doesn't apply. Run a second **Every tick (`TestModel=0`) pass** with M1 coverage (target ≈ 90%) to check stop-loss and take-profit fills and same-bar SL/TP ordering. Accept 90% as the ceiling.
2. **Jev replay:** replay decisions against closed bars exported from XM, plus M1 bars for fill simulation in Node. Same data, no ticks needed.
3. **External tick data is not needed** for Phases 0–6. Revisit only if the strategy starts relying on intrabar timing, like entries on touch or very tight stops, where an M1 path is too coarse.
4. **The real gap is depth.** For credible walk-forward and out-of-sample results, the signal timeframe needs years, not months. Next step (HITL or scripted): in the isolated terminal, request deeper H1, H4 and M1 for the symbol list (scroll charts back or use History Center), then rerun `hst_coverage.py`. Prefer XM's own server bars. Treat History Center downloads, and the pre-2024 `default` H4 block, as **non-XM** data, and if used, label them as such. If XM's server depth turns out shallow, the fallback is Dukascopy M1 converted to `.hst` as a clearly labelled proxy dataset. This is still bars, so no FXT hacking is needed.

## Q4. Spread and commission realism

- **XM history has no spread.** The `.hst` spread field is 0 everywhere (Q1). Bars are Bid-only: "The price history stored in the client terminal includes only Bid prices" ([MT4 help, Strategy Tester setup](https://www.metatrader4.com/en/trading-platform/help/autotrading/tester/tester_parameters)).
- **The live demo feed is variable spread.** Measured from the isolated copy's `ticks.raw` (40-byte records: symbol[12], time, bid, ask, seq), during 01:54–01:57 server time around rollover:

  | Symbol | Ticks | Spread (points) min / median / max |
  | --- | --: | --- |
  | EURUSD | 57 | 19 / 21 / 22 |
  | GBPUSD | 43 | 23 / 25 / 27 |
  | USDCHF | 134 | 23 / 28 / 29 |
  | USDJPY | 294 | 20 / 27 / 29 |
  | GOLD | 743 | 49 / 56 / 70 |
  | BTCUSD | 130 | 4000 flat |
  | ETHUSD | 187 | 300 flat |

  This sample is a few minutes at the widest time of day, so it's an upper-end sample, not a profile. The FX spreads are consistent with a Standard-type (commission-free, markup-in-spread) account. I couldn't confirm the account type or XM's published spreads and commissions, because xm.com refused automated fetches. **HITL:** read the account type in the terminal (Navigator → Accounts, or the XM Members Area) and XM's contract specs page.
- **How the tester uses it:** one fixed spread for the whole run. Either `TestSpread=0` ("current spread of a symbol at the beginning of testing", so it depends on when you click Start; this run got 19 at rollover), or an explicit `TestSpread=<points>` ([MT4 help, Configuration at Startup](https://www.metatrader4.com/en/trading-platform/help/service/start_conf_file); [Strategy Tester setup](https://www.metatrader4.com/en/trading-platform/help/autotrading/tester/tester_parameters)). Ask = Bid + that spread on every modelled tick. Commission is taken from the symbol and account settings, which this run (0 trades) didn't exercise.
- **Recommendation for the spec:** **never use `TestSpread=0`**, because it isn't reproducible. Set an explicit, conservative fixed spread per symbol, e.g. the median session spread measured by a small MQL4 logger EA over a week of live demo ticks, plus a padding margin. Model commission and slippage explicitly in the Node replay and PAPER engine, which the map still lists as open. If a variable-spread run is ever needed, it requires the external-tick route from Q3.

## HITL checklist

1. Optional, to measure true XM depth: in the isolated terminal, `WINEPREFIX=/home/prgzro/.wine-jevquant wine 'C:\JevQuantMT4\terminal.exe' /portable`, raise Tools → Options → Charts → "Max bars in history/chart", open H1/H4/M1 charts for the symbol list and scroll back (Home key) until no more data arrives. Then close the terminal and rerun `hst_coverage.py` on `C:\JevQuantMT4\history\XMGlobal-Demo 2`. Don't press "Download" in History Center unless you accept MetaQuotes' non-XM data.
2. Confirm the demo account type (Standard / Ultra Low / Zero) and record XM's published spread and commission for it.
3. Fix `docs/research/mt4-test-harness.md` §(b): positional ini path, not `/config:`.
4. Optional cleanup: `C:\JevQuantMT4\tester\history\EURUSD60_0.fxt` (278 MB) is regenerated every run.

## Scripts and artifacts

In the scratchpad `/tmp/claude-1000/-home-prgzro-Projects-XOR0/205c3630-a6e9-485f-b79e-e22a252b80f3/scratchpad/backtest-data/` (run Python with `-I`):
- `hst_coverage.py <dir>...`: read-only `.hst` scanner that prints JSON (`coverage.json`, `cov_all.json`).
- `ticks_spread.py <ticks.raw>`: spread stats from `ticks.raw`.
- `jq_everytick.ini`, `jq_everytick.htm`, `jq_everytick.gif`, `20261126.log` (tester journal), `tester_out.csv`.
