#!/usr/bin/env python3
"""Encaixa o vídeo na narração gravada.

    python encaixar.py audio/narracao.m4a        (uma tomada, ~2 s de silêncio entre os blocos)
    python encaixar.py audio/                    (um arquivo por bloco, em ordem alfabética)

1. Acha os 9 blocos (pelas pausas, ou um arquivo por bloco) e mede cada um.
2. Ajusta cada cena para a duração do bloco: as gravações reais são cortadas e aceleradas,
   as animações são renderizadas de novo no Manim com o tempo exato.
3. Junta tudo com a voz tratada (filtro de ruído leve + volume normalizado).

Saída: saida/store-pma-final.mp4 e saida/marcas.txt
"""
import os
import re
import subprocess
import sys
from pathlib import Path

ANIM_DIR = Path("anim")
ANIM_OUT = ANIM_DIR / "media/videos/cenas/1080p30"
REAL = Path("gravacoes")
OUT = Path("saida")
FONTE = "C\\:/Windows/Fonts/segoeui.ttf"
FUNDO = "0x131415"

# Cada bloco do roteiro e as cenas dele: (tipo, fonte, fração do bloco, ini, fim, selo).
# tipo "anim" = cena do Manim (renderizada com a duração certa); "real" = gravação cortada.
BLOCOS = [
    [("anim", "Abertura", 1.0, None, None, None)],
    [("anim", "Arquitetura", 1.0, None, None, None)],
    [("real", "app.mp4", 1.0, 8.0, 71.0, "gravação real · loja completa no docker compose")],
    [("real", "k8s.mp4", 0.35, 56.0, 76.0, "gravação real · os k8s.yaml do EKS num cluster kind"),
     ("real", "hpa.mp4", 0.65, 40.0, 80.0, "gravação real · HPA do gateway sob carga")],
    [("anim", "Gargalos", 1.0, None, None, None)],
    [("real", "grafana.mp4", 1.0, 58.0, 81.0, "gravação real · Grafana do order")],
    [("real", "exchange-cache.mp4", 0.5, 0.0, 19.5, "gravação real · cache do exchange"),
     ("real", "exchange-security.mp4", 0.5, 21.0, 40.5, "gravação real · Trivy antes e depois")],
    [("anim", "Nuvem", 1.0, None, None, None)],
    [("real", "docs.mp4", 0.4, 0.0, 14.0, "documentação MkDocs"),
     ("anim", "Fecho", 0.6, None, None, None)],
]


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)


def dur(f):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                      "-of", "csv=p=0", str(f)]).stdout)


# ---------------------------------------------------------------- áudio

def blocos_de_uma_tomada(audio):
    """Acha as 8 maiores pausas (>= 1 s), corta a fala de cada bloco e junta com um respiro curto."""
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(audio), "-af",
                          "silencedetect=noise=-35dB:d=1.0", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    ini = [max(0.0, float(x)) for x in re.findall(r"silence_start: (-?[\d.]+)", err)]
    fim = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", err)]
    total = dur(audio)
    pausas = [(b - a, a, b) for a, b in zip(ini, fim) if a > 0.5 and b < total - 0.5]
    if len(pausas) < 8:
        sys.exit(f"achei só {len(pausas)} pausas de 1 s ou mais; preciso de 8 (uma entre cada bloco)")
    if len(pausas) > 8:
        print(f"aviso: {len(pausas)} pausas; uso as 8 mais longas")
    escolhidas = sorted(sorted(pausas, reverse=True)[:8], key=lambda x: x[1])
    # silêncio do começo e do fim do arquivo
    comeco = fim[0] if ini and ini[0] <= 0.05 else 0.0
    final = ini[-1] if ini and len(fim) < len(ini) else total
    falas, pos = [], comeco
    for _, a, b in escolhidas:
        falas.append((max(0.0, pos - 0.1), a + 0.25))
        pos = b
    falas.append((max(0.0, pos - 0.1), min(total, final + 0.25)))
    OUT.mkdir(exist_ok=True)
    partes = []
    for i, (a, b) in enumerate(falas):
        p = OUT / f"voz{i}.wav"
        run(["ffmpeg", "-y", "-i", str(audio), "-ss", f"{a:.3f}", "-to", f"{b:.3f}",
             "-af", "apad=pad_dur=0.35", "-ar", "48000", "-ac", "1", str(p)])
        partes.append(p)
    lista = OUT / "audios.txt"
    lista.write_text("".join(f"file '{p.name}'\n" for p in partes), encoding="utf-8")
    junto = OUT / "voz.wav"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(junto)])
    return [dur(p) for p in partes], junto


def blocos_de_arquivos(pasta):
    arqs = sorted(p for p in pasta.iterdir() if p.suffix.lower() in (".wav", ".mp3", ".m4a", ".ogg", ".flac", ".aac", ".webm"))
    if len(arqs) != 9:
        sys.exit(f"achei {len(arqs)} arquivos de áudio em {pasta}; preciso de 9 (um por bloco)")
    OUT.mkdir(exist_ok=True)
    lista = OUT / "audios.txt"
    # cada bloco ganha 0,5 s de respiro no fim
    partes = []
    for i, a in enumerate(arqs):
        p = OUT / f"voz{i}.wav"
        run(["ffmpeg", "-y", "-i", str(a), "-af", "apad=pad_dur=0.35", "-ar", "48000", "-ac", "1", str(p)])
        partes.append(p)
    lista.write_text("".join(f"file '{p.name}'\n" for p in partes), encoding="utf-8")
    junto = OUT / "voz.wav"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(junto)])
    return [dur(p) for p in partes], junto


# ---------------------------------------------------------------- vídeo

def anim(cena, alvo):
    env = dict(os.environ, SEM_VOZ="1", ALVO=f"{alvo:.3f}", PYTHONIOENCODING="utf-8")
    run([sys.executable, "-m", "manim", "-qh", "--frame_rate", "30", "--disable_caching",
         "-v", "ERROR", "cenas.py", cena], cwd=ANIM_DIR, env=env)
    return ANIM_OUT / f"{cena}.mp4"


def normaliza(fonte, dst, alvo, ini=None, fim=None, selo=None):
    total = dur(fonte)
    ini = ini or 0.0
    fim = min(fim if fim is not None else total, total)
    vel = (fim - ini) / alvo
    vf = [f"trim={ini}:{fim}", "setpts=PTS-STARTPTS", f"setpts=PTS/{vel:.5f}",
          "scale=1920:1080:force_original_aspect_ratio=decrease",
          f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color={FUNDO}", "fps=30", "format=yuv420p",
          f"tpad=stop_mode=clone:stop_duration=1"]
    if selo:
        txt = selo + (f"  ·  {vel:.1f}x" if vel > 1.15 else "")
        vf.append(f"drawtext=fontfile='{FONTE}':text='{txt}':fontsize=26:fontcolor=0xEAEAE6@0.85:"
                  f"box=1:boxcolor={FUNDO}@0.75:boxborderw=12:x=w-tw-40:y=h-th-36")
    vf += [f"trim=duration={alvo:.3f}",
           f"fade=in:st=0:d=0.25:color={FUNDO}", f"fade=out:st={alvo - 0.25:.3f}:d=0.25:color={FUNDO}"]
    run(["ffmpeg", "-y", "-i", str(fonte), "-an", "-vf", ",".join(vf),
         "-c:v", "libx264", "-preset", "slow", "-crf", "18", str(dst)])
    return vel


def main():
    alvo = Path(sys.argv[1])
    duracoes, voz = blocos_de_arquivos(alvo) if alvo.is_dir() else blocos_de_uma_tomada(alvo)
    OUT.mkdir(exist_ok=True)
    partes, marcas, t, n = [], [], 0.0, 0
    for b, (bloco, d) in enumerate(zip(BLOCOS, duracoes), start=1):
        for tipo, fonte, frac, ini, fim, selo in bloco:
            alvo_s = d * frac
            dst = OUT / f"p{n:02d}.mp4"
            if tipo == "anim":
                f = anim(fonte, alvo_s)
                vel = normaliza(f, dst, alvo_s)
            else:
                vel = normaliza(REAL / fonte, dst, alvo_s, ini, fim, selo)
            aviso = "  << rápido demais para ler" if vel > 6 else ("  << câmera lenta" if vel < 0.7 else "")
            marcas.append(f"bloco {b}  {int(t // 60)}:{t % 60:05.2f}  {alvo_s:5.1f}s  {fonte} ({vel:.2f}x){aviso}")
            partes.append(dst)
            t += alvo_s
            n += 1
    lista = OUT / "lista.txt"
    lista.write_text("".join(f"file '{p.name}'\n" for p in partes), encoding="utf-8")
    mudo = OUT / "mudo.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(mudo)])
    final = OUT / "store-pma-final.mp4"
    run(["ffmpeg", "-y", "-i", str(mudo), "-i", str(voz), "-map", "0:v", "-map", "1:a",
         "-af", "highpass=f=80,afftdn=nf=-25,loudnorm=I=-16:TP=-1.5:LRA=11",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(final)])
    marcas.append(f"total {t:.1f}s  ({int(t // 60)} min {t % 60:.0f} s)")
    (OUT / "marcas.txt").write_text("\n".join(marcas) + "\n", encoding="utf-8")
    print("\n".join(marcas))
    print(f"pronto: {final}")


if __name__ == "__main__":
    main()
