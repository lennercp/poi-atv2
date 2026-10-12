#!/bin/bash
# Uso: scripts/run-load.sh <cenario>
cd "$(dirname "$0")/.."
source config/load.env

cenario=$1
if [ -z "$cenario" ]; then
  echo "uso: $0 <cenario>"
  exit 1
fi

mkdir -p results
csv=results/$cenario.csv
if [ ! -f $csv ]; then
  echo "cenario,limit,vus,rep,inicio,fim,requisicoes,rps,media_ms,mediana_ms,p95_ms,max_ms,erros,timeouts,calculo_media_ms,calculo_p95_ms" > $csv
fi

for limit in $LIMITS; do
  # aquecimento da JVM, resultado descartado
  k6 run -q -e URL=$URL -e LIMIT=$limit -e VUS=1 -e DURATION=${AQUECIMENTO}s load/primes.js > /dev/null

  for vus in $VUS; do
    for rep in $(seq $REPETICOES); do
      echo "limit=$limit vus=$vus rep=$rep"
      inicio=$(date +%s)
      resumo=$(k6 run -q -e URL=$URL -e LIMIT=$limit -e VUS=$vus -e DURATION=${DURACAO}s -e TIMEOUT=$TIMEOUT load/primes.js)
      fim=$(date +%s)
      echo "$cenario,$limit,$vus,$rep,$inicio,$fim,$resumo" >> $csv
      sleep $PAUSA
    done
  done
done
