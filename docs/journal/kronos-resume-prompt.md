Continue the Kronos Edge test. Read these first:
- docs/journal/kronos-edge-test.md (status board and the latest entries, from "Fri 2026-11-27")
- docs/research/kronos-edge-test.md (the pre-registration and disclosed deviations D1–D3)

Where we are: the in-sample Forecasts (2010–2019, 7 majors) are 66 of 70 symbol-years done. Only NZDUSD 2016–2019 are left. I rebooted the laptop to fix the NVIDIA driver, which was stuck at a 20 W power cap after a suspend.

Do this, in order:
1. Check the GPU is back to normal: nvidia-smi shows a power limit of 50 W, not 20 W. Check the charger is plugged in. If the GPU is still capped, stop and tell me.
2. Start the safety watch in the background: spikes/kronos/scripts/safety_watch.sh. It pauses the job if CPU ≥ 95 °C, GPU ≥ 87 °C, the charger is unplugged, or disk < 5 GB.
3. Finish the remaining years from spikes/kronos, in the background:
   FROM=2010-01-01 TO=2020-01-01 SYMBOLS=NZDUSD ./scripts/run_pre_oos.sh >> results/run_is.log 2>&1
   (it skips the files that already exist). Expect about 8.68 Forecasts/s and about 12 min per year.
4. When it finishes, check all 70 files, then smoke-test evaluate.py (it has never been run) and run the in-sample selection:
   .venv/bin/python scripts/evaluate.py --forecasts results/forecasts/small_n30 --stage select
5. Before unsealing the out-of-sample window, ask me whether to commit D1–D3 first (my plan is yes).
   The exam must use its own folder: --out results/forecasts/small_n30_oos --unseal fcbef95.

Rules:
- English only.
- Update the journal at every step.
- Never change the pre-registered rules.
- Never trade live (PAPER only).
- Never commit secrets.
- Never touch indcators/ or ~/.wine.
- Commit only when I say so.
- When I ask "tell the progress NOW ?", report progress, ETA and the safety readings.
