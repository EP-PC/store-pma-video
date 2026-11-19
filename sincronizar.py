#!/usr/bin/env python3
"""Monta o vídeo sincronizado FRASE A FRASE com a narração.

    .venv-asr/Scripts/python transcrever.py saida/narracao16k.wav   (gera saida/palavras.json)
    python sincronizar.py audio/narracao.m4a

- As cenas mudam no silêncio entre as frases (achado pelas palavras transcritas, não pelo volume).
- Dentro de cada gravação real, cada resultado (401, 403, conversão, 422, réplicas do HPA...)
  aparece no instante em que a palavra correspondente é falada: o clipe é dividido em trechos,
  cada um com a velocidade que faz isso acontecer.
- Nas animações, cada elemento entra quando a frase que fala dele começa (MARCAS do Manim).
- O áudio não é editado por dentro: só as pausas acima de 1 s viram 0,7 s, cortando no silêncio.
"""
import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

FPS = 30
OUT = Path("saida")
PARTES = OUT / "partes"
REAL = Path("gravacoes")
ANIM_DIR = Path("anim")
ANIM_OUT = ANIM_DIR / "media/videos/cenas/1080p30"
FONTE = "C\\:/Windows/Fonts/segoeui.ttf"
FUNDO = "0x131415"


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", **kw)


def dur(f):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                      "-of", "csv=p=0", str(f)]).stdout)


# ---------------------------------------------------------------- palavras

def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if unicodedata.category(c) != "Mn"))


P = json.load(open(OUT / "palavras.json", encoding="utf-8"))
NW = [norm(w["w"]) for w in P]


def idx(*seq, depois=0.0):
    """Índice da primeira ocorrência da sequência de palavras (prefixos) depois do tempo dado."""
    alvo = [norm(s) for s in seq]
    for i in range(len(P) - len(alvo) + 1):
        if P[i]["a"] < depois:
            continue
        if all(NW[i + k].startswith(a) for k, a in enumerate(alvo)):
            return i
    sys.exit(f"não achei {' '.join(seq)!r} depois de {depois:.1f}s na transcrição")


def w(*seq, depois=0.0):
    """Instante (s, áudio original) em que a sequência começa a ser falada."""
    return P[idx(*seq, depois=depois)]["a"]


def corte(*seq, depois=0.0):
    """Meio do silêncio logo antes da sequência: onde trocar de cena."""
    i = idx(*seq, depois=depois)
    return (P[i - 1]["b"] + P[i]["a"]) / 2 if i else max(0.0, P[0]["a"] - 0.3)


# ---------------------------------------------------------------- áudio: pausas longas viram 0,7 s

def pico(a, b, wav=OUT / "narracao16k.wav"):
    """Pico (dB) do trecho: para confirmar que é silêncio de verdade antes de cortar."""
    err = subprocess.run(["ffmpeg", "-hide_banner", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", str(wav),
                          "-af", "astats=metadata=0", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    v = re.findall(r"Peak level dB: (-?[\d.]+|-inf)", err)
    return float(v[-1]) if v and v[-1] != "-inf" else -99.0


INICIO = max(0.0, P[0]["a"] - 0.4)
FIM = P[-1]["b"] + 0.9
MANTER = []
a = INICIO
for p, q in zip(P, P[1:]):
    # só encurta pausa longa que é silêncio mesmo (o fim da palavra às vezes passa do que o Whisper marca)
    if q["a"] - p["b"] > 1.0 and pico(p["b"] + 0.35, q["a"] - 0.35) < -22:
        MANTER.append((a, p["b"] + 0.35))
        a = q["a"] - 0.35
MANTER.append((a, FIM))


def novo(t):
    """Tempo no áudio original -> tempo no vídeo final."""
    acc = 0.0
    for x, y in MANTER:
        if t <= y:
            return acc + max(0.0, t - x)
        acc += y - x
    return acc


def quadro(t):
    return round(novo(t) * FPS)


# ---------------------------------------------------------------- roteiro de cenas (tempos no áudio original)

def cenas():
    b2 = corte("a", "entrada")
    b3 = corte("aqui")
    b4 = corte("no", "kubernetes")
    b4h = corte("no", "test", depois=60)
    b5 = corte("foram")
    b6 = corte("esse", depois=85)
    b7 = corte("no", "exchange", depois=90)
    b7s = corte("e", "a", "varred", depois=99)
    b8 = corte("na", "aws", depois=100)
    b9 = corte("a", "documenta")
    b9f = corte("a", "loja", "funciona")
    fim = FIM

    yield ("anim", "Abertura", INICIO, b2,
           [w("esse") - 0.1, w("eu", "sou"), w("e", "uma", "l")])
    yield ("anim", "Arquitetura", b2, b3,
           [w("a", "entrada") - 0.6, w("ele", depois=16), w("atras"), w("exchange", depois=23) - 0.3,
            w("na", "aws"), w("jenkins") - 0.3])

    sem, barra, se_tentar = w("sem", "login"), w("barra"), w("se", "tentar")
    q403, ele_faz, reais = w("403"), w("ele", "faz"), w("reais")
    hora, mas, q422 = w("hora"), w("mas", depois=50), w("422")
    yield ("real", "app.mp4", "gravação real · loja completa no docker compose", [
        (b3, barra - 0.15, 8.4, 11.45),          # 401 aparece no "barra"
        (barra - 0.15, se_tentar, 11.45, 24.4),  # cadastro e login
        (se_tentar, q403, 26.4, 30.8),           # 403 no "403"
        (q403, ele_faz, 30.8, 41.5),             # o admin cadastra os produtos
        (ele_faz, reais, 41.5, 47.6),            # o pedido (em dólar)
        (reais, hora, 50.3, 55.5),               # convertido em reais no "converte na hora"
        (hora, mas, 55.5, 56.6),
        (mas, q422, 64.4, 68.6),                 # 422 no "422"
        (q422, b4, 68.6, 71.4),
    ])

    pods, responde = w("pods"), w("responde")
    yield ("real", "k8s.mp4", "gravação real · os k8s.yaml do EKS num cluster kind", [
        (b4, pods, 17.1, 20.8),                  # as probes / kubectl get pods
        (pods, responde + 0.3, 52.0, 62.7),      # pods ficando prontos (todos 1/1 aos ~62,5 s)
        (responde + 0.3, b4h, 62.7, 64.3),
    ])
    cpu, alvo, quatro = w("cpu"), w("alvo"), w("quatro")
    yield ("real", "hpa.mp4", "gravação real · HPA do gateway sob carga", [
        (b4h, cpu, 5.5, 10.0),                   # liga a carga
        (cpu, alvo + 0.1, 36.0, 42.5),           # CPU 186% do alvo no "passa do alvo"
        (alvo + 0.1, quatro, 42.5, 56.6),        # 4 réplicas no "quatro"
        (quatro, b5, 56.6, 63.0),
    ])

    yield ("anim", "Gargalos", b5, b6,
           [w("foram"), w("no", "gateway"), w("probe") - 0.5, w("no", "order"), b6 - 1.6])

    yield ("real", "grafana.mp4", "gravação real · Grafana do order", [(b6, b7, 58.0, 81.0)])

    q800, q4 = w("800"), w("4", depois=95)
    yield ("real", "exchange-cache.mp4", "gravação real · cache do exchange", [
        (b7, q800, 2.6, 8.4),                    # sem cache: 820 ms no "800"
        (q800, q4, 10.9, 16.4),                  # com cache: 4 ms no "4"
        (q4, b7s, 16.4, 19.2),
    ])
    pegou, corrigidas = w("pegou"), w("corrigidas")
    yield ("real", "exchange-security.mp4", "gravação real · Trivy antes e depois", [
        (b7s, pegou + 0.8, 21.8, 29.3),          # imagem barrada (exit 1) no "duas falhas graves"
        (pegou + 0.8, corrigidas + 0.3, 29.3, 38.9),  # corrigida (exit 0) no "corrigidas"
        (corrigidas + 0.3, b8, 38.9, 41.5),
    ])

    yield ("anim", "Nuvem", b8, b9, [w("34") - 0.4, w("por", "isso", depois=109), w("o", "ponto")])
    yield ("real", "docs.mp4", "documentação MkDocs", [(b9, b9f, 0.0, 12.0)])
    yield ("anim", "Fecho", b9f, fim, [w("loja", "funciona") - 0.05, w("proximos") - 0.2])


# ---------------------------------------------------------------- render

def selo_txt(selo, vel):
    return selo + (f"  ·  {vel:.1f}x" if vel > 1.15 else "")


def peca_real(fonte, n0, n1, c0, c1, selo, entra, sai, dst):
    f0, f1 = quadro(n0), quadro(n1)
    frames = f1 - f0
    if frames <= 0:
        return None
    seg = frames / FPS
    vel = (c1 - c0) / seg
    vf = [f"trim={c0}:{c1}", "setpts=PTS-STARTPTS", f"setpts=PTS/{vel:.5f}", f"fps={FPS}",
          "scale=1920:1080:force_original_aspect_ratio=decrease",
          f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color={FUNDO}", "format=yuv420p",
          "tpad=stop_mode=clone:stop_duration=2",
          f"drawtext=fontfile='{FONTE}':text='{selo_txt(selo, vel)}':fontsize=26:fontcolor=0xEAEAE6@0.85:"
          f"box=1:boxcolor={FUNDO}@0.75:boxborderw=12:x=w-tw-40:y=h-th-36"]
    if entra:
        vf.append(f"fade=in:st=0:d=0.2:color={FUNDO}")
    if sai:
        vf.append(f"fade=out:st={max(0, seg - 0.2):.3f}:d=0.2:color={FUNDO}")
    run(["ffmpeg", "-y", "-i", str(fonte), "-an", "-vf", ",".join(vf), "-frames:v", str(frames),
         "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "18", str(dst)])
    return vel


def peca_anim(cena, n0, n1, marcas, dst):
    f0, f1 = quadro(n0), quadro(n1)
    frames = f1 - f0
    alvo = frames / FPS
    rel = [round(novo(m) - novo(n0), 3) for m in marcas]
    env = dict(os.environ, SEM_VOZ="1", ALVO=f"{alvo:.3f}", MARCAS=json.dumps(rel), PYTHONIOENCODING="utf-8")
    run([sys.executable, "-m", "manim", "-qh", "--frame_rate", str(FPS), "--disable_caching",
         "-v", "ERROR", "cenas.py", cena], cwd=ANIM_DIR, env=env)
    src = ANIM_OUT / f"{cena}.mp4"
    run(["ffmpeg", "-y", "-i", str(src), "-an", "-vf", f"fps={FPS},format=yuv420p,tpad=stop_mode=clone:stop_duration=2",
         "-frames:v", str(frames), "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "18", str(dst)])
    return rel, dur(src)


def audio(original):
    partes = []
    for i, (x, y) in enumerate(MANTER):
        p = PARTES / f"a{i:02d}.wav"
        run(["ffmpeg", "-y", "-i", str(original), "-ss", f"{x:.3f}", "-to", f"{y:.3f}",
             "-ar", "48000", "-ac", "1", str(p)])
        partes.append(p)
    lista = PARTES / "audio.txt"
    lista.write_text("".join(f"file '{p.name}'\n" for p in partes), encoding="utf-8")
    voz = OUT / "voz.wav"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lista),
         "-af", "highpass=f=80,afftdn=nf=-25,loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", str(voz)])
    return voz


def main():
    original = Path(sys.argv[1])
    PARTES.mkdir(parents=True, exist_ok=True)
    pecas, log, k = [], [], 0
    for cena in cenas():
        if cena[0] == "anim":
            _, nome, n0, n1, marcas = cena
            dst = PARTES / f"v{k:02d}.mp4"; k += 1
            rel, base = peca_anim(nome, n0, n1, marcas, dst)
            pecas.append(dst)
            log.append(f"{novo(n0):6.2f}s  {nome:<12} {novo(n1) - novo(n0):5.1f}s  marcas {rel}")
        else:
            _, fonte, selo, trechos = cena
            for j, (n0, n1, c0, c1) in enumerate(trechos):
                dst = PARTES / f"v{k:02d}.mp4"; k += 1
                vel = peca_real(REAL / fonte, n0, n1, c0, c1, selo, False, False, dst)
                if vel is None:
                    k -= 1
                    continue
                pecas.append(dst)
                aviso = "  << rápido" if vel > 6 else ("  << lento" if vel < 0.6 else "")
                log.append(f"{novo(n0):6.2f}s  {fonte:<22} clipe {c0:5.1f}-{c1:5.1f}s  em {novo(n1) - novo(n0):4.1f}s ({vel:.1f}x){aviso}")
    lista = PARTES / "video.txt"
    lista.write_text("".join(f"file '{p.name}'\n" for p in pecas), encoding="utf-8")
    mudo = OUT / "mudo.mp4"
    junto = OUT / "junto.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(junto)])
    # só o fim do vídeo escurece (0,6 s); entre as cenas o corte é seco
    d = dur(junto)
    run(["ffmpeg", "-y", "-i", str(junto), "-vf", f"fade=out:st={d - 0.6:.3f}:d=0.6:color={FUNDO}",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18", str(mudo)])
    voz = audio(original)
    final = OUT / "store-pma-final.mp4"
    run(["ffmpeg", "-y", "-i", str(mudo), "-i", str(voz), "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(final)])
    total = dur(final)
    log.append(f"total {total:.1f}s ({int(total // 60)} min {total % 60:.0f} s) · vídeo {dur(mudo):.2f}s · voz {dur(voz):.2f}s")
    (OUT / "sincronia.txt").write_text("\n".join(log) + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(log))


if __name__ == "__main__":
    main()
