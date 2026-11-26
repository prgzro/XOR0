# MT4 test harness under Wine

Type: research
Status: resolved
Blocked by: 

## Question

How can the agent compile and test MQL4 automatically on this machine? Establish: (a) headless compile via `wine metaeditor.exe /compile:... /log` (and include paths), (b) running scripts / the Strategy Tester from a `terminal.exe /config:` ini without disturbing the user's running terminal (a second portable copy?), (c) how test results come back (files in `MQL4/Files`, tester reports), (d) whether the SQ9 maths and state machine should also be mirrored in Node for fast unit tests, and what the parity check between them would be. Prove each with a trivial example; don't touch the user's profiles or running terminal.

## Answer

- **Compile works headless.** `wine metaeditor.exe /compile:"<file>" /log:"<file>"` takes about 0.8 s and needs no display. The exit code is inverted (1 = ok, 0 = failed), so gate on the UTF-16LE log's `Result: 0 errors` line instead. `/s` only checks syntax and writes no .ex4.
- **Tester is blocked on one HITL step.** Run it from a portable copy in a separate `WINEPREFIX=~/.wine-jevquant` (`C:\JevQuantMT4`, `/portable /config:`). The copy starts, but it shows a modal "Open an Account" wizard until a demo login has been saved once. A copy inside the shared `~/.wine` triggered LiveUpdate, and the user's terminal was closed and auto-updated to build 1492. Never run a second terminal in `~/.wine`.
- **Results come back as files.** Normal runs write to `MQL4\Files`. Tester runs write to `tester\files`, and the report goes to `TestReport` (.htm). Journals are ANSI; compile logs are UTF-16LE.
- **Node mirror recommended.** Mirror the SQ9 maths and the state machine in Node with `node:test`. Check parity with an MQL4 dumper EA (`ParityDump`, which compiles) that writes CSV for shared fixtures, and compare in Node within 1e-9 relative.
- Details: [docs/research/mt4-test-harness.md](../../../docs/research/mt4-test-harness.md)
