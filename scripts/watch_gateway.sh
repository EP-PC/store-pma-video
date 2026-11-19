#!/usr/bin/env bash
# Painel da direita na cena do HPA: réplicas do gateway e CPU de cada uma, a cada 3 s.
while true; do
  out=$(kubectl get pods -l app=gateway 2>&1; echo; kubectl top pods -l app=gateway 2>/dev/null || echo "(metrics-server coletando...)")
  printf '\e[H\e[2J\e[38;5;110m$\e[0m kubectl get pods -l app=gateway; kubectl top pods -l app=gateway\n\n%s\n' "$out"
  sleep 3
done
