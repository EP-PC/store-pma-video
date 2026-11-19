#!/usr/bin/env bash
# render.sh cena.cast cena.mp4 [tamanho-da-fonte] [pausa-maxima-s]
# asciicast -> gif (agg) -> mp4 1920x1080 no fundo escuro dos outros vídeos.
set -euo pipefail
in=$1 out=$2 fs=${3:-26} idle=${4:-4}
# fundo, texto e as 8 cores ANSI na paleta do base_video.py (TINTA, VERM, VERDE, AMAR, AZUL...)
theme=121614,eaeae6,1c201e,f4706a,5cbe84,e4c44e,6fa8dc,c39ac9,7fc8c8,eaeae6
agg --font-family "JetBrains Mono" --font-size "$fs" --line-height 1.35 --theme "$theme" \
    --idle-time-limit "$idle" --last-frame-duration 3 --fps-cap 30 "$in" "${out%.mp4}.gif"
ffmpeg -loglevel error -y -i "${out%.mp4}.gif" \
  -vf "fps=30,scale=1840:1000:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x121614,format=yuv420p" \
  -c:v libx264 -preset slow -crf 18 -movflags +faststart "$out"
rm -f "${out%.mp4}.gif"
ffprobe -v error -show_entries format=duration -of csv=p=0 "$out" | xargs printf '%s: %.1f s\n' "$out"
