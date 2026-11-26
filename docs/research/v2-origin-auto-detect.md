# V2 Origin auto-detect rule (black-box)

Researched 2026-11-26 for ticket `.scratch/jev-quant/issues/01-v2-origin-auto-detect-rule.md`.
Method: compare the Origins V2 saved against XM price history. The `.ex4` was not opened.
Scripts and frozen data copies live in the session scratchpad (ephemeral): `/tmp/claude-1000/-home-prgzro-Projects-XOR0/205c3630-a6e9-485f-b79e-e22a252b80f3/scratchpad/` (paths below are relative to it).

## Answer

With `AutoDetect=true`, V2 behaves like SQ9-36's rule with a **longer window**:

```
Hi = iHighest(NULL, tf, MODE_HIGH, N, 0)    // shift of the highest high
Lo = iLowest (NULL, tf, MODE_LOW,  N, 0)    // shift of the lowest low
Origin = (Hi > Lo) ? High[Hi] : Low[Lo]     // the OLDER of the two extremes wins
N ≈ 270 bars, bar 0 (the open bar) included   // best fit 269–270; jointly feasible 265–270
```

- **Window N:** every jointly testable symbol fits N in 265–270 only. EURUSD, where the compute minute is known from the log, narrows it to 269 or 270. N = 225, the SQ9-36 value, fails 5 of 5 symbols. N = 270 with bar 0 included is the same as N = 269 with bar 0 excluded. The data can't tell these two apart (see HITL).
- **Older extreme wins, not newer.** This follows SQ9-36's literal code, `if(Hi > Lo)` on shifts. The "newer-wins" variant fits **no** symbol.
- **High vs low (level direction):** follows the extreme that was picked. Equivalently, it is SQ9-36's `Origin > Close[0]` ⇒ high (levels fall), else low (levels rise). For a hand-placed Origin, only the Close test explains the drawn direction (chart07, old sample). So implement the Close test.
- **Timeframe scanned:** each timeframe's own bars. V2 keeps one Origin per timeframe (M1…MN) per symbol. In every sample, Frame equalled the chart timeframe, so whether **Frame ≠ chart TF** changes the scanned series is still open (HITL).
- **Persistence:** the Origin is stored and is not recomputed on every tick. A hand-dragged Origin sticks: in the state file its row has `flag=0`.

Confidence: **high** for "older-wins, ~270 bars, per-TF". **Medium** for the exact N (269 vs 270) and for whether bar 0 is included.

## Evidence

### 1. V2's own state file (the main evidence)

V2 writes `MQL4/Files/AbuHamzah Auto SQ9/AbuHamzah Auto SQ9 <SYMBOL>.txt`: 585 bytes = 9 records × 65 bytes, one per timeframe M1…MN. The layout was inferred by reading the bytes; this is a data file V2 wrote, not its code. Little-endian:

| Offset | Type | Meaning (inferred) |
| --- | --- | --- |
| 0 | int32 | period (1, 5, 15, 30, 60, 240, 1440, 10080, 43200) |
| 13 | double | Origin price |
| 21 | int32 | Origin bar time (server time) |
| 29 / 33 / 37 | int32 | Angle / Time / Space index (8 → 90, 10 → 144, 11 → 180; Space = 10^(idx−2)) |
| 41 | double | Angle |
| 49 | int32 | Time |
| 53 | double | Space |
| 61 | int32 | **flag**: 1 = untouched auto, 0 = user-modified |

`flag=1` rows always have the default Angle 90 / Time 90 / default Space and a real quote price. `flag=0` rows have custom Angle/Space and often a non-quote price (hand-dragged). Example: GOLD D1 `5624.5625`, USDJPY H4 `152.16693771626296`. So `flag=1` rows are auto-detected Origins. Parser: `scratchpad/origin01/st2.py`. Snapshot of all files: `scratchpad/origin01/snap/state/`.

Test: for each symbol, find any single as-of minute T at which one rule reproduces **all** `flag=1` rows at once (each on its own TF's history). Bar 0 at T is taken from the final `.hst` bar. Script: `scratchpad/origin01/c5.py` / `c6.py`.

| Symbol (rows) | History | older-wins, bar 0 in | newer-wins | Joint T found |
| --- | --- | --- | --- | --- |
| EURUSD (8: M1…MN) | `history/XMGlobal-Demo 2/` (Nov 2026) | N 259–270 | none | 2026-11-25 22:59–23:10 |
| AUDUSD (7) | `history/XMGlobal-Demo/` | N 262–300+ | none | 2026-02-26 04:40–05:24 |
| SILVER (7) | same | N 265–285 | none | 2026-02-27 22:50–23:00 |
| GOLD (5) | same | N 264–273 | none | 2026-02-27 22:21–22:30 |
| BTCUSD (6) | same | N 259–273 | none | 2026-03-02 15:57–16:00 |
| **Intersection** | | **N 265–270** | | |

Bar-0-excluded results are the same ranges shifted down by 1.

- **EURUSD pins N.** The terminal log `MQL4/Logs/20261125.log` shows V2 running a per-timeframe loop (`M = 8 … 3`, 9 lines) at 23:09:50 on EURUSD H1 and at 23:10:53 on EURUSD H4. The state file was written at 23:11:23. Its M1 row (1.09558 @ 18:41) fits only N = 269 if computed in the 23:09 minute, or N = 270 in the 23:10 minute. Before 23:09:06 the terminal had no Nov 2026 data: `logs/20261125.log` shows `connect failed [Invalid account]` until the `login on XMGlobal-Demo 2` at 23:09:06.
- The EURUSD higher timeframes need the long window: H1 1.1169 @ 2026-11-11 04:00 sits at shift 259, and MN 1.6038 @ 2008-07 at shift 222. They also need older-wins. W1 picks the 2022-09 low 0.95351 (shift 217) over the newer 2026-01 high 1.2081 (shift 43). MN picks the 2008 high (shift 222) over the newer 2022 low (shift 50). Newer-wins would invert both.
- AUDUSD's joint T (26 Feb 04:40–05:24) matches the first V2 install: the state folder was created 2026-02-26 05:06.
- OIL-APR26 rows fit N = 270 individually, but not at one common T. Its H1 row needs T ≥ 2026-03-06 08:00 while its M1 row needs T ≈ 2026-03-04 23:35. So rows are recomputed separately, presumably whenever that TF is shown in auto mode. This is not a contradiction.
- USDJPY's `flag=1` H4/D1 rows are not real quotes. That fits rows left over from a reset, or edited, but it is unexplained. These rows were excluded.

### 2. Chart-profile samples (from `v2-live-observations.md` + post-restart snapshot)

As-of = `OverlayPrice.time_1 − 40 × period`. All charts' `time_1` values fit TimeCurrent + 40 bars: H4 − H1 = 432000 s = 40 × 3 h, and D1 fits too. The common "now" for the doc's samples is 2026-03-29 01:14 (= GOLD state-file mtime). Post-restart samples come from `scratchpad/profiles-snapshot-0149/` (now = 2026-11-26 01:39). The table gives each sample's verdict under older-wins, N = 270.

| Sample | Origin | Real bar H/L? | Verdict |
| --- | --- | --- | --- |
| chart01 EURUSD H4 | 1.208100 H @ 01-27 20:00 | yes (High) | fits (as-of window 2026-03-03 … 03-27) |
| chart04 GBPUSD H1 | 1.321750 L @ 03-13 22:00 | yes (Low) | fits (as-of ≈ 03-25 … 03-27) |
| chart06 EURUSD H4 (old) | 1.150600 L @ 03-09 00:00 | yes (Low) | **does not fit** (only N ≤ 45); likely magnet-snapped hand drag |
| chart06 EURUSD H4 (new) | 1.088010 L @ 11-23 16:00 | yes (Low) | **does not fit** at 11-26 01:39 (only N ≤ 16). State file shows a user drag on this exact bar (`P240 flag=0 1.087865 @ 11-23 16:00`), so this is a hand drag snapped to the low |
| chart07 EURUSD H1 (new) | 1.088010 L @ 11-23 19:00 | yes (Low) | **does not fit** (only N ≤ 63; auto at that time would be 1.1169 H); likely hand drag |
| chart02 GBPUSD H1 | 1.348087 | no (6 dp) | hand-dragged |
| chart03 GOLD D1 | 5585.634821 | no | hand-dragged |
| chart05 NGAS-APR26 H4 | 3.472187 | no (3-dp symbol) | hand-dragged; same value in NGAS state row `P240 flag=0` |
| chart07 EURUSD H1 (old) | 1.150251 | no | hand-dragged |

NGAS-APR26 history exists (`NGAS-APR26240.hst`, to 2026-03-23); it is not missing.

An exact high/low match does not prove an Origin was auto-detected. MT4's object magnet snaps a dragged line to a bar's OHLC. The state file's `flag` is the reliable marker.

**Direction check.** Every profile's drawn direction equals `Origin > Close(as-of) ⇒ high`. Examples: chart06-old 1.1506 < close 1.15092 ⇒ rising. chart07-old 1.150251 > Nov close ≈ 1.0975 ⇒ falling, even though it sits at a swing *low*. That last case rules out "direction = swing type" for dragged Origins.

### 3. Reference source

`indcators/AbuHamzah Auto SQ9-36.mq4` (UTF-16), lines 87–95: `iHighest(NULL,0,MODE_HIGH,225,0)`, `iLowest(…225,0)`, `if(Hi > Lo){Overlay = iHigh(…Hi)}else{Overlay = iLow(…Lo)}`. Since `Hi`/`Lo` are shifts, `Hi > Lo` means the high is older, so **the older extreme wins**. The ticket's premise ("more recent wins") is a misreading. Lines ~245–255: `if(OverlayPrice > Close[0]) IsLowPrice = false; else true;` when AutoDetect. An existing `SQ9 OverlayPrice` object overrides the computed value (`FindPrice`). V2 keeps this design and changes the window from 225 to ≈270.

### 4. Web sources

No primary source on V2's auto-detect was found. The web searches returned nothing about AbuHamzah Auto SQ9. `https://www.shoqi.net` returned HTTP 403, and `https://www.abuhamzah.ws` refused the connection (both 2026-11-26).

## Open points (HITL)

Each needs a human at the user's MT4 (XMGlobal-Demo 2), with the times noted to the minute.

1. **N = 269 vs 270, bar 0 in or out.** On EURUSD M1, press V2's Reset (auto) button at a noted server minute T. Then read `AbuHamzah Auto SQ9 EURUSD.txt` (M1 row) and export M1 history. The test is: is the Origin the older of HH/LL over 270 bars counting the open bar? Repeat 2–3 times at minutes where 269 and 270 give different answers. The script `c5.py` can pick such minutes beforehand.
2. **Does the Time setting drive N (270 = 3 × 90)?** Every auto row seen had Time = 90. Set Time to 45 or 120 on one TF, Reset, and check whether the window becomes 135 or 360.
3. **Frame ≠ chart TF.** On an H1 chart set Frame = H4 (not Fix), Reset. Record which TF's bars and which state row the Origin comes from.
4. **Were chart06/chart07's 1.08801 Origins dragged?** Ask the user. If not, V2 has a second placement path, for example the "Reset Origin" (`CP_ResetO`) button, that needs its own test.

## Live pinning (ticket 13)

Done on 2026-11-26, 03:20–03:57 server time, in the isolated terminal only (`WINEPREFIX=~/.wine-jevquant`, `C:\JevQuantMT4`, demo). V2's `.ex4` was copied read-only from the user's install into the isolated `MQL4\Indicators\` and was not decompiled. No human clicks were needed.

### Answers

| Question | Answer | Confidence |
| --- | --- | --- |
| (a) 269 or 270 bars | **270 bars, shifts 0…269.** Over 141 auto rows from 22 fresh attaches, this is the only window in N = 150…400 that fits every row. 269, 271 and the bar-0-excluded variants each fail several rows. | **High** |
| (b) bar 0 included | **Yes.** The open bar counts. 39 of the 141 rows separate "0…269" from "1…269" or "1…270", and every one of them needs bar 0 (typically the newest bar's open is a new extreme, which makes the *other* extreme the older one). | **High** |
| (c) does the panel's Time drive the window | **No, not on any path that computes an auto Origin.** Changing Time (90 → 120 → 144, or → 72 → 60 → 45) never moved the Origin. **Reset puts Time back to 90** and recomputes, so a non-90 window is never used. A fresh attach also starts at Time 90. "270 = 3 × 90" can't be told apart from "a fixed 270", and for us the difference doesn't matter: the window is always 270. | High for the behaviour; the internals are unknowable |
| (d) Frame ≠ chart TF | **Frame picks both the scanned series and the state row, and the chart TF doesn't matter.** On an H1 chart with Frame = H4, Reset gave the H4-bar N = 270 Origin (1.14100 @ 09-25 16:00, exactly the H4 rule) and not an H1 one. Frame = D1 gives the D1 row. Frame can't be set **below** the chart TF (Frame ▼ on an H1 chart stays at H1). | High |

Two more findings change how V2 should be read:

- **Ties go to the older bar.** When two bars share the extreme price, V2 takes the older one. That is `>=` while walking from new to old, not MT4 `iHighest`'s first hit. Three rows need this rule (for example M1 on 10-19, 1.12392 at 23:00, not 23:57). If the history is shorter than 270 bars, the window just shrinks to what is there (M30 rows in the tester).
- **V2 does not recompute a stored Origin on its own.** In the Tester the Origin stayed fixed for **864 H1 bars**, Oct 1–Nov 20. Deleting the `OverlayPrice` object made V2 redraw it from its stored row, not recompute it. Live, a seeded stale row (09-16 H1 Origin, far outside the window) stayed on screen through attach, Time changes and Frame switches until **Reset** was clicked. An auto Origin is only computed (1) at attach, for a TF with **no row** in the state file, or (2) on **Reset**, for the Frame TF. Rows with `flag=1` and even `origin=0` are loaded as they are. This contradicts ticket 03's premise that "V2 repaints constantly". That premise came from replaying the rule bar by bar. V2 itself shows whatever was computed at attach or last Reset (live repainting across a new bar wasn't watched directly; the Tester shows none). The confirmed-Origin policy (rule on `shift 1`, freeze per setup) is still a sound design for our EA. The thing it does *not* do is match V2's screen bar for bar.

So the rule to mirror is: `Origin = older of (highest High, lowest Low) over shifts 0…269 of the Frame TF, ties → older bar, evaluated at the moment of attach or Reset`. As before, direction comes from Origin vs `Close[0]`.

### How it was driven (reproducible, no GUI)

1. **Tester route (main evidence).** `MQL4\Experts\JevQuant\JevQuantV2Probe.mq4` calls `iCustom(NULL,0,"AbuHamzah Auto SQ9 V2 ",0,0)` on each tick and logs the `AbuHamzah Auto SQ9 OverlayPrice` object, all objects, and each TF's bar 0 as the Tester sees it at the first tick. V2 computes fully inside the Tester. It loops its TFs (`M = 8 … 3` in the journal, about 2 s each) and writes all 9 rows to `tester\files\AbuHamzah Auto SQ9\AbuHamzah Auto SQ9 EURUSD.txt`. I deleted that file before every run, so each run is one fresh attach at the first tick of `TestFromDate`. Runner: `runv2.sh <tag> EURUSD H1 <from> <from+2d> 2 0 5 0`. Ini keys: `TestExpert`, `TestExpertParameters=<file>.set` (in `tester\`), `TestModel=2`, `TestShutdownTerminal=true`, `ExpertsTrades=false`. 22 dates from 2026-09-23 to 2026-11-24, EURUSD. The fit used the deep `.hst` files from ticket 15 (`fit2.py`, `TIE=old`). Note: `TestFromDate == TestToDate` gives "no data for testing", so use at least one more day.
2. **Live route (Reset / Time / Frame).** The script `MQL4\Scripts\JevQuant\JevQuantV2Click.mq4` is started by a startup ini (`Script=JevQuant\JevQuantV2Click`, `ScriptParameters=<file>.set` in `MQL4\Presets`, `ExpertsDllImport=true`, `ExpertsDllConfirm=false`, `ExpertsTrades=false`). It waits for the login, optionally deletes V2's state file, then `ChartOpen`s a chart and `ChartApplyTemplate(cid,"jqv2.tpl")`. The template is V2 with its default inputs, plus `ControlYpos=5`. It then **clicks panel buttons** by posting `WM_LBUTTONDOWN/UP` to `CHART_WINDOW_HANDLE` at each button's centre, computed from `OBJPROP_XDISTANCE/YDISTANCE/XSIZE/YSIZE` and `CORNER=1`. After each step it logs the Origin object and the panel texts (`CP_TimeE`, `CP_FrameT`, …). The headless chart is only about 220 px tall, so with the default `ControlYpos=100` the Reset/ResetAll buttons (y ≈ 220–240) fall off-screen and the clicks miss. Move the panel up.
3. **Live sanity check.** A fresh live attach at 03:36 (H1 chart, all 9 rows) is consistent with the same rule. All 9 rows fit 0…269 with live, developed bar-0 highs and lows. Ticks don't separate the variants at that minute.

Panel facts seen in the object dump: Time steps … 45, 60, 72, 90, 120, 144 …. The Frame label shows the TF name next to a `Fix` button. Reset = `CP_ResetO*`, ResetAll = `CP_ResetA*`. The state-file Time index (offset 33) follows the list (72 → 7, 90 → 8, 180 → 11).

### Artifacts (session scratchpad, ephemeral)

`/tmp/claude-1000/-home-prgzro-Projects-XOR0/205c3630-a6e9-485f-b79e-e22a252b80f3/scratchpad/mt4-tasks/`:
- `v2runs/d2026MMDD/`: per-attach state file, `v2_bar0_*.csv`, `v2_origin_*.csv`, `v2_objects_*.csv`.
- `live1/`: `click_EURUSD_60*.csv/.bin` (live Reset/Time/Frame logs and state files).
- `fit2.py` (window fit + discriminating rows), `rulenow.py`, `st3.py` (state-file decoder), `runv2.sh`, `src/` (MQL4 sources, inis, template).

The sources also stay in the isolated copy under `MQL4\Experts\JevQuant\`, `MQL4\Scripts\JevQuant\` and `templates\jqv2.tpl`.

### Remaining HITL

None is needed for (a)–(d). Optional: ask the user whether they ever click Reset. If V2 on their charts only computes at attach, the Origins they trade from are "as of attach or Reset", which matches the frozen-Origin policy better than a rolling rule.
