# MT4 test harness under Wine

Research for ticket `.scratch/jev-quant/issues/04-mt4-test-harness-under-wine.md`. Probed on 2026-11-26. Host: Linux, `wine-9.0`, `DISPLAY=:1` (Wayland session with XWayland), no Xvfb installed, Node v22.

> **Correction (2026-11-26, from [backtest-data-source.md](backtest-data-source.md)):** MT4 silently ignores `/config:<ini>`, and the test never starts. The working form is a bare relative path: `WINEPREFIX=/home/prgzro/.wine-jevquant timeout 900 wine terminal.exe /portable 'config\jq_everytick.ini'`. Read every `/config:` command below as that form. The leftover `~/.wine/drive_c/JevQuantMT4` copy has been deleted.

## TL;DR

| Need | Status | How |
| --- | --- | --- |
| (a) Headless compile | **Works**, proven | `wine metaeditor.exe /compile:<file> /log[:<file>]`. Takes about 0.8 s and needs no display. **The exit code is inverted** (1 = compiled, 0 = failed), so parse the UTF-16LE log instead. |
| (b) Tester from `/config:` ini | **Blocked on one HITL login** | Use an isolated Wine prefix `~/.wine-jevquant` holding a portable copy at `C:\JevQuantMT4`. The terminal starts, but it shows a modal "Open an Account" wizard until an account has been saved once. |
| (c) Results | Documented; tester side not yet observed | Normal runs write to `<data>\MQL4\Files\`; tester runs write to `<data>\tester\files\`. Compile logs are UTF-16LE with a BOM. Terminal journals are single-byte ANSI. |
| (d) Node mirror | **Recommended** | Use pure `sq9.mjs` and state-machine modules with `node:test`. Check parity with an MQL4 dumper EA that writes CSV for shared fixtures, and have a Node test compare within 1e-9 relative. A working Node side exists. |

**Incident to know about:** the first probe ran a copy inside the user's *shared* prefix `~/.wine`. MT4 LiveUpdate (build 1470 → 1492, already downloaded by the user's own terminal on 2026-11-25 23:17) fired for the copy. About 20 s later the user's terminal logged `build 1470 stopped` (01:39:58). It was then restarted at 01:40:51, and LiveUpdate updated it to **build 1492** and restarted it with `/skipupdate:<token>`. It is running again (on 1492), and its profiles and config were not edited by the agent. I can't prove the causal chain, but the lesson holds: **never run a second terminal in `~/.wine`**. Use a separate `WINEPREFIX`, which has its own wineserver, window station and `AppData\Roaming\MetaQuotes\WebInstall` updater cache.

## (a) Headless compile

### Sources
- MetaEditor help, "Integration with other IDEs" (command-line compilation): `metaeditor.exe /compile:"<full path to the source file>"`. A folder path mass-compiles (without subfolders, and only stale files). `/include` sets a custom MQL folder. `/log` writes `<source>.log` next to the source. `/s` together with `/log` is a syntax check only. https://www.metatrader5.com/en/metaeditor/help/beginning/integration_ide (MT5 docs; the MT4 build-1470/1492 `metaeditor.exe` accepts the same keys, verified below).

### Commands that worked

Run from the terminal folder, with paths relative to it:

```bash
cd "$HOME/.wine/drive_c/Program Files (x86)/XM Global MT4"
timeout 120 wine metaeditor.exe \
  /compile:"MQL4\\Scripts\\JevQuantProbe\\ProbeInclude.mq4" \
  /log:"MQL4\\Scripts\\JevQuantProbe\\ProbeInclude.log"
echo $?   # 1 on success
```

With absolute paths from anywhere, a source tree outside the terminal, and the isolated prefix:

```bash
export WINEPREFIX=$HOME/.wine-jevquant
SRC=$(winepath -w /path/to/repo/mql4/MQL4/Experts/Foo.mq4)
timeout 120 wine 'C:\JevQuantMT4\metaeditor.exe' /portable /compile:"$SRC" /log:"$(winepath -w /tmp/foo.log)"
```

`winepath -w` maps `/home/...` to `Z:\home\...`.

### Observed behaviour
- **Exit code = number of files successfully compiled.** Clean compile → `1`. Syntax error → `0`. This is the reverse of the Unix convention. The MetaEditor docs don't document it, so treat it as a hint only and **gate on the log's `Result:` line**.
- **Log format:** UTF-16LE with a BOM and CRLF line endings. Decode with `iconv -f UTF-16LE -t UTF-8` or `Buffer#toString('utf16le')`. Example lines:
  ```
  MQL4\Scripts\JevQuantProbe\ProbeInclude.mq4 : information: compiling 'ProbeInclude.mq4'
  MQL4\Scripts\JevQuantProbe\ProbeMath.mqh : information: including 'ProbeMath.mqh'
  Result: 0 errors, 0 warnings, 87 msec elapsed
  ```
  On failure:
  ```
  MQL4\Scripts\JevQuantProbe\ProbeBroken.mq4(2,25) : error 157: ';' - expression expected
  MQL4\Scripts\JevQuantProbe\ProbeBroken.mq4(2,21) : warning 31: variable 'x' not used
  Result: 1 errors, 1 warnings
  ```
  Diagnostic regex: `^(.+)\((\d+),(\d+)\) : (error|warning) (\d+): (.*)$`. Success means the log contains `Result: 0 errors`.
- `/s` gives a syntax check only (`checking ...`, `result 0 errors`) and writes **no `.ex4`**. Don't use it for builds.
- **Include resolution:** with no `/include`, MetaEditor resolved `#include <JQ/Lib.mqh>` against the `MQL4\Include` *next to the source's own `MQL4` folder* (a tree under the scratchpad), and fell back to the terminal's `MQL4\Include` for `<stdlib.mqh>`. Passing `/include:<other>\MQL4` **replaced** the include root, so `<stdlib.mqh>` was then not found (error 106). Recommendation: keep repo sources in an `MQL4/` tree (`MQL4/Experts`, `MQL4/Include/JevQuant`) and either compile in place without `/include`, or sync the tree into the terminal copy and compile there. Quoted includes (`#include "x.mqh"`) resolve relative to the source file.
- **No display needed:** `env -u DISPLAY -u WAYLAND_DISPLAY wine metaeditor.exe /compile:...` worked.
- Compiling in the user's live terminal tree while it was running caused no visible side effect. Even so, the harness should compile inside the isolated copy.
- Each compile takes about 0.7–0.8 s wall time, warm.

Probe sources (left in place, harmless): `~/.wine/drive_c/Program Files (x86)/XM Global MT4/MQL4/Scripts/JevQuantProbe/` (`ProbeHello`, `ProbeInclude` + `ProbeMath.mqh`, `ProbeBroken`).

## (b) Running scripts / Strategy Tester from `/config:`

### Sources
- MT4 help, "Configuration at Startup": keys `Login`, `Password`, `Server`, `EnableNews`, `ExpertsEnable`, `ExpertsTrades`, `Symbol`, `Period`, `Expert`, `ExpertParameters`, `Script`, `ScriptParameters`, and the tester keys `TestExpert`, `TestExpertParameters` (file in `/tester`), `TestSymbol`, `TestPeriod` (`M1..MN`), `TestModel` (0 every tick, 1 control points, 2 open prices), `TestSpread`, `TestOptimization`, `TestDateEnable`, `TestFromDate`/`TestToDate` (`YYYY.MM.DD`), `TestReport` (relative to the terminal dir, `.htm` added), `TestReplaceReport`, `TestShutdownTerminal`, `TestVisualEnable`. `Password` is ignored if the account's data is already stored. https://www.metatrader4.com/en/trading-platform/help/service/start_conf_file
- MT5 help, "Platform Start": `/portable` keeps all data in the install folder. "Two copies of the platform cannot run from the same directory." `/config:` files are read-only. https://www.metatrader5.com/en/terminal/help/start_advanced/start (the MT4 page shows only the bare-filename form, but `/config:` and `/portable` were accepted by MT4 build 1470/1492: the copy logged `Data Folder: C:\JevQuantMT4`).

### What was tried
1. **Copy in the shared prefix** (`~/.wine/drive_c/JevQuantMT4`, `/portable /config:C:\JevQuantMT4\config\jq_tester.ini`). The copy started (`Data Folder: C:\JevQuantMT4`) and **logged in by itself** to the user's demo account on `XMGlobal-Demo 2`, even though I did not copy `accounts.ini`. LiveUpdate then closed it, replaced the copy's `terminal.exe`/`metaeditor.exe` with build 1492, and relaunched it without the config. This is the incident described above. Abandoned. This directory remains at `~/.wine/drive_c/JevQuantMT4` (63 MB) and should be deleted by the user. It must not be run again.
2. **Isolated prefix** (the recommended layout):
   ```bash
   export WINEPREFIX=$HOME/.wine-jevquant
   timeout 180 wineboot -i
   # C:\JevQuantMT4 = terminal.exe + metaeditor.exe (build 1492) + MQL4/ + config/servers.ini
   #   + history/{XMGlobal-Demo,XMGlobal-Demo 2}/{symbols.raw,symbols.sel,symgroups.raw,EURUSD60.hst}
   cd "$WINEPREFIX/drive_c/JevQuantMT4"
   timeout 180 wine terminal.exe /portable /config:'C:\JevQuantMT4\config\jq_tester.ini'
   WINEPREFIX=$HOME/.wine-jevquant wineserver -k   # cleanup; only touches this prefix
   ```
   with `config/jq_tester.ini` (CRLF):
   ```ini
   TestExpert=JevQuantProbe\ProbeTesterEA
   TestSymbol=EURUSD
   TestPeriod=H1
   TestModel=2
   TestSpread=10
   TestOptimization=false
   TestDateEnable=false
   TestReport=tester\jq_report
   TestReplaceReport=true
   TestShutdownTerminal=true
   TestVisualEnable=false
   ExpertsEnable=false
   ExpertsTrades=false
   EnableNews=false
   ```
   The terminal starts cleanly with no LiveUpdate, and the user's terminal is unaffected. But with no saved account it opens the modal **"Open an Account / Select a more suitable trading server"** wizard, Market Watch is empty, the status bar shows "No connection", and **the test never starts**. The run ended by timeout (exit 124) with no `tester/files` output and no report. Screenshot evidence: `/tmp/claude-1000/-home-prgzro-Projects-XOR0/205c3630-a6e9-485f-b79e-e22a252b80f3/scratchpad/copy_dlg.png`.

### HITL step required (one-time)
The isolated terminal needs a saved **demo** login before the tester will run unattended:

```bash
WINEPREFIX=$HOME/.wine-jevquant wine 'C:\JevQuantMT4\terminal.exe' /portable
```

In the window: pick `XMGlobal-Demo` or `XMGlobal-Demo 2`, then either log in to an existing demo account or (preferably) **open a fresh demo account dedicated to the harness**. Tick "Save account information", wait for the connection and for Market Watch to fill, then File → Exit. This writes encrypted credentials to `C:\JevQuantMT4\config\accounts.ini`. After that, `/config:` runs should start the test without dialogs. A credential-free alternative is to put `Login=`, `Password=` and `Server=` in the startup ini, but that leaves a plaintext password on disk, so prefer the saved login.

Then do these once, after the login:
- Set the tester `Expert properties → Testing` to **Long & Short** and leave "Allow live trading" (`ExpertsTrades`) off. The tester simulates trades regardless; live trading never applies inside the Tester.
- Re-run `jq_tester.ini`. Expected outputs are `tester\files\JevQuantProbe\tester_out.csv` and `jq_report.htm` in the terminal folder. Neither has been observed yet.

### Display
`DISPLAY=:1` exists, so terminal windows appear on the user's desktop. Xvfb isn't installed. Optional HITL step to keep harness windows off-screen: `sudo apt install xvfb`, then `xvfb-run -a env WINEPREFIX=$HOME/.wine-jevquant wine ...`. The terminal is a GUI app and needs *some* X server. Only the compiler runs without one.

### Other notes
- History must be in `history/<server name>/`, where the server name is the **one actually logged into**. The user's account is on `XMGlobal-Demo 2`, not `XMGlobal-Demo`. The tester reads `<SYMBOL><period>.hst` plus `symbols.raw` from that folder. `EURUSD60.hst` is only 135 KB (about 2.2k H1 bars). Longer backtests need history downloaded in the copy (History Center, F2) or `.hst` files copied from the user's tree.
- After a run the tester writes `tester/lastparameters.ini`. `TestShutdownTerminal=true` closes the terminal when the test ends, so `timeout N wine terminal.exe ...` returns when the test finishes. Always wrap it in `timeout` and finish with `wineserver -k` **for the isolated prefix only**.
- Scripts: `Script=JevQuantProbe\ProbeHello` with `Symbol=EURUSD` and `Period=H1` in the startup ini runs a script on a chart after startup. That needs a connected account too, and it has not been run yet.

## (c) How results come back

| Artifact | Path (portable copy) | Encoding / format | Source |
| --- | --- | --- | --- |
| `FileOpen` from a script/EA (live chart) | `C:\JevQuantMT4\MQL4\Files\<relpath>` | Whatever you request. Always pass `FILE_ANSI` (or `FILE_UNICODE`) explicitly | MQL4 `FileOpen`: "opened in ... MQL4\files (or Tester\Files in case of testing)". https://docs.mql4.com/files/fileopen |
| `FileOpen` inside the Strategy Tester | `C:\JevQuantMT4\tester\files\<relpath>`. Fixtures an EA reads must be pre-placed here | same | same |
| `FILE_COMMON` | shared `...\AppData\Roaming\MetaQuotes\Terminal\Common\Files` **of that prefix** | same | same |
| Tester report | `TestReport=` path, relative to the terminal folder, with `.htm` appended | HTML (MetaQuotes template `templates/StrategyTester.htm`) | start_conf_file page |
| Terminal journal | `logs\YYYYMMDD.log` | **ANSI single-byte, CRLF, TAB-separated** (`0\t01:37:50.650\tMetaTrader 4 build 1470 started`). Not UTF-16 | observed |
| Tester journal | `tester\logs\YYYYMMDD.log` | expected same as journal | not observed (no run completed) |
| EA `Print()` output (live) | `MQL4\Logs\YYYYMMDD.log` | ANSI | observed in the user's tree |
| Compile log | `/log:` path, or `<source>.log` | **UTF-16LE + BOM, CRLF** | observed |
| MetaEditor's own log | `logs\metaeditor.log` | UTF-16LE (mostly blank lines) | observed |

The terminal flushes its journal lazily. For machine-readable results, prefer an explicit CSV/JSONL written with `FileOpen` and closed in `OnDeinit`, rather than scraping logs.

## (d) Node mirror and parity check

**Recommendation: yes.** Mirror the pure parts in Node and keep MQL4 as the source of truth for execution.

- **What to mirror:** the SQ9 level maths (`level(θ) = (√(Origin×Space) + d·θ/180)² / Space`, from `docs/research/v2-live-observations.md`) and the `SQ9_90_BREAKOUT_RETEST` state machine as a pure transition function `(state, bar, levels, params) → (state', events)`. Both are deterministic and need no broker state. The Node bridge needs the levels and states anyway (Jev snapshot, PAPER fills, replay), so the code earns its place beyond testing.
- **Why:** `node:test` runs in about 50 ms with no Wine, display, login or updater risk. The MT4 tester loop is minutes long and currently gated on the HITL login.
- **Keep the MQL4 side testable the same way:** put the maths and transition function in `MQL4/Include/JevQuant/*.mqh` with no `Symbol()`/order calls inside, so the same code is driven by the EA *and* by a dumper.
- **Parity check design (built and partly proven):**
  1. Shared fixtures `fixtures.csv` (`case,origin,space,theta,dir,expected`), seeded from the V2 evidence table (6 rows, to 6 dp).
  2. Node test `sq9.test.mjs`: asserts `sq9Level` matches `expected` within 5e-7 (**passes**). A second test reads `MQL4_LEVELS_CSV` (when present) and asserts Node vs MQL4 agree within `1e-9 × max(1,|x|)`. It is skipped when the file is absent.
  3. MQL4 dumper `MQL4/Experts/JevQuantProbe/ParityDump.mq4` (+ `MQL4/Include/JevQuant/Sq9.mqh`) **compiles cleanly**. In `OnInit` it reads `tester\files\JevQuantProbe\fixtures.csv` and writes `mql4_levels.csv` with `DoubleToString(x,12)`. It is an EA, not a script, so it runs inside the Strategy Tester (no live chart, no trading). It runs as soon as the HITL login is done: `sed 's/ProbeTesterEA/ParityDump/' jq_tester.ini > jq_parity.ini`, then `MQL4_LEVELS_CSV=.../tester/files/JevQuantProbe/mql4_levels.csv node --test`.
  4. For the state machine, use the same pattern. Fixture bar sequences (OHLC rows + Origin) go in, and the dumper writes one row per bar (`bar_time,state,event,level_idx`). Node replays the same rows and diffs them exactly. States are discrete, so require exact equality, with tolerance only on the price columns.
- Tolerances: both sides use IEEE-754 doubles. `MathSqrt` and `Math.sqrt` are correctly rounded, so differences should be ≤ 1 ulp. 1e-9 relative is generous. Compare at **full precision** (12 dp), not at `Digits`, so rounding drift shows up.

Working Node files (throwaway, copy into the repo when building): `/tmp/claude-1000/-home-prgzro-Projects-XOR0/205c3630-a6e9-485f-b79e-e22a252b80f3/scratchpad/parity/{sq9.mjs,sq9.test.mjs,fixtures.csv}`. The isolated copy already holds `ParityDump.ex4`, `Sq9.mqh` and `tester\files\JevQuantProbe\fixtures.csv` under `~/.wine-jevquant/drive_c/JevQuantMT4/`.

## Proposed harness shape (for the spec)

1. `npm test` → `node --test` (pure maths + state machine). Fast, runs on every change.
2. `scripts/mt4-compile.sh <file.mq4>` → isolated prefix, `metaeditor.exe /portable /compile /log`. Decodes UTF-16 and fails if the log lacks `Result: 0 errors`. Ignores the exit code.
3. `scripts/mt4-tester.sh <ini>` → copies fixtures into `tester\files`, runs `timeout N wine terminal.exe /portable /config:...` (optionally under `xvfb-run`), then `wineserver -k` for that prefix, collects `tester\files\*` + the report, and runs the parity tests.
4. Hard rules: `WINEPREFIX=$HOME/.wine-jevquant` is always set (assert it in the script). Never touch `~/.wine`. `ExpertsTrades=false` in every ini. Demo account only.

## HITL checklist
1. **Delete** `~/.wine/drive_c/JevQuantMT4` (the shared-prefix copy; leaving it is harmless, but it must never be run). Optionally delete the probe folder `.../XM Global MT4/MQL4/Scripts/JevQuantProbe/`.
2. **Log in once** to a demo account in the isolated copy with "Save account information" (command above). A dedicated new demo account is preferred.
3. Optional: `sudo apt install xvfb` so harness windows stay off the desktop.
4. Note that the user's MT4 is now **build 1492**. LiveUpdate updated it at 01:40:58 after it was closed and restarted.
