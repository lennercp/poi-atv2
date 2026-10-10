#!/usr/bin/env bash
# Runs every LIMIT x VUS x repetition combination from config/load.env against the app
# and appends one line per run to results/<scenario>/runs.csv.
# Usage: scripts/run-load.sh <scenario>     (scenario name from config/scenarios.env, e.g. A)
set -euo pipefail
export LC_ALL=C   # "." as decimal separator in awk/printf
cd "$(dirname "$0")/.."
source config/scenarios.env
source "${LOAD_ENV:-config/load.env}"   # LOAD_ENV=other.env selects another load profile

scenario=${1:?usage: $0 <scenario>}
vcpus_var=${scenario}_VCPUS
ram_var=${scenario}_RAM_MB
[ -n "${!vcpus_var:-}" ] || { echo "unknown scenario '$scenario' in config/scenarios.env" >&2; exit 1; }
curl -fsS "$TARGET_URL/health" > /dev/null || { echo "app not reachable at $TARGET_URL" >&2; exit 1; }

out=results/$scenario
mkdir -p "$out"
csv=$out/runs.csv
{
  echo "scenario=$scenario vcpus=${!vcpus_var} ram_mb=${!ram_var} started=$(date -Iseconds)"
  [ -n "$VM_SSH" ] && ssh $VM_SSH 'echo "vm nproc=$(nproc) mem_total_mb=$(free -m | awk "/^Mem:/ {print \$2}")"'
  cat "${LOAD_ENV:-config/load.env}"
} > "$out/meta.txt"
[ -f "$csv" ] || echo "scenario,limit,vus,rep,requests,rps,avg_ms,med_ms,p95_ms,max_ms,errors,timeouts,compute_avg_ms,compute_med_ms,compute_p95_ms,cpu_avg_pct,mem_used_avg_mb,java_rss_max_mb" > "$csv"

for limit in $LIMITS; do
  echo "warm-up limit=$limit (${WARMUP_SECONDS}s)"
  k6 run -q -e TARGET_URL="$TARGET_URL" -e LIMIT="$limit" -e VUS=1 -e DURATION="${WARMUP_SECONDS}s" \
    load/primes.js > /dev/null

  for vus in $VUS_LEVELS; do
    for rep in $(seq 1 "$REPETITIONS"); do
      run=l${limit}_u${vus}_r${rep}
      echo "run $run"
      if [ -n "$VM_SSH" ]; then
        ssh $VM_SSH "$VM_APP_DIR/scripts/monitor.sh $DURATION_SECONDS" > "$out/$run.monitor.csv" &
      fi

      k6 run -q -e TARGET_URL="$TARGET_URL" -e LIMIT="$limit" -e VUS="$vus" \
        -e DURATION="${DURATION_SECONDS}s" -e REQUEST_TIMEOUT="$REQUEST_TIMEOUT" \
        -e SCENARIO="$scenario" -e REP="$rep" -e OUT="$out/$run.k6.csv" load/primes.js > /dev/null
      wait

      resources=",,"
      if [ -s "$out/$run.monitor.csv" ]; then
        resources=$(awk -F, '/^[0-9]/ {n++; cpu += $2; mem += $3; if ($4 > rss) rss = $4}
          END {if (n) printf "%.1f,%.0f,%d", cpu / n, mem / n, rss; else printf ",,"}' "$out/$run.monitor.csv")
      fi
      echo "$(cat "$out/$run.k6.csv"),$resources" | tee -a "$csv"
      sleep "$COOLDOWN_SECONDS"
    done
  done
done
echo "done: $csv"
