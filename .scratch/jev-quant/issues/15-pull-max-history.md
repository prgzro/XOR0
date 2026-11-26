# Pull maximum XM history into the isolated terminal

Type: task
Status: resolved
Blocked by: 

## Question

How many years of M1/H1/H4/D1 history will XM's server provide for the FX + GOLD symbol list? Pull as much as it gives into the isolated terminal (`WINEPREFIX=~/.wine-jevquant` only) without GUI clicks: raise "Max bars in history/chart" in its terminal.ini, then run an MQL4 script that pages back with `iTime`/`iBars` per symbol and timeframe until the server stops returning more. Record first-bar dates and bar counts per symbol and timeframe. The edge re-test (ticket 14) needs this.

## Answer

XM's server serves a fixed number of bars per timeframe, the same for all 11 FX pairs: **M1 ≈ 70k bars (rolling, about 10 weeks, back to 2026-09-18)**, **H1 42,032 (back to 2020-02-21, ≈ 6.8 y)**, **H4 12,069 (back to 2019-02-26, ≈ 7.7 y)**, **D1 4,585 (back to mid-2009)**. GOLD is about the same. The oldest bar pulled equals `SERIES_SERVER_FIRSTDATE` everywhere, and H1/H4 have no holes beyond holidays. All of it is now in the isolated `history\XMGlobal-Demo 2\*.hst`.
Paging only works through a simulated Home key on a chart (`PostMessageW VK_HOME`). `iBars`/`CopyTime`/`ChartNavigate` don't fetch older bars. The max-bars options live in binary `config\charts.ini` (offsets 0x14/0x18).
Specs are captured: Standard contract (100k, GOLD 100), lot 0.01–50 step 0.01, stop level 0, account USD at **1:1 leverage**. Commission isn't exposed and no primary XM source could be fetched (403).
[write-up](../../../docs/research/xm-history-depth.md)
