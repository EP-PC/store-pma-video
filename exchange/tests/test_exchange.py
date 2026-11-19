"""Testes do Exchange com o PTAX simulado (sem rede): httpx.MockTransport responde no lugar do BCB."""

from datetime import date

import httpx
import pytest
from fastapi.testclient import TestClient

import main
from ptax import Ptax

ACCOUNT = "0195ae95-5be7-7dd3-b35d-7a7d87c404fb"
H = {"id-account": ACCOUNT}

MOEDAS = {"value": [{"simbolo": "USD"}, {"simbolo": "EUR"}]}
QUOTES = {
    # dois boletins do USD: o serviço tem que usar o mais recente
    "USD": [
        {"cotacaoCompra": 5.50, "cotacaoVenda": 5.51, "dataHoraCotacao": "2026-11-17 13:02:30.354667"},
        {"cotacaoCompra": 5.60, "cotacaoVenda": 5.61, "dataHoraCotacao": "2026-11-18 10:06:10.203409"},
    ],
    "EUR": [
        {"cotacaoCompra": 6.40, "cotacaoVenda": 6.42, "dataHoraCotacao": "2026-11-18 10:06:10.203409"},
    ],
}


class FakePtax:
    """Simula o PTAX e conta as chamadas. `down=True` faz toda chamada falhar."""

    def __init__(self):
        self.down = False
        self.calls = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request.url.path)
        if self.down:
            raise httpx.ConnectTimeout("simulado", request=request)
        if request.url.path.endswith("/Moedas"):
            return httpx.Response(200, json=MOEDAS)
        moeda = request.url.params["@moeda"].strip("'")
        return httpx.Response(200, json={"value": QUOTES.get(moeda, [])})


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


@pytest.fixture
def fake():
    return FakePtax()


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def client(fake, clock, monkeypatch):
    p = Ptax(
        base_url="http://ptax.test/odata",
        cache_seconds=300,
        retry_seconds=30,
        max_stale_seconds=3600,
        client=httpx.Client(transport=httpx.MockTransport(fake)),
        clock=clock,
        today=lambda: date(2026, 11, 18),
    )
    monkeypatch.setattr(main, "ptax", p)
    return TestClient(main.app)


# ---------- contrato com o Order ----------

def test_usd_brl_retorna_campos_e_tipos_do_contrato(client):
    r = client.get("/exchange/USD/BRL", headers=H)
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"sell", "buy", "date", "id-account"}
    assert body["sell"] == 5.61 and body["buy"] == 5.60  # boletim mais recente
    assert isinstance(body["sell"], float) and isinstance(body["buy"], float)
    assert body["date"] == "2026-11-18 10:06:10"
    assert body["id-account"] == ACCOUNT


def test_taxa_cruzada_usd_eur(client):
    body = client.get("/exchange/USD/EUR", headers=H).json()
    assert body["buy"] == round(5.60 / 6.42, 6)  # compra(USD) / venda(EUR)
    assert body["sell"] == round(5.61 / 6.40, 6)  # venda(USD) / compra(EUR)
    assert body["sell"] > body["buy"]


def test_brl_usd_e_o_inverso(client):
    body = client.get("/exchange/BRL/USD", headers=H).json()
    assert body["buy"] == round(1 / 5.61, 6)
    assert body["sell"] == round(1 / 5.60, 6)


def test_aceita_minusculas(client):
    assert client.get("/exchange/usd/brl", headers=H).status_code == 200


def test_sem_id_account_401(client, fake):
    assert client.get("/exchange/USD/BRL").status_code == 401
    assert client.get("/exchange/USD/BRL", headers={"id-account": "  "}).status_code == 401
    assert fake.calls == []  # nem chega a chamar o PTAX


def test_moeda_desconhecida_404(client):
    assert client.get("/exchange/USD/XYZ", headers=H).status_code == 404
    assert client.get("/exchange/REAL/BRL", headers=H).status_code == 404


def test_ptax_fora_sem_cache_503(client, fake):
    fake.down = True
    assert client.get("/exchange/USD/BRL", headers=H).status_code == 503


def test_ptax_sem_boletim_503(client, monkeypatch):
    monkeypatch.setitem(QUOTES, "USD", [])
    assert client.get("/exchange/USD/BRL", headers=H).status_code == 503


def test_health_check_sem_login(client, fake):
    r = client.get("/exchange/health-check")
    assert r.status_code == 200
    assert r.json() == {}
    assert fake.calls == []


def test_currencies(client):
    assert client.get("/exchange/currencies", headers=H).json() == ["BRL", "EUR", "USD"]
    assert client.get("/exchange/currencies").status_code == 401


# ---------- bottleneck: cache ----------

def test_cache_evita_chamadas_repetidas(client, fake):
    r1 = client.get("/exchange/USD/BRL", headers=H)
    assert r1.headers["X-Cache"] == "miss"
    for _ in range(50):
        assert client.get("/exchange/USD/BRL", headers=H).headers["X-Cache"] == "hit"
    assert len(fake.calls) == 2  # Moedas + USD, uma vez só


def test_cache_expira(client, fake, clock):
    client.get("/exchange/USD/BRL", headers=H)
    clock.t += 301
    assert client.get("/exchange/USD/BRL", headers=H).headers["X-Cache"] == "miss"
    assert len(fake.calls) == 3  # Moedas (24 h) + USD duas vezes


def test_ptax_fora_serve_cotacao_antiga(client, fake, clock):
    client.get("/exchange/USD/BRL", headers=H)
    fake.down = True
    clock.t += 301
    r = client.get("/exchange/USD/BRL", headers=H)
    assert r.status_code == 200
    assert r.headers["X-Cache"] == "stale"
    assert r.json()["sell"] == 5.61

    # dentro de RETRY_SECONDS não tenta o PTAX de novo
    calls = len(fake.calls)
    clock.t += 10
    assert client.get("/exchange/USD/BRL", headers=H).headers["X-Cache"] == "stale"
    assert len(fake.calls) == calls

    # PTAX voltou: depois de RETRY_SECONDS busca de novo
    fake.down = False
    clock.t += 30
    assert client.get("/exchange/USD/BRL", headers=H).headers["X-Cache"] == "miss"


def test_cotacao_antiga_demais_vira_503(client, fake, clock):
    client.get("/exchange/USD/BRL", headers=H)
    fake.down = True
    clock.t += 3601  # passou de MAX_STALE_SECONDS
    assert client.get("/exchange/USD/BRL", headers=H).status_code == 503
