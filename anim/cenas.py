# -*- coding: utf-8 -*-
"""Cenas animadas do vídeo do store-pma (sem voz: a narração é gravada por cima).

    SEM_VOZ=1 python -m manim -qh --frame_rate 30 --disable_caching cenas.py Abertura

Cada cena tem duração fixa, combinada com o roteiro (ROTEIRO.md).
"""
from base_video import *

CINZA = "#2A2E33"


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


class Abertura(Aula):
    """0:00 a 0:07"""

    def roteiro(self):
        tit = t("store-pma", 72)
        sub = t("uma loja de produtos feita de microsserviços", 32, APAGADO)
        nomes = t("Pedro   ·   Enzo Perego   ·   Pedro Garcia", 28, AZUL)
        rod = t("Grupo 05 · Platforms, Microservices, DevOps and APIs · Insper 2026.2", 22, APAGADO)
        g = VGroup(tit, sub, nomes).arrange(DOWN, buff=0.45).shift(UP * 0.3)
        rod.to_edge(DOWN, buff=0.6)
        self.play(Write(tit), run_time=1.4)
        self.play(FadeIn(sub, shift=UP * 0.1), run_time=0.7)
        self.play(FadeIn(nomes), FadeIn(rod), run_time=0.7)
        self.wait(3.7)
        self.limpa()


class Arquitetura(Aula):
    """0:07 a 0:30: os serviços e, depois, como isso fica na AWS."""

    def roteiro(self):
        tit = self.titulo("arquitetura", TINTA, 38)

        cliente = no("cliente", APAGADO, 22)
        gw = no("gateway", AZUL, 22)
        servs = VGroup(*[no(n, AZUL if n != "exchange" else AMAR, 22, larg=2.1)
                         for n in ("auth", "account", "product", "order", "exchange")]
                       ).arrange(DOWN, buff=0.2)
        db = no("PostgreSQL", VERDE, 22)
        redis = no("Redis", VERDE, 22)
        ptax = no("PTAX · Banco Central", VERDE, 22)

        servs.move_to(RIGHT * 0.1 + DOWN * 0.35)
        gw.move_to(LEFT * 2.9 + DOWN * 0.35)
        cliente.move_to(LEFT * 5.6 + DOWN * 0.35)
        auth, account, product, order, exchange = servs
        db.move_to(RIGHT * 4.6).match_y(account)
        redis.move_to(RIGHT * 4.6).match_y(order).shift(UP * 0.1)
        ptax.move_to(RIGHT * 4.6).match_y(exchange).shift(DOWN * 0.1)

        s_cg = seta(cliente.get_right(), gw.get_left())
        s_gs = VGroup(*[seta(gw.get_right(), s.get_left()) for s in servs])
        alvo = [db.get_left() + UP * 0.15, db.get_left(), db.get_left() + DOWN * 0.15]
        s_db = VGroup(*[seta(s.get_right(), a, VERDE) for s, a in zip((account, product, order), alvo)])
        s_redis = seta(order.get_right(), redis.get_left(), VERDE)
        s_ptax = seta(exchange.get_right(), ptax.get_left(), AMAR)
        s_oe = CurvedArrow(order.get_left() + LEFT * 0.05, exchange.get_left() + LEFT * 0.05,
                           angle=PI / 1.6, color=AMAR, stroke_width=3, tip_length=0.15)

        leg = t("só o gateway é exposto: ele valida o JWT no auth e repassa id-account / id-role",
                24, APAGADO).to_edge(DOWN, buff=0.55)

        self.play(FadeIn(cliente), run_time=0.4)
        self.play(GrowArrow(s_cg), FadeIn(gw), run_time=0.6)
        self.play(LaggedStart(*[GrowArrow(a) for a in s_gs], lag_ratio=0.15),
                  LaggedStart(*[FadeIn(s, shift=RIGHT * 0.1) for s in servs], lag_ratio=0.15),
                  run_time=1.6)
        self.play(FadeIn(leg), run_time=0.5)
        self.wait(1.4)
        self.play(FadeIn(db), LaggedStart(*[GrowArrow(a) for a in s_db], lag_ratio=0.2), run_time=1.0)
        self.play(FadeIn(redis), GrowArrow(s_redis), run_time=0.6)
        self.play(Create(s_oe), run_time=0.7)
        self.play(FadeIn(ptax), GrowArrow(s_ptax), run_time=0.7)
        leg2 = t("Java + Spring nos 5 serviços · exchange em Python (FastAPI) · um schema por serviço",
                 24, APAGADO).move_to(leg)
        self.play(FadeOut(leg), FadeIn(leg2), run_time=0.5)
        self.wait(2.0)

        # --- na AWS
        caixa = VGroup(gw, servs, s_oe)
        eks = DashedVMobject(RoundedRectangle(width=caixa.width + 0.5, height=caixa.height + 0.45,
                                              corner_radius=0.2, stroke_color=APAGADO, stroke_width=2),
                             num_dashes=80).move_to(caixa)
        eks_rot = t("EKS · 2 nós t3.medium", 22, APAGADO).next_to(eks, UP, buff=0.08).align_to(eks, LEFT)
        lb = no("Load Balancer", APAGADO, 22).move_to(cliente).align_to(cliente, RIGHT)
        rds = no("RDS PostgreSQL 17", VERDE, 22).move_to(db).align_to(db, LEFT)
        tit2 = t("na AWS · us-east-2", 38).move_to(tit)
        leg3 = t("tudo por CloudFormation: aws/up.ps1 sobe em ~30 min, aws/down.ps1 derruba",
                 24, APAGADO).move_to(leg)
        self.play(Transform(tit, tit2), Create(eks), FadeIn(eks_rot),
                  Transform(cliente, lb), Transform(db, rds), FadeOut(leg2), FadeIn(leg3), run_time=1.2)
        self.wait(1.6)

        pipe = VGroup(*[no(n, c, 22) for n, c in (("git push", APAGADO), ("Jenkins", AMAR),
                                                  ("Docker Hub", AZUL), ("kubectl set image", VERDE))]
                      ).arrange(RIGHT, buff=0.7).move_to(leg)
        s_pipe = VGroup(*[seta(a.get_right(), b.get_left()) for a, b in zip(pipe[:-1], pipe[1:])])
        self.play(FadeOut(leg3), run_time=0.3)
        self.play(LaggedStart(*[FadeIn(p) for p in pipe], lag_ratio=0.35),
                  LaggedStart(*[GrowArrow(s) for s in s_pipe], lag_ratio=0.35), run_time=1.6)
        self.wait(2.6)
        self.limpa()


class Gargalos(Aula):
    """bottlenecks: 2 por integrante, com os números medidos."""

    def roteiro(self):
        self.titulo("bottlenecks · 2 por integrante", AMAR, 38)
        linhas = [
            ("Pedro", "HPA no gateway", "p95  770 → 320 ms", "readinessProbe", "deploy sem 40 s de 503"),
            ("Enzo", "Redis no order", "p50  335 → 10 ms", "Prometheus + Grafana", "p95 por rota, acerto do cache"),
            ("Pedro Garcia", "cache no exchange", "p50  234 → 3,7 ms", "pip-audit + Trivy", "15 → 0 vulnerabilidades"),
        ]
        rows = VGroup()
        for nome, b1, n1, b2, n2 in linhas:
            c0 = t(nome, 28, AZUL)
            c1 = VGroup(t(b1, 26), t(n1, 26, VERDE)).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
            c2 = VGroup(t(b2, 26), t(n2, 26, VERDE)).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
            c0.move_to(LEFT * 4.6, aligned_edge=LEFT)
            c1.move_to(LEFT * 1.4, aligned_edge=LEFT)
            c2.move_to(RIGHT * 2.9, aligned_edge=LEFT)
            rows.add(VGroup(c0, c1, c2))
        rows.arrange(DOWN, buff=0.75).move_to(DOWN * 0.35)
        for r in rows:
            r[0].align_to(LEFT * 6.0, LEFT)
            r[1].align_to(LEFT * 2.4, LEFT)
            r[2].align_to(RIGHT * 1.9, LEFT)
        linhas_sep = VGroup(*[Line(LEFT * 6.1, RIGHT * 6.3, color=CINZA, stroke_width=2)
                              .move_to((rows[i].get_bottom() + rows[i + 1].get_top()) / 2 * UP)
                              for i in range(2)])
        for i, r in enumerate(rows):
            self.play(FadeIn(r[0], shift=RIGHT * 0.1), FadeIn(r[1], shift=RIGHT * 0.1), run_time=0.6)
            self.play(FadeIn(r[2], shift=RIGHT * 0.1), run_time=0.5)
            if i < 2:
                self.play(Create(linhas_sep[i]), run_time=0.3)
            self.wait(1.9)
        self.wait(1.4)
        self.limpa()


class Nuvem(Aula):
    """custos e SLA da AWS."""

    def roteiro(self):
        self.titulo("quanto custa e quanto aguenta", TINTA, 38)
        grande = t("US$ 0,34 / hora", 64, VERDE)
        l1 = t("EKS + 2 nós t3.medium + 2 NAT + Load Balancer + RDS db.t4g.micro", 26, APAGADO)
        l2 = t("~US$ 250/mês se ficasse ligado; o grupo sobe e derruba com up.ps1 / down.ps1", 26, APAGADO)
        sla = t("SLA composto ≈ 99,4%  ·  elo fraco: RDS Single-AZ (Multi-AZ → 99,9%)", 28, AMAR)
        g = VGroup(grande, l1, l2, sla).arrange(DOWN, buff=0.42).move_to(DOWN * 0.3)
        self.play(Write(grande), run_time=1.0)
        self.play(FadeIn(l1), run_time=0.5)
        self.play(FadeIn(l2), run_time=0.5)
        self.wait(1.6)
        self.play(FadeIn(sla, shift=UP * 0.1), run_time=0.6)
        self.wait(2.6)
        self.limpa()


class Fecho(Aula):
    """conclusão e próximos passos."""

    def roteiro(self):
        g = VGroup(
            t("funcionando de ponta a ponta", 46, VERDE),
            t("compose · Minikube · EKS  ·  CI/CD com Jenkins  ·  HPA  ·  6 bottlenecks medidos", 26, APAGADO),
            t("próximos passos: RDS Multi-AZ · 2 réplicas por serviço · Cluster Autoscaler", 26, AMAR),
            t("documentação: garciapp2.github.io/store-pma-docs", 26, AZUL),
        ).arrange(DOWN, buff=0.5)
        self.play(Write(g[0]), run_time=1.2)
        self.play(FadeIn(g[1:], lag_ratio=0.35), run_time=1.2)
        self.wait(3.8)
        self.play(FadeOut(g), run_time=0.8)
