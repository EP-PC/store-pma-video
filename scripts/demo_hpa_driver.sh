#!/usr/bin/env bash
# Painel de cima na cena do HPA: liga a carga, espera o HPA escalar e desliga.
source "$(dirname "$0")/lib.sh"
cd "$(dirname "$0")/.."

note "HPA do gateway: alvo de 50% da CPU pedida (250m), de 1 a 6 réplicas" 4
note "carga: 4 geradores chamando GET /products em loop, de dentro do cluster" 1
run "for i in 1 2 3 4; do kubectl run carga-\$i --image=busybox:1.36 --restart=Never -- sh -c 'while true; do wget -qO- http://gateway:8080/products >/dev/null; done'; done" 2

# espera o HPA chegar a 3 réplicas ou mais (no máximo ~5 min)
for _ in $(seq 1 100); do
  r=$(kubectl get hpa gateway -o jsonpath='{.status.currentReplicas}' 2>/dev/null || echo 1)
  [ "${r:-1}" -ge 3 ] && break
  sleep 3
done
sleep 45   # deixa as réplicas novas ficarem prontas e a CPU se dividir

note "desligando a carga (o HPA volta para 1 réplica depois de ~5 min de estabilização)" 1
run "kubectl delete pod carga-1 carga-2 carga-3 carga-4 --wait=false" 12
tmux kill-session -t hpa
