#!/bin/bash
# Rodar dentro da VM durante os testes (Ctrl+C para parar).
# Exemplo: scripts/monitor.sh > monitor_A.csv
pid=$(pgrep -f 'java.*cpu-bound\.jar' | head -1)

echo "# nproc=$(nproc) mem_total_mb=$(free -m | awk '/^Mem:/ {print $2}')"
echo "epoch,cpu_pct,mem_usada_mb,java_rss_mb"
while true; do
  cpu=$(vmstat 1 2 | tail -1 | awk '{print 100 - $15}')
  mem=$(free -m | awk '/^Mem:/ {print $3}')
  rss=$(ps -o rss= -p $pid | awk '{print int($1 / 1024)}')
  echo "$(date +%s),$cpu,$mem,$rss"
done
