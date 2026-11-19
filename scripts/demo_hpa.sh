#!/usr/bin/env bash
# Cena: o HPA escalando o gateway sob carga, em 3 painéis do tmux, gravada de verdade.
#   em cima: os comandos (geradores de carga)
#   embaixo à esquerda: kubectl get hpa gateway -w
#   embaixo à direita: pods do gateway e CPU de cada um (kubectl top)
set -euo pipefail
cd "$(dirname "$0")/.."
COLS=150 ROWS=36

tmux kill-session -t hpa 2>/dev/null || true
tmux new-session -d -s hpa -x $COLS -y $ROWS
tmux set -g status off
tmux set -g pane-border-style fg=colour238
tmux set -g pane-active-border-style fg=colour238
tmux split-window -v -t hpa -l 26
tmux split-window -h -t hpa:0.1
tmux send-keys -t hpa:0.1 "clear; kubectl get hpa gateway -w" Enter
tmux send-keys -t hpa:0.2 "clear; bash scripts/watch_gateway.sh" Enter

python3 scripts/rec.py casts/hpa.cast $COLS $ROWS tmux attach -t hpa &
REC=$!
sleep 2
tmux send-keys -t hpa:0.0 "clear; bash scripts/demo_hpa_driver.sh" Enter
wait $REC
