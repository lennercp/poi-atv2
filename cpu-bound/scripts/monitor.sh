#!/usr/bin/env bash
# Run INSIDE the VM. Prints one CSV line per second for <seconds> seconds:
# whole-VM CPU use (%), VM used memory (MB) and resident memory of the Java app (MB).
set -euo pipefail
export LC_ALL=C   # "." as decimal separator in awk/printf
secs=${1:?usage: $0 <seconds>}
pid=$(pgrep -f 'java.*cpu-bound\.jar' | head -1 || true)

echo "# nproc=$(nproc) mem_total_mb=$(free -m | awk '/^Mem:/ {print $2}')"
echo "epoch,cpu_used_pct,mem_used_mb,java_rss_mb"
for ((i = 0; i < secs; i++)); do
  cpu=$(vmstat 1 2 | tail -1 | awk '{print 100 - $15}')   # $15 = idle; takes 1 s
  mem=$(free -m | awk '/^Mem:/ {print $3}')
  rss=$([ -n "$pid" ] && ps -o rss= -p "$pid" | awk '{print int($1 / 1024)}' || echo 0)
  echo "$(date +%s),$cpu,$mem,$rss"
done
