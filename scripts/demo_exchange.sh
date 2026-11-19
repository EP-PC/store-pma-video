#!/usr/bin/env bash
# Cenas do Exchange: testes, cache (bottleneck 1) e varredura (bottleneck 2).
# Uso: demo_exchange.sh tests|cache|security
source "$(dirname "$0")/lib.sh"
cd "$(dirname "$0")/../exchange"
export PATH="/tmp/venv/bin:$PATH"

case "$1" in

tests)
  title "Exchange · testes automatizados"
  note "PTAX simulado (httpx.MockTransport) e relógio falso: sem rede, sem esperar o cache expirar"
  run "pytest -v --no-header -p no:warnings tests/ 2>&1 | sed -E 's#tests/test_exchange.py::##'" 4
  ;;

cache)
  title "Exchange · bottleneck 1: cache das cotações"
  note "sem cache: toda requisição vai ao Banco Central"
  CACHE_SECONDS=0 uvicorn main:app --port 8080 --log-level warning >/tmp/sem-cache.log 2>&1 &
  SRV=$!
  sleep 3
  run "python bench/bench.py --n 100 --c 5" 3
  kill $SRV; sleep 1
  note "com cache (5 min) e lock por moeda, serviço recém-iniciado"
  uvicorn main:app --port 8080 --log-level warning >/tmp/com-cache.log 2>&1 &
  SRV=$!
  sleep 3
  run "python bench/bench.py --n 100 --c 5" 4
  kill $SRV
  ;;

security)
  title "Exchange · bottleneck 2: varredura de vulnerabilidades"
  note "dependências antigas (fastapi 0.109): o pipeline tem que parar"
  run "printf 'fastapi==0.109.0\nuvicorn==0.27.0\nhttpx==0.26.0\n' > /tmp/antigas.txt"  0.5
  run "pip-audit -r /tmp/antigas.txt" 4
  note "dependências atuais, fixadas no requirements.txt"
  run "pip-audit -r requirements.txt" 3
  note "Trivy na imagem final: barra HIGH/CRITICAL com correção disponível"
  run "trivy image --quiet --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 exchange:scan; echo \"exit code: \$?\"" 4
  ;;

esac
