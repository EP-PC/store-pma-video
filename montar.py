#!/usr/bin/env python3
"""Monta o vídeo final: animações (Manim) + gravações reais (Actions), sem áudio.

    python montar.py            gera saida/store-pma.mp4 e saida/marcas.txt

Cada trecho real pode ser cortado (ini/fim, em segundos do clipe) e acelerado para caber no
tempo do roteiro; um selo discreto no canto diz que é gravação real e o que está acelerado.
"""
import subprocess
from pathlib import Path

ANIM = Path("anim/media/videos/cenas/1080p30")
REAL = Path("gravacoes")
OUT = Path("saida")
FONTE = "C\\:/Windows/Fonts/segoeui.ttf"

# (arquivo, ini, fim, duração no vídeo final ou None = tempo real, selo)
TRECHOS = [
    (ANIM / "Abertura.mp4", None, None, None, None),
    (ANIM / "Arquitetura.mp4", None, None, None, None),
    (REAL / "app.mp4", 0, None, 24, "gravação real · loja completa (docker compose)"),
    (REAL / "k8s.mp4", 0, None, 10, "gravação real · os k8s.yaml do EKS num cluster kind"),
    (REAL / "hpa.mp4", 0, None, 12, "gravação real · HPA do gateway sob carga"),
    (ANIM / "Gargalos.mp4", None, None, None, None),
    (REAL / "grafana.mp4", 0, None, 6, "gravação real · Grafana do order"),
    (REAL / "exchange-cache.mp4", 0, None, 8, "gravação real · cache do exchange"),
    (REAL / "exchange-security.mp4", 0, None, 7, "gravação real · pip-audit e Trivy"),
    (ANIM / "Nuvem.mp4", None, None, None, None),
    (REAL / "docs.mp4", 0, None, 5, "documentação MkDocs"),
    (ANIM / "Fecho.mp4", None, None, None, None),
]


def dur(f):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(f)], capture_output=True, text=True, check=True)
    return float(out.stdout)


def trecho(i, f, ini, fim, alvo, selo):
    total = dur(f)
    ini = ini or 0.0
    fim = fim if fim is not None else total
    janela = fim - ini
    vel = janela / alvo if alvo else 1.0
    final = janela / vel
    vf = [f"trim={ini}:{fim}", "setpts=PTS-STARTPTS", f"setpts=PTS/{vel:.4f}",
          "scale=1920:1080:force_original_aspect_ratio=decrease",
          "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x131415", "fps=30", "format=yuv420p"]
    if selo:
        txt = selo + (f"  ·  {vel:.1f}x" if vel > 1.15 else "")
        vf.append(f"drawtext=fontfile='{FONTE}':text='{txt}':fontsize=26:fontcolor=0xEAEAE6@0.85:"
                  "box=1:boxcolor=0x131415@0.75:boxborderw=12:x=w-tw-40:y=h-th-36")
    vf += [f"fade=in:st=0:d=0.25:color=0x131415", f"fade=out:st={final - 0.25:.3f}:d=0.25:color=0x131415"]
    dst = OUT / f"parte{i:02d}.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(f), "-an", "-vf", ",".join(vf),
                    "-c:v", "libx264", "-preset", "slow", "-crf", "18", str(dst)], check=True)
    return dst, dur(dst), vel


def main():
    OUT.mkdir(exist_ok=True)
    partes, marcas, t = [], [], 0.0
    for i, (f, ini, fim, alvo, selo) in enumerate(TRECHOS):
        dst, d, vel = trecho(i, f, ini, fim, alvo, selo)
        partes.append(dst)
        marcas.append(f"{int(t // 60)}:{t % 60:05.2f}  {d:5.1f}s  {f.name}  ({vel:.1f}x)")
        t += d
    lista = OUT / "lista.txt"
    lista.write_text("".join(f"file '{p.name}'\n" for p in partes), encoding="utf-8")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lista),
                    "-c", "copy", "-movflags", "+faststart", str(OUT / "store-pma.mp4")], check=True)
    (OUT / "marcas.txt").write_text("\n".join(marcas) + f"\ntotal {t:.1f}s\n", encoding="utf-8")
    print("\n".join(marcas), f"\ntotal {t:.1f}s")


if __name__ == "__main__":
    main()
