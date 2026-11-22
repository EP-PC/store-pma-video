# -*- coding: utf-8 -*-
"""Cenas animadas do vídeo do store-pma (sem voz: a narração é gravada por cima).

    SEM_VOZ=1 ALVO=21.2 MARCAS="[0.6, 3.9, 7.2, 11.5, 15.0, 18.9]" \
        python -m manim -qh --frame_rate 30 --disable_caching cenas.py Arquitetura

ALVO   = duração total da cena (s), a do trecho narrado.
MARCAS = em que segundo da cena entra cada elemento, para casar com a frase que fala dele.
Sem as variáveis, a cena usa os tempos padrão.
"""
import json
import os

from base_video import *

CINZA = "#2A2E33"


def marcas(padrao):
    m = os.environ.get("MARCAS")
    return json.loads(m) if m else padrao


def ate(cena, t):
    """Espera até o segundo t da cena (se ainda não chegou)."""
    resto = t - cena.renderer.time
    if resto > 0.02:
        cena.wait(resto)


def folga(cena, fim=0.5):
    """Espera o que falta para a cena durar ALVO segundos."""
    alvo = float(os.environ.get("ALVO", "0") or 0)
    if alvo:
        ate(cena, alvo - fim)


def no(rotulo, borda=AZUL, s=24, larg=None):
    """Caixa de serviço com largura mínima, para as colunas ficarem alinhadas."""
    txt = t(rotulo, s, TINTA)
    w = max(larg or 0, txt.width + 0.45)
    r = RoundedRectangle(width=w, height=txt.height + 0.38, corner_radius=0.1,
                         stroke_color=borda, stroke_width=2.5, fill_color="#181B1F", fill_opacity=1)
    txt.move_to(r)
    return VGroup(r, txt)


def seta(a, b, cor=APAGADO, **kw):
    return Arrow(a, b, buff=0.08, stroke_width=3, color=cor, tip_length=0.18,
                 max_tip_length_to_length_ratio=0.25, **kw)


def legenda(cena, atual, texto):
    """Troca a legenda de baixo."""
    nova = t(texto, 24, APAGADO).to_edge(DOWN, buff=0.55)
    if atual is None:
        cena.play(FadeIn(nova), run_time=0.4)
    else:
        cena.play(FadeOut(atual), FadeIn(nova), run_time=0.4)
    return nova


class Abertura(Aula):
    """titulo · nomes · o que é"""

    def roteiro(self):
        m = marcas([0.2, 2.0, 4.0])
        tit = t("store-pma", 72)
        nomes = t("Pedro Garcia   ·   Pedro Machado   ·   Enzo Perego", 28, AZUL)
        sub = t("uma loja online: cadastro, produtos e pedidos, em microsserviços", 30, APAGADO)
        rod = t("Grupo 05 · Platforms, Microservices, DevOps and APIs · Insper 2026.2", 22, APAGADO)
        VGroup(tit, nomes, sub).arrange(DOWN, buff=0.5).shift(UP * 0.3)
        rod.to_edge(DOWN, buff=0.6)
        self.add(tit, rod)
        ate(self, m[0])
        self.play(Indicate(tit, color=AZUL, scale_factor=1.04), run_time=0.8)
        ate(self, m[1])
        self.play(FadeIn(nomes, shift=UP * 0.1), run_time=0.6)
        ate(self, m[2])
        self.play(FadeIn(sub, shift=UP * 0.1), run_time=0.6)
        folga(self, 0.0)


class Arquitetura(Aula):
    """gateway · auth · account/product/order · exchange · AWS · Jenkins"""

    def roteiro(self):
        m = marcas([0.5, 3.0, 6.0, 10.0, 14.0, 17.5])
        tit = t("arquitetura", 38).to_edge(UP, buff=0.7)

        cliente = no("cliente", APAGADO, 22)
        gw = no("gateway", AZUL, 22)
        servs = VGroup(*[no(n, AZUL if n != "exchange" else AMAR, 22, larg=2.1)
                         for n in ("auth", "account", "product", "order", "exchange")]
                       ).arrange(DOWN, buff=0.2)
        servs.move_to(RIGHT * 0.1 + DOWN * 0.35)
        gw.move_to(LEFT * 2.9 + DOWN * 0.35)
        cliente.move_to(LEFT * 5.6 + DOWN * 0.35)
        auth, account, product, order, exchange = servs
        db = no("PostgreSQL", VERDE, 22).move_to(RIGHT * 4.6).match_y(account)
        redis = no("Redis", VERDE, 22).move_to(RIGHT * 4.6).match_y(order).shift(UP * 0.1)
        ptax = no("PTAX · Banco Central", VERDE, 22).move_to(RIGHT * 4.6).match_y(exchange).shift(DOWN * 0.1)

        s_cg = seta(cliente.get_right(), gw.get_left())
        s_gs = [seta(gw.get_right(), s.get_left()) for s in servs]
        alvo = [db.get_left() + UP * 0.15, db.get_left(), db.get_left() + DOWN * 0.15]
        s_db = [seta(s.get_right(), a, VERDE) for s, a in zip((account, product, order), alvo)]
        s_redis = seta(order.get_right(), redis.get_left(), VERDE)
        s_ptax = seta(exchange.get_right(), ptax.get_left(), AMAR)
        s_oe = CurvedArrow(order.get_left() + LEFT * 0.05, exchange.get_left() + LEFT * 0.05,
                           angle=PI / 1.6, color=AMAR, stroke_width=3, tip_length=0.15)

        self.add(tit, cliente)
        ate(self, m[0])  # "a entrada é um gateway"
        self.play(GrowArrow(s_cg), FadeIn(gw), run_time=0.6)
        leg = legenda(self, None, "o gateway é o único serviço exposto")
        ate(self, m[1])  # "valida o login com o auth"
        self.play(GrowArrow(s_gs[0]), FadeIn(auth, shift=RIGHT * 0.1), run_time=0.6)
        leg = legenda(self, leg, "valida o JWT no auth e repassa id-account / id-role")
        ate(self, m[2])  # "account, product, order em Java com Spring"
        self.play(*[GrowArrow(a) for a in s_gs[1:4]],
                  LaggedStart(*[FadeIn(s, shift=RIGHT * 0.1) for s in (account, product, order)], lag_ratio=0.2),
                  run_time=0.9)
        self.play(FadeIn(db), *[GrowArrow(a) for a in s_db], FadeIn(redis), GrowArrow(s_redis), run_time=0.7)
        leg = legenda(self, leg, "Java + Spring · um schema por serviço no PostgreSQL · Redis de cache no order")
        ate(self, m[3])  # "o exchange em Python, que busca a cotação no Banco Central"
        self.play(GrowArrow(s_gs[4]), FadeIn(exchange, shift=RIGHT * 0.1), run_time=0.5)
        self.play(Create(s_oe), FadeIn(ptax), GrowArrow(s_ptax), run_time=0.7)
        leg = legenda(self, leg, "exchange em Python (FastAPI) · cotação no PTAX do Banco Central")

        ate(self, m[4])  # "na AWS, EKS com dois nós e o banco no RDS"
        caixa = VGroup(gw, servs, s_oe)
        eks = DashedVMobject(RoundedRectangle(width=caixa.width + 0.5, height=caixa.height + 0.45,
                                              corner_radius=0.2, stroke_color=APAGADO, stroke_width=2),
                             num_dashes=80).move_to(caixa)
        eks_rot = t("EKS · 2 nós t3.medium", 22, APAGADO).next_to(eks, UP, buff=0.08).align_to(eks, LEFT)
        lb = no("Load Balancer", APAGADO, 22).move_to(cliente).align_to(cliente, RIGHT)
        rds = no("RDS PostgreSQL 17", VERDE, 22).move_to(db).align_to(db, LEFT)
        self.play(Transform(tit, t("na AWS · us-east-2", 38).move_to(tit)), Create(eks), FadeIn(eks_rot),
                  Transform(cliente, lb), Transform(db, rds), run_time=1.2)
        leg = legenda(self, leg, "tudo criado por CloudFormation (aws/up.ps1)")

        ate(self, m[5])  # "o Jenkins builda e faz o deploy a cada push"
        pipe = VGroup(*[no(n, c, 22) for n, c in (("git push", APAGADO), ("Jenkins", AMAR),
                                                  ("Docker Hub", AZUL), ("kubectl set image", VERDE))]
                      ).arrange(RIGHT, buff=0.7).move_to(leg)
        s_pipe = [seta(a.get_right(), b.get_left()) for a, b in zip(pipe[:-1], pipe[1:])]
        self.play(FadeOut(leg), run_time=0.2)
        self.play(LaggedStart(*[FadeIn(p) for p in pipe], lag_ratio=0.35),
                  LaggedStart(*[GrowArrow(s) for s in s_pipe], lag_ratio=0.35), run_time=1.4)
        folga(self, 0.0)


class Gargalos(Aula):
    """nomes · HPA · readiness · Redis/Grafana · exchange"""

    def roteiro(self):
        m = marcas([0.3, 2.5, 5.0, 7.5, 10.0])
        self.add(t("bottlenecks · 2 por integrante", 38, AMAR).to_edge(UP, buff=0.7))
        dados = [
            ("Pedro Machado", ("HPA no gateway", "p95  770 → 320 ms"), ("readinessProbe", "deploy sem 40 s de erro")),
            ("Enzo Perego", ("Redis no order", "p50  335 → 10 ms"), ("Prometheus + Grafana", "p95 por rota, acerto do cache")),
            ("Pedro Garcia", ("cache no exchange", "chamadas ao PTAX  101 → 2"), ("pip-audit + Trivy", "imagem barrada → corrigida")),
        ]
        linhas = VGroup()
        for nome, b1, b2 in dados:
            c0 = t(nome, 28, AZUL)
            c1 = VGroup(t(b1[0], 26), t(b1[1], 26, VERDE)).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
            c2 = VGroup(t(b2[0], 26), t(b2[1], 26, VERDE)).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
            linhas.add(VGroup(c0, c1, c2))
        linhas.arrange(DOWN, buff=0.75).move_to(DOWN * 0.35)
        for r in linhas:
            r[0].align_to(LEFT * 6.0, LEFT)
            r[1].align_to(LEFT * 2.4, LEFT)
            r[2].align_to(RIGHT * 1.9, LEFT)
        sep = VGroup(*[Line(LEFT * 6.1, RIGHT * 6.3, color=CINZA, stroke_width=2)
                       .move_to((linhas[i].get_bottom() + linhas[i + 1].get_top()) / 2 * UP) for i in range(2)])

        ate(self, m[0])  # "foram seis bottlenecks, dois por integrante"
        self.play(LaggedStart(*[FadeIn(r[0], shift=RIGHT * 0.1) for r in linhas], lag_ratio=0.25),
                  Create(sep), run_time=0.9)
        ate(self, m[1])  # "no gateway, o HPA..."
        self.play(FadeIn(linhas[0][1], shift=RIGHT * 0.1), run_time=0.5)
        ate(self, m[2])  # "...e a readiness probe"
        self.play(FadeIn(linhas[0][2], shift=RIGHT * 0.1), run_time=0.5)
        ate(self, m[3])  # "no order, cache com Redis e monitoramento"
        self.play(FadeIn(linhas[1][1], shift=RIGHT * 0.1), FadeIn(linhas[1][2], shift=RIGHT * 0.1), run_time=0.6)
        ate(self, m[4])  # adianta a linha do exchange (bloco seguinte)
        self.play(FadeIn(linhas[2][1], shift=RIGHT * 0.1), FadeIn(linhas[2][2], shift=RIGHT * 0.1), run_time=0.6)
        folga(self, 0.0)


class Nuvem(Aula):
    """custo · sobe e derruba · SLA"""

    def roteiro(self):
        m = marcas([1.5, 4.0, 6.5])
        self.add(t("quanto custa e quanto aguenta", 38).to_edge(UP, buff=0.7))
        grande = t("US$ 0,34 / hora", 64, VERDE)
        l1 = t("EKS + 2 nós t3.medium + 2 NAT + Load Balancer + RDS db.t4g.micro", 26, APAGADO)
        l2 = t("~US$ 250/mês se ficasse ligado: sobe e derruba com aws/up.ps1 e aws/down.ps1", 26, APAGADO)
        sla = t("SLA composto ≈ 99,4%  ·  ponto fraco: RDS numa zona só (Multi-AZ → 99,9%)", 28, AMAR)
        VGroup(grande, l1, l2, sla).arrange(DOWN, buff=0.42).move_to(DOWN * 0.3)
        ate(self, m[0])  # "custa cerca de 34 centavos"
        self.play(Write(grande), FadeIn(l1), run_time=0.9)
        ate(self, m[1])  # "por isso sobe e é derrubado por script"
        self.play(FadeIn(l2), run_time=0.5)
        ate(self, m[2])  # "o ponto fraco..."
        self.play(FadeIn(sla, shift=UP * 0.1), run_time=0.5)
        folga(self, 0.0)


class Fecho(Aula):
    """funciona · próximos passos"""

    def roteiro(self):
        m = marcas([0.2, 1.6])
        g = VGroup(
            t("funcionando de ponta a ponta", 46, VERDE),
            t("compose · Minikube · EKS  ·  CI/CD com Jenkins  ·  HPA  ·  6 bottlenecks medidos", 26, APAGADO),
            t("próximos passos: banco em várias zonas · mais réplicas · autoscaling do cluster", 26, AMAR),
            t("documentação: ep-pc.github.io/store-pma-docs", 26, AZUL),
        ).arrange(DOWN, buff=0.5)
        self.add(g[0])
        ate(self, m[0])  # "a loja funciona de ponta a ponta"
        self.play(Indicate(g[0], color=VERDE, scale_factor=1.04), FadeIn(g[1]), run_time=0.8)
        ate(self, m[1])  # "os próximos passos são..."
        self.play(FadeIn(g[2:], lag_ratio=0.3), run_time=0.8)
        folga(self, 0.0)
