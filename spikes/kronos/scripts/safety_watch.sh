#!/usr/bin/env bash
# Safety watch for the Kronos Forecast run. Every 60 s it logs temperatures. If a limit is
# exceeded for 3 readings in a row (or the charger is unplugged, or the disk is nearly full),
# it PAUSES the Forecast process with SIGSTOP (resumable, no work lost) and exits.
LOG=/home/prgzro/Projects/XOR0/spikes/kronos/results/safety_watch.log
CPU_MAX=95; GPU_MAX=87; DISK_MIN_GB=5; NEED=3
bad=0
while true; do
  pid=$(pgrep -f "scripts/run_forecasts.py" | head -1)
  if [[ -z "$pid" ]] && ! pgrep -f run_pre_oos.sh >/dev/null; then
    echo "$(date -u +%FT%TZ) forecast job finished; watch ends" | tee -a "$LOG"; exit 0
  fi
  cpu=$(sensors 2>/dev/null | awk '/Package id 0/ {gsub(/[+°C]/,"",$4); print int($4)}')
  gpu=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits 2>/dev/null | head -1)
  power=$(cat /sys/class/power_supply/*/status 2>/dev/null | head -1)
  disk=$(df -BG --output=avail / | tail -1 | tr -dc 0-9)
  reason=""
  (( ${cpu:-0} >= CPU_MAX )) && reason="CPU ${cpu}C >= ${CPU_MAX}C"
  (( ${gpu:-0} >= GPU_MAX )) && reason="$reason GPU ${gpu}C >= ${GPU_MAX}C"
  [[ "$power" == "Discharging" ]] && reason="$reason charger unplugged"
  (( ${disk:-999} < DISK_MIN_GB )) && reason="$reason disk ${disk}G free"
  echo "$(date -u +%FT%TZ) cpu=${cpu}C gpu=${gpu}C power=${power} disk=${disk}G pid=${pid:-none} ${reason}" >> "$LOG"
  if [[ -n "$reason" ]]; then bad=$((bad+1)); else bad=0; fi
  if (( bad >= NEED )); then
    [[ -n "$pid" ]] && kill -STOP "$pid"
    echo "$(date -u +%FT%TZ) PAUSED forecast pid $pid:$reason (resume with: kill -CONT $pid)" | tee -a "$LOG"
    exit 1
  fi
  sleep 60
done
