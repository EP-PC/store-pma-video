#!/usr/bin/env python3
"""Transcreve a narração com o tempo de cada palavra (Whisper local).

    .venv-asr/Scripts/python transcrever.py saida/narracao16k.wav  (WAV 16 kHz mono)

Saída: saida/palavras.json  ([{"w": "palavra", "a": inicio, "b": fim}, ...]) e o texto por linha.
"""
import json
import sys
import wave

import numpy as np
from pathlib import Path

from faster_whisper import WhisperModel

# o av instalado não aceita o argumento que o faster-whisper passa; lê o WAV 16 kHz mono direto
with wave.open(sys.argv[1], "rb") as f:
    audio = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
model = WhisperModel("small", device="cpu", compute_type="int8")
segs, info = model.transcribe(audio, language="pt", word_timestamps=True, vad_filter=False,
                              initial_prompt="store-pma, gateway, auth, account, product, order, exchange, "
                                             "EKS, RDS, Jenkins, Kubernetes, health-check, HPA, readiness probe, "
                                             "Redis, Prometheus, Grafana, Trivy, MkDocs, Banco Central.")
palavras = []
Path("saida").mkdir(exist_ok=True)
for s in segs:
    print(f"[{s.start:6.2f} - {s.end:6.2f}] {s.text.strip()}")
    for w in s.words:
        palavras.append({"w": w.word.strip(), "a": round(w.start, 3), "b": round(w.end, 3)})
Path("saida/palavras.json").write_text(json.dumps(palavras, ensure_ascii=False, indent=0), encoding="utf-8")
print(f"{len(palavras)} palavras")
