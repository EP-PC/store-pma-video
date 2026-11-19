#!/usr/bin/env bash
# Ferramentas para transformar as gravações em vídeo: fonte, ffmpeg, tmux e agg.
set -euo pipefail
sudo apt-get update -qq
sudo apt-get install -y -qq fonts-jetbrains-mono ffmpeg tmux >/dev/null
sudo curl -fsSL -o /usr/local/bin/agg \
  https://github.com/asciinema/agg/releases/download/v1.9.0/agg-x86_64-unknown-linux-gnu
sudo chmod +x /usr/local/bin/agg
agg --version
