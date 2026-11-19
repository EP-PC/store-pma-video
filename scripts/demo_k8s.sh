#!/usr/bin/env bash
# Cena: os MESMOS manifestos do EKS aplicados num Kubernetes (kind) e os pods subindo.
source "$(dirname "$0")/lib.sh"
cd "$(dirname "$0")/.."

title "store-pma no Kubernetes · os mesmos k8s.yaml do EKS"

note "cluster kind: 1 control plane + 2 nós de trabalho (no EKS: 2 x t3.medium)"
run "kubectl get nodes" 2.5

note "banco, Secrets e os 6 serviços"
run "kubectl apply -f k8s/postgres/" 1
run "kubectl apply -f k8s/account.yaml -f k8s/auth.yaml -f k8s/product.yaml -f k8s/order.yaml -f k8s/exchange.yaml -f k8s/gateway.yaml" 2

note "as probes chamam /<serviço>/health-check: o pod só recebe tráfego quando está pronto"
type_cmd "kubectl get pods   # atualiza a cada 3 s"
for i in $(seq 1 160); do
  printf '\e[H\e[2J'
  printf '\e[38;5;110m$\e[0m kubectl get pods \e[38;5;245m(atualiza a cada 3 s · %ds)\e[0m\n\n' $((i * 3))
  kubectl get pods
  total=$(kubectl get pods --no-headers | wc -l)
  prontos=$(kubectl get pods --no-headers | awk '{split($2, a, "/"); if (a[1] == a[2] && $3 == "Running") n++} END {print n + 0}')
  [ "$total" -gt 0 ] && [ "$prontos" -eq "$total" ] && break
  sleep 3
done
sleep 3

note "só o gateway é exposto (LoadBalancer); o resto é ClusterIP"
run "kubectl get svc" 3

note "pela porta do gateway"
quiet "kubectl port-forward svc/gateway 8080:8080 >/tmp/pf.log 2>&1 &"
sleep 3
run "http --print=hb :8080/exchange/health-check" 2
run "http --pretty=all --print=h :8080/exchange/USD/BRL | head -1" 3
