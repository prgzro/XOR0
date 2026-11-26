# XM history depth and symbol specs (XMGlobal-Demo 2)

Research for ticket `.scratch/jev-quant/issues/15-pull-max-history.md`. Run on 2026-11-26, 02:12–03:20 server time (EET, GMT+2), in the isolated terminal `C:\JevQuantMT4` (`WINEPREFIX=~/.wine-jevquant`), MT4 build 1492, demo account on `XMGlobal-Demo 2`. No GUI clicks were needed.

## TL;DR

- **XM serves a fixed number of bars per timeframe, not a date range.** The counts are the same for every FX symbol: **M1 ≈ 70,000 bars (about 10 weeks, back to 2026-09-18)**, **H1 42,032 (back to 2020-02-21, ≈ 6.8 years)**, **H4 12,069 (back to 2019-02-26, ≈ 7.7 years)**, **D1 4,585 (back to mid-2009, ≈ 17 years)**. GOLD is close: M1 to 2026-09-16, H1 to 2020-02-14, H4 to 2019-02-20, D1 to 2009-04-20.
- For each series, the oldest bar we got equals MT4's `SERIES_SERVER_FIRSTDATE`. So this is the server's whole depth, not a stall in the download. Asking for more stops adding bars.
- **The pulled series are continuous.** In every H1 and H4 file the biggest gap is the 2020-12-31 New Year break (3.2–3.3 days). M1's biggest gap is a normal weekend. D1's is New Year 2023/24 (4 days). The exception is EURUSD D1, which has a 62-day hole at 2010-05. The pre-2024 holes that the old cached H4 files had are gone.
- **For the edge re-test (ticket 14):** H1 gives about 6.8 years and H4 about 7.7 years of XM's own bars. That is enough for walk-forward. Every-tick testing is still limited by M1, which only covers the last ~10 weeks. Before that, the tester models from H1/H4 ("Open prices only" is the right mode).
- The specs are in the table below. The account is a **Standard-type** contract (1 lot = 100,000 units, GOLD 100 oz). Its leverage is **1:1** (`AccountLeverage()=1`), so margin for 1 lot equals the full notional. **MT4 doesn't expose commission.** XM's website returned HTTP 403 to automated fetches, so I didn't record a commission from a primary source.

## Method

1. **Max bars.** In MT4 the Options values "Max bars in history" and "Max bars in chart" live in the **binary** `config\charts.ini`, not in `terminal.ini`. They are two little-endian int32s: offset `0x14` holds max bars in chart (default `65000`) and offset `0x18` holds max bars in history (default `512000`). I patched them to 5,000,000 and 10,000,000. A backup is at `config\charts.ini.bak-t15`. The startup ini also accepts `ChartsMaxBars=` and `ChartsMaxBarsInHistory=` (key names found as strings in `terminal.exe`), and I set them there as well. `TerminalInfoInteger(TERMINAL_MAXBARS)` then reported 5,000,000.
2. **Startup ini** `config\jq_history_home.ini`: `Symbol=EURUSD`, `Period=H1`, `Script=JevQuant\JevQuantHistoryHome`, `ExpertsEnable=true`, `ExpertsTrades=false`, `ExpertsDllImport=true`, `ExpertsDllConfirm=false`. Run with `WINEPREFIX=/home/prgzro/.wine-jevquant timeout 10800 wine terminal.exe /portable 'config\jq_history_home.ini'`. The script waits for the login, then calls `TerminalClose(0)` when it's done.
3. **Paging.** `iBars`/`iTime`/`CopyTime` at shifts past the oldest bar **did not fetch anything**. Neither did `ChartNavigate(CHART_BEGIN)`. They only return what is cached, about 2,048 bars on a cold series (first attempt: `JevQuantHistoryDepth.mq4`, output `history_depth.csv`). What worked was the GUI **Home key**, simulated. The script opens a chart per symbol/TF with `ChartOpen`, then repeatedly sends `PostMessageW(CHART_WINDOW_HANDLE, WM_KEYDOWN/WM_KEYUP, VK_HOME)` (user32 import), polling `iBars` every 1.5 s. It stops after 10 polls in a row with no growth. Every series stopped that way ("stall", none hit the time or max-bars cap). The bars were written to `history\XMGlobal-Demo 2\*.hst` when the terminal closed.
4. **Specs.** The script reads `MarketInfo` per symbol and `AccountServer/Company/Currency/Leverage`. The account number is not recorded.

Sources (isolated copy): `MQL4\Scripts\JevQuant\JevQuantHistoryHome.mq4` (and the non-working `JevQuantHistoryDepth.mq4`). Outputs: `MQL4\Files\JevQuant\history_depth_home.csv` and `symbol_specs2.csv`. Copies are in the scratchpad `mt4-tasks/`, with `tab15.py` (table) and `gaps.py` (gap scan of the `.hst` files).

## History depth per symbol and timeframe

Server time. "bars" is `iBars` at the end of the pull. Every first bar equals `SERIES_SERVER_FIRSTDATE`.

| Symbol | M1 first bar | M1 bars | H1 first bar | H1 bars | H4 first bar | H4 bars | D1 first bar | D1 bars |
|---|---|---|---|---|---|---|---|---|
| EURUSD | 2026.09.18 05:39 | 69,969 | 2020.02.21 16:00 | 42,032 | 2019.02.26 20:00 | 12,069 | 2009.01.28 00:00 | 4,585 |
| GBPUSD | 2026.09.18 06:24 | 69,981 | 2020.02.21 16:00 | 42,032 | 2019.02.26 20:00 | 12,069 | 2009.07.03 00:00 | 4,585 |
| USDJPY | 2026.09.18 05:59 | 69,978 | 2020.02.21 16:00 | 42,032 | 2019.02.26 20:00 | 12,069 | 2009.07.06 00:00 | 4,585 |
| USDCHF | 2026.09.18 04:52 | 69,993 | 2020.02.21 16:00 | 42,032 | 2019.02.26 20:00 | 12,069 | 2009.07.03 00:00 | 4,585 |
| AUDUSD | 2026.09.18 05:55 | 69,990 | 2020.02.21 16:00 | 42,032 | 2019.02.26 20:00 | 12,069 | 2009.07.03 00:00 | 4,585 |
| USDCAD | 2026.09.18 05:37 | 69,986 | 2020.02.21 16:00 | 42,032 | 2019.02.26 20:00 | 12,069 | 2009.07.03 00:00 | 4,585 |
| NZDUSD | 2026.09.18 03:38 | 69,995 | 2020.02.21 16:00 | 42,031 | 2019.02.26 20:00 | 12,069 | 2009.07.03 00:00 | 4,585 |
| EURGBP | 2026.09.18 06:25 | 70,021 | 2020.02.21 16:00 | 42,032 | 2019.02.26 20:00 | 12,069 | 2009.07.03 00:00 | 4,585 |
| EURJPY | 2026.09.18 08:36 | 70,026 | 2020.02.21 16:00 | 42,033 | 2019.02.26 20:00 | 12,069 | 2009.07.02 00:00 | 4,585 |
| GBPJPY | 2026.09.18 07:31 | 70,018 | 2020.02.21 16:00 | 42,033 | 2019.02.26 20:00 | 12,069 | 2009.07.03 00:00 | 4,585 |
| EURCHF | 2026.09.18 07:33 | 70,023 | 2020.02.21 16:00 | 42,033 | 2019.02.26 20:00 | 12,069 | 2009.07.03 00:00 | 4,585 |
| GOLD | 2026.09.16 11:46 | 69,811 | 2020.02.14 15:00 | 40,071 | 2019.02.20 09:00 | 12,150 | 2009.04.20 00:00 | 4,556 |

All 12 requested names exist on XMGlobal-Demo 2 exactly as written, with no suffix: EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, EURGBP, EURJPY, GBPJPY, EURCHF, GOLD.

The M1 counts were still growing by about 1 bar a minute while the run went on. The first dates did not change between the first and second run, so the M1 window is a rolling ~70k bars. **An M1 archive has to be collected forward from now** (for example, rerun the script weekly and keep the `.hst` files) if more M1 is ever needed.

## Symbol specs (MarketInfo, 2026-11-26 02:14 EET)

Account: server `XMGlobal-Demo 2`, company `XM Global Limited`, currency **USD**, leverage **1:1**. Spread is the live spread in points at 02:14, near the daily rollover, so it is wider than in the main sessions. The feed is variable spread. See backtest-data-source.md for the measured spread distribution.

| Symbol | Digits | Point | Spread (pts) | StopLevel (pts) | LotStep | MinLot | MaxLot | Contract | TickValue (USD) | TickSize | Margin / 1 lot (USD) | Swap long / short (pts) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EURUSD | 5 | 0.00001 | 20 | 0 | 0.01 | 0.01 | 50 | 100,000 | 1.000000 | 0.00001 | 109,728.00 | -7.83 / 1.44 |
| GBPUSD | 5 | 0.00001 | 25 | 0 | 0.01 | 0.01 | 50 | 100,000 | 1.000000 | 0.00001 | 131,139.00 | -3.66 / -3.84 |
| USDJPY | 3 | 0.001 | 28 | 0 | 0.01 | 0.01 | 50 | 100,000 | 0.628401 | 0.001 | 100,000.00 | 2.11 / -29.59 |
| USDCHF | 5 | 0.00001 | 29 | 0 | 0.01 | 0.01 | 50 | 100,000 | 1.203138 | 0.00001 | 100,000.00 | 5.11 / -14.26 |
| AUDUSD | 5 | 0.00001 | 24 | 0 | 0.01 | 0.01 | 50 | 100,000 | 1.000000 | 0.00001 | 66,272.00 | -0.46 / -3.75 |
| USDCAD | 5 | 0.00001 | 31 | 0 | 0.01 | 0.01 | 50 | 100,000 | 0.703512 | 0.00001 | 100,000.00 | 1.88 / -9.81 |
| NZDUSD | 5 | 0.00001 | 31 | 0 | 0.01 | 0.01 | 50 | 100,000 | 1.000000 | 0.00001 | 54,866.00 | -4.62 / -0.41 |
| EURGBP | 5 | 0.00001 | 25 | 0 | 0.01 | 0.01 | 50 | 100,000 | 1.311100 | 0.00001 | 109,718.00 | -5.87 / 1.12 |
| EURJPY | 3 | 0.001 | 33 | 0 | 0.01 | 0.01 | 50 | 100,000 | 0.628417 | 0.001 | 109,718.00 | -4.97 / -19.53 |
| GBPJPY | 3 | 0.001 | 42 | 0 | 0.01 | 0.01 | 50 | 100,000 | 0.628409 | 0.001 | 131,123.50 | 3.09 / -40.51 |
| EURCHF | 5 | 0.00001 | 36 | 0 | 0.01 | 0.01 | 50 | 100,000 | 1.203138 | 0.00001 | 109,718.00 | 1.44 / -12.02 |
| GOLD | 2 | 0.01 | 70 | 0 | 0.01 | 0.01 | 50 | 100 | 1.000000 | 0.01 | 357,695.00 | -69.50 / 15.07 |

Notes:
- `MODE_STOPLEVEL = 0` and `MODE_FREEZELEVEL = 0` on every symbol, so stops can go at any distance.
- `MODE_SWAPTYPE = 0` (points). GOLD has `PROFITCALCMODE = 1` (CFD) and `MARGINCALCMODE = 4`. FX is mode 0/0.
- TickValue for non-USD-quote pairs is a live conversion, so it moves with price. Read it at runtime, don't hard-code it.
- **Leverage 1:1** makes the margin per lot equal the notional (EURUSD 1 lot ≈ 109.7k USD). If the backtest or paper engine checks margin, either use these numbers or note that a real account's leverage would differ.
- **Commission:** MT4's `MarketInfo` has no commission field, and commission only shows up on closed deals (`OrderCommission()`). A contract size of 100,000 means a Standard (or Ultra Low Standard) type rather than Micro (1,000). I tried XM's own account-types pages (`https://www.xm.com/account-types` and others). Every one returned 403 or failed to fetch, so **no primary-source commission is recorded here**. Next step: place one 0.01-lot demo trade in the Tester (or by hand), then read `OrderCommission()`, or read XM's account page in a browser.

## Gotchas found

- `iBars`, `iTime` and `CopyTime` at shifts past the oldest cached bar don't make MT4 4 fetch older history. Neither does `ChartNavigate`. Only the chart's Home key (`VK_HOME` posted to the chart window) does. It needs `ExpertsDllImport=true` for the user32 import. This only uses windowing, with no trading DLL.
- A script started from the startup ini runs before the login. `AccountServer()` is empty and the `MarketInfo` fields are 0 at that point, so wait for `IsConnected() && AccountNumber()>0` first.
- No `LiveUpdate` lines appeared in the terminal log during these runs. It's still on build 1492.
