# -*- coding: utf-8 -*-
"""Peças comuns dos vídeos: cores, textos, painéis e narração.

Uso numa cena:
    from base_video import *
    class Minha(Aula):
        def roteiro(self): ...

Renderiza com narração (padrão) ou mudo, para conferir o layout:
    python -m manim -qh --frame_rate 30 --disable_caching arquivo.py Classe
    SEM_VOZ=1 python -m manim -ql --disable_caching arquivo.py Classe
"""
import os
import contextlib

from manim import *

MUDO = os.environ.get("SEM_VOZ") == "1"

if MUDO:
    _Base = Scene
else:
    from manim_voiceover import VoiceoverScene
    from voz import EdgeService
    _Base = VoiceoverScene

TINTA, APAGADO = "#EAEAE6", "#8C908C"
VERM, VERDE, AZUL, AMAR = "#F4706A", "#5CBE84", "#6FA8DC", "#E4C44E"
MONO = "Consolas"
LARG, ALT = 12.4, 5.0


def t(txt, s=34, cor=TINTA, mono=False):
    if mono:
        return Text(txt, font_size=s, color=cor, font=MONO)
    return Text(txt, font_size=s, color=cor)


def m(txt, s=28, cor=TINTA):
    """Texto mono. O Manim descarta os espaços do começo da linha, então o
    recuo fica guardado e é aplicado depois, em recua()."""
    obj = t(txt, s, cor, mono=True)
    obj.recuo = len(txt) - len(txt.lstrip(" "))
    obj.tam = s
    return obj


_LARG_CHAR = {}


def recua(grupo):
    for item in grupo:
        n = getattr(item, "recuo", 0)
        if n:
            s = item.tam
            if s not in _LARG_CHAR:
                _LARG_CHAR[s] = Text("M" * 20, font=MONO, font_size=s).width / 20
            item.shift(RIGHT * n * _LARG_CHAR[s])
    return grupo


class _Tempo:
    def __init__(self, duracao):
        self.duration = duracao


class Aula(_Base):
    TITULO = ""
    SUBTITULO = ""

    def construct(self):
        self.camera.background_color = "#131415"
        if not MUDO:
            self.set_speech_service(EdgeService(voice="pt-BR-AntonioNeural", rate="+4%"))
        self.roteiro()

    def roteiro(self):
        raise NotImplementedError

    @contextlib.contextmanager
    def fala(self, texto):
        """Narra o texto. As animações dentro do bloco rodam junto com a voz,
        e no fim o bloco espera a fala terminar (com ou sem voz)."""
        if MUDO:
            t = _Tempo(max(1.8, len(texto) / 14.5))
            inicio = self.renderer.time
            yield t
            resto = t.duration - (self.renderer.time - inicio)
            if resto > 0.05:
                self.wait(resto)
        else:
            with self.voiceover(text=texto) as f:
                yield f

    def limpa(self):
        if self.mobjects:
            self.play(*[FadeOut(x) for x in self.mobjects], run_time=0.5)

    def titulo(self, txt, cor=TINTA, s=38):
        tit = t(txt, s, cor).to_edge(UP, buff=0.7)
        if tit.width > LARG:
            tit.scale_to_fit_width(LARG)
        self.play(FadeIn(tit), run_time=0.5)
        return tit

    def painel(self, *linhas, **kw):
        g = VGroup(*linhas).arrange(DOWN, buff=kw.get("buff", 0.28),
                                    aligned_edge=kw.get("edge", LEFT))
        recua(g)
        larg = kw.get("larg", LARG)
        alt = kw.get("alt", ALT)
        if g.width > larg:
            g.scale_to_fit_width(larg)
        if g.height > alt:
            g.scale_to_fit_height(alt)
        return g.move_to(DOWN * kw.get("desce", 0.3))

    def mostra(self, grupo, texto, por_linha=False):
        with self.fala(texto) as f:
            if por_linha and len(grupo) > 1:
                passo = min(0.6, (f.duration * 0.6) / len(grupo))
                for item in grupo:
                    self.play(FadeIn(item, shift=RIGHT * 0.12), run_time=passo)
                gasto = passo * len(grupo)
            else:
                self.play(FadeIn(grupo, shift=UP * 0.1), run_time=1.0)
                gasto = 1.0
            self.wait(max(0.1, f.duration - gasto))

    def revela(self, itens, falas):
        """Uma fala por item: o item aparece junto com a frase que o explica."""
        assert len(itens) == len(falas), (len(itens), len(falas))
        for item, texto in zip(itens, falas):
            with self.fala(texto) as f:
                rt = min(0.7, max(0.2, f.duration * 0.5))
                self.play(FadeIn(item, shift=RIGHT * 0.12), run_time=rt)
                self.wait(max(0.1, f.duration - rt))

    def tela(self, titulo, linhas, falas, cor=TINTA, **kw):
        """Título + uma linha por fala, e limpa no fim."""
        self.titulo(titulo, cor, 36)
        g = self.painel(*linhas, **kw)
        self.revela(list(g), falas)
        self.limpa()

    def resumo(self, linhas, texto, titulo="o que levar daqui"):
        self.titulo(titulo, AMAR, 34)
        g = self.painel(*[t(x, 30) for x in linhas], buff=0.32)
        self.mostra(g, texto, por_linha=True)
        self.limpa()

    def abertura(self, texto):
        tit = t(self.TITULO, 50)
        sub = t(self.SUBTITULO, 26, APAGADO)
        g = VGroup(tit, sub).arrange(DOWN, buff=0.35)
        if g.width > LARG:
            g.scale_to_fit_width(LARG)
        with self.fala(texto) as f:
            self.play(Write(tit), run_time=1.4)
            self.play(FadeIn(sub), run_time=0.6)
            self.wait(max(0.1, f.duration - 2.0))
        self.limpa()

    def fecho(self, grande, linhas, texto):
        g = self.painel(t(grande, 42, VERDE), *[t(x, 28, APAGADO) for x in linhas],
                        edge=ORIGIN, buff=0.4)
        with self.fala(texto) as f:
            self.play(Write(g[0]), run_time=1.2)
            if len(g) > 1:
                self.play(FadeIn(g[1:], lag_ratio=0.3), run_time=0.8)
            self.wait(max(0.1, f.duration - 2.0))
        self.wait(0.8)

    # -- pedaços que toda aula passo a passo repete ---------------------------
    def pausa_pensa(self, segundos=3.0):
        aviso = t("pausa e pensa", 40, AMAR).to_corner(DR, buff=0.5)
        self.play(FadeIn(aviso), run_time=0.3)
        self.wait(segundos)
        self.play(FadeOut(aviso), run_time=0.3)

    def resposta_a(self, pergunta, blocos, falas):
        """Monta a resposta nota A: blocos = [(D, texto), (E, texto), (C, texto)]."""
        self.titulo("na prova: “" + pergunta + "”", AMAR, 32)
        fundos = {"D": "#1E3350", "E": "#3A3418", "C": "#1D3A2A"}
        g = VGroup(*[balao(k + "  " + txt, TINTA, fundos[k], 32) for k, txt in blocos]
                   ).arrange(DOWN, buff=0.35, aligned_edge=LEFT).move_to(DOWN * 0.2)
        if g.width > LARG:
            g.scale_to_fit_width(LARG)
        for b, f in zip(g, falas):
            with self.fala(f):
                self.play(FadeIn(b, shift=RIGHT * 0.3), run_time=0.7)
        self.limpa()

    def quiz(self, perguntas):
        """perguntas = [(pergunta, resposta na tela, resposta falada)]."""
        self.titulo("quiz relâmpago", AMAR, 38)
        nomes = ["Pergunta um.", "Pergunta dois.", "Pergunta três.", "Pergunta quatro."]
        for i, (q, r, rf) in enumerate(perguntas):
            pq = t(q, 38).move_to(UP * 0.8)
            if pq.width > LARG:
                pq.scale_to_fit_width(LARG)
            pr = t(r, 42, VERDE).move_to(DOWN * 0.8)
            if pr.width > LARG:
                pr.scale_to_fit_width(LARG)
            with self.fala(nomes[i] + " " + q):
                self.play(FadeIn(pq), run_time=0.5)
            self.pausa_pensa(3.0)
            with self.fala("Resposta: " + rf):
                self.play(FadeIn(pr, scale=1.1), run_time=0.5)
            self.play(FadeOut(pq), FadeOut(pr), run_time=0.4)
        self.limpa()

    def caixa(self, rotulo, s=24, cor=TINTA, borda=AZUL):
        txt = t(rotulo, s, cor, mono=True)
        r = RoundedRectangle(width=txt.width + 0.3, height=txt.height + 0.25,
                             corner_radius=0.08, stroke_color=borda, stroke_width=2)
        r.move_to(txt)
        return VGroup(r, txt)


# ---------------------------------------------------------------------------
# Peças visuais das aulas "em passinhos"
# ---------------------------------------------------------------------------

class Fita(VGroup):
    """Fita da Máquina de Turing: uma fileira de quadradinhos com símbolos."""

    def __init__(self, simbolos, lado=0.9, cor=TINTA, **kw):
        super().__init__(**kw)
        self.lado = lado
        self.celulas = VGroup(*[
            Square(lado, stroke_color=APAGADO, stroke_width=3) for _ in simbolos
        ]).arrange(RIGHT, buff=0)
        self.textos = VGroup(*[
            t(s, int(lado * 46), cor, mono=True).move_to(c)
            for s, c in zip(simbolos, self.celulas)
        ])
        self.add(self.celulas, self.textos)

    def centro(self, i):
        return self.celulas[i].get_center()

    def escreve(self, i, simbolo, cor=AMAR):
        novo = t(simbolo, int(self.lado * 46), cor, mono=True).move_to(self.celulas[i])
        return Transform(self.textos[i], novo)  # o que está na tela vira o novo

    def acende(self, i, cor=AMAR):
        return Indicate(self.celulas[i], color=cor, scale_factor=1.15)


class Cabeca(VGroup):
    """Cabeça de leitura: setinha em cima da fita + balão com o estado."""

    def __init__(self, estado="q0", cor=AZUL):
        super().__init__()
        self.seta = Triangle(color=cor, fill_opacity=1).scale(0.3).rotate(PI)
        self.rot = t(estado, 34, cor, mono=True).next_to(self.seta, UP, buff=0.12)
        self.add(self.seta, self.rot)

    def em(self, fita, i):
        return self.animate.move_to(fita.centro(i) + UP * (fita.lado / 2 + 0.45))

    def estado(self, novo, cor=AZUL):
        r = t(novo, 34, cor, mono=True).next_to(self.seta, UP, buff=0.12)
        return Transform(self.rot, r)


def robo(cor=AZUL, escala=1.0):
    """Um robozinho simpático: cabeça, olhos, boca e antena."""
    cabeca = RoundedRectangle(width=1.6, height=1.2, corner_radius=0.25,
                              stroke_color=cor, fill_color=cor, fill_opacity=0.18)
    olhos = VGroup(Dot(radius=0.11, color=TINTA), Dot(radius=0.11, color=TINTA)
                   ).arrange(RIGHT, buff=0.45).move_to(cabeca).shift(UP * 0.12)
    boca = Line(LEFT * 0.25, RIGHT * 0.25, color=TINTA, stroke_width=4
                ).move_to(cabeca).shift(DOWN * 0.25)
    haste = Line(cabeca.get_top(), cabeca.get_top() + UP * 0.35, color=cor)
    bola = Dot(haste.get_end(), radius=0.09, color=cor)
    return VGroup(cabeca, olhos, boca, haste, bola).scale(escala)


def celular(nome, cor=AZUL):
    """Um celular com o nome do contato no topo."""
    corpo = RoundedRectangle(width=4.6, height=5.6, corner_radius=0.3,
                             stroke_color=APAGADO, stroke_width=3)
    topo = t(nome, 32, cor).move_to(corpo.get_top() + DOWN * 0.42)
    linha = Line(corpo.get_left() + RIGHT * 0.2, corpo.get_right() + LEFT * 0.2,
                 color=APAGADO, stroke_width=1.5).next_to(topo, DOWN, buff=0.15)
    return VGroup(corpo, topo, linha)


def balao(texto, cor=TINTA, fundo="#22262B", s=24, borda=None):
    """Balão de conversa."""
    txt = t(texto, s, cor)
    caixa = RoundedRectangle(width=txt.width + 0.4, height=txt.height + 0.3,
                             corner_radius=0.15, stroke_color=borda or fundo,
                             fill_color=fundo, fill_opacity=1)
    txt.move_to(caixa)
    return VGroup(caixa, txt)


def digitando(cor=APAGADO):
    """Os três pontinhos de 'digitando...'."""
    return VGroup(*[Dot(radius=0.11, color=cor) for _ in range(3)]).arrange(RIGHT, buff=0.16)


def pisca_pontinhos(pontos, voltas=2):
    """Anima os três pontinhos subindo um de cada vez."""
    anims = []
    for _ in range(voltas):
        for p in pontos:
            anims.append(p.animate(rate_func=there_and_back, run_time=0.35).shift(UP * 0.12))
    return Succession(*anims)


def selo(texto, cor):
    """Carimbo grande de resultado (ACEITA, REJEITA...)."""
    txt = t(texto, 40, cor)
    caixa = RoundedRectangle(width=txt.width + 0.6, height=txt.height + 0.4,
                             corner_radius=0.12, stroke_color=cor, stroke_width=5)
    caixa.move_to(txt)
    return VGroup(caixa, txt)


# ---------------------------------------------------------------------------
# Checagem de sobreposição (CHECA=1): lista textos que se encostam ou saem da tela
# ---------------------------------------------------------------------------
if os.environ.get("CHECA") == "1":
    _play_original = Scene.play
    _vistos = set()

    def _caixa(m):
        return (m.get_left()[0], m.get_right()[0], m.get_bottom()[1], m.get_top()[1])

    def _textos(scene):
        out = []
        for top in scene.mobjects:
            for m in top.get_family():
                if isinstance(m, Text) and m.width > 0.01 and m.get_fill_opacity() > 0.05:
                    out.append(m)
        return out

    def _play_checado(self, *args, **kwargs):
        _play_original(self, *args, **kwargs)
        ts = _textos(self)
        fw, fh = config.frame_width / 2, config.frame_height / 2
        for i, a in enumerate(ts):
            ax0, ax1, ay0, ay1 = _caixa(a)
            if ax0 < -fw + 0.3 or ax1 > fw - 0.3 or ay0 < -fh + 0.15 or ay1 > fh - 0.15:
                chave = ("fora", a.text)
                if chave not in _vistos:
                    _vistos.add(chave)
                    print(f"[CHECA] t={self.renderer.time:6.1f}s FORA DA TELA: {a.text!r}", flush=True)
            for b in ts[i + 1:]:
                if a.text == b.text and abs(a.get_center() - b.get_center()).max() < 0.01:
                    continue
                bx0, bx1, by0, by1 = _caixa(b)
                ox = min(ax1, bx1) - max(ax0, bx0)
                oy = min(ay1, by1) - max(ay0, by0)
                if ox > 0.03 and oy > 0.03:
                    chave = (a.text, b.text)
                    if chave not in _vistos:
                        _vistos.add(chave)
                        print(f"[CHECA] t={self.renderer.time:6.1f}s ENCOSTA: {a.text!r} x {b.text!r}", flush=True)

    def _formas(scene):
        dentro_de_texto = set()
        for top in scene.mobjects:
            for m in top.get_family():
                if isinstance(m, Text):
                    for f in m.get_family():
                        dentro_de_texto.add(id(f))
        out = []
        for top in scene.mobjects:
            for m in top.get_family():
                if id(m) in dentro_de_texto or isinstance(m, Text) or m.submobjects:
                    continue
                if not isinstance(m, VMobject) or (m.width < 0.05 and m.height < 0.05):
                    continue
                if m.get_stroke_width() <= 0 and m.get_fill_opacity() <= 0.05:
                    continue
                out.append(m)
        return out

    def _play_checado2(self, *args, **kwargs):
        _play_checado(self, *args, **kwargs)
        for a in _textos(self):
            ax0, ax1, ay0, ay1 = _caixa(a)
            for f in _formas(self):
                bx0, bx1, by0, by1 = _caixa(f)
                ox = min(ax1, bx1) - max(ax0, bx0)
                oy = min(ay1, by1) - max(ay0, by0)
                if ox <= 0.03 or oy <= 0.03:
                    continue
                texto_dentro = ax0 >= bx0 - 0.02 and ax1 <= bx1 + 0.02 and ay0 >= by0 - 0.02 and ay1 <= by1 + 0.02
                forma_dentro = bx0 >= ax0 - 0.02 and bx1 <= ax1 + 0.02 and by0 >= ay0 - 0.02 and by1 <= ay1 + 0.02
                if texto_dentro:
                    folga = min(ax0 - bx0, bx1 - ax1, ay0 - by0, by1 - ay1)
                    if folga < 0.06 and type(f).__name__ in ("RoundedRectangle", "Rectangle", "Square"):
                        chave = ("apertado", a.text, round(bx0, 1), round(by0, 1))
                        if chave not in _vistos:
                            _vistos.add(chave)
                            print(f"[CHECA] t={self.renderer.time:6.1f}s APERTADO NA CAIXA: {a.text!r}", flush=True)
                    continue
                if forma_dentro:
                    continue
                chave = ("cruza", a.text, type(f).__name__, round(bx0, 1), round(by0, 1))
                if chave not in _vistos:
                    _vistos.add(chave)
                    print(f"[CHECA] t={self.renderer.time:6.1f}s CRUZA BORDA: {a.text!r} x {type(f).__name__}", flush=True)

    Scene.play = _play_checado2


def bloco(rotulo, cor=AZUL, s=30, larg=None, alt=None):
    """Caixa com texto no meio, para diagramas (máquinas, nós, tabelas)."""
    txt = t(rotulo, s, TINTA)
    w = larg or txt.width + 0.6
    h = alt or txt.height + 0.5
    r = RoundedRectangle(width=w, height=h, corner_radius=0.12, stroke_color=cor,
                         stroke_width=3, fill_color=cor, fill_opacity=0.12)
    txt.move_to(r)
    return VGroup(r, txt)


def seta(a, b, cor=APAGADO, buff=0.12):
    """Seta entre dois objetos, saindo e chegando pela lateral da caixa que os
    envolve (e não pelo contorno das letras)."""
    d = b.get_center() - a.get_center()
    if abs(d[0]) >= abs(d[1]):  # mais horizontal: lado a lado
        ini = a.get_right() if d[0] > 0 else a.get_left()
        fim = b.get_left() if d[0] > 0 else b.get_right()
    else:  # mais vertical: um em cima do outro
        ini = a.get_bottom() if d[1] < 0 else a.get_top()
        fim = b.get_top() if d[1] < 0 else b.get_bottom()
    return Arrow(ini, fim, color=cor, buff=buff, stroke_width=4, max_tip_length_to_length_ratio=0.2)
