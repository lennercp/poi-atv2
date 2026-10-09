#!/usr/bin/env bash
# Teste ponta a ponta: 2 cenários falsos (servidor limitado a 1 vs 2 núcleos) → run → report → checagens.
set -euo pipefail
cd "$(dirname "$0")/../.."
PY=.venv/bin/python
CONFIG=tests/e2e/e2e.yaml
SERVIDOR=""
trap '[ -n "$SERVIDOR" ] && kill "$SERVIDOR" 2>/dev/null || true' EXIT

rm -rf results-e2e

rodar_cenario() {  # $1 = nome do cenário, $2 = núcleos permitidos (taskset)
  taskset -c "$2" "$PY" tests/e2e/fake_server.py --porta 18080 --workers 2 &
  SERVIDOR=$!
  sleep 1
  "$PY" bench/bench.py run --cenario "$1" --config "$CONFIG"
  kill "$SERVIDOR"; wait "$SERVIDOR" 2>/dev/null || true
  SERVIDOR=""
}

rodar_cenario c1-1nucleo 0
rodar_cenario c2-2nucleos 0,1
"$PY" bench/bench.py report --config "$CONFIG"
"$PY" tests/e2e/verificar.py
