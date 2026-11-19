"""Cliente do PTAX (Banco Central do Brasil) com cache em memória.

O PTAX só cota moedas contra o real (BRL). Para USD -> EUR o serviço busca as duas cotações
em BRL e divide uma pela outra (taxa cruzada):

    buy  = compra(from) / venda(to)    o que o mercado PAGA por 1 `from`, em `to`
    sell = venda(from)  / compra(to)   o que o mercado COBRA por 1 `from`, em `to`

O BRL vale 1 (compra = venda = 1), então USD -> BRL é a própria cotação do dólar.

Cache (bottleneck 1): cada cotação fica guardada por CACHE_SECONDS. Se o PTAX falhar e
houver uma cotação antiga (até MAX_STALE_SECONDS), o serviço responde com ela ("stale")
em vez de devolver 503, e só tenta o PTAX de novo depois de RETRY_SECONDS.
Só uma requisição por moeda busca no PTAX por vez (lock por moeda): as outras esperam
e usam o valor que ela trouxe, em vez de todas chamarem o Banco Central juntas.
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Callable

import httpx

log = logging.getLogger("exchange.ptax")

DEFAULT_URL = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata"
BRL = "BRL"
CODE = re.compile(r"^[A-Z]{3}$")
# Brasília é UTC-3 o ano inteiro (sem horário de verão desde 2019). Fuso fixo para não
# depender do banco de fusos (tzdata) dentro da imagem slim.
BRASILIA = timezone(timedelta(hours=-3))
# fim de semana e feriado não têm boletim: busca os últimos 7 dias e usa o mais recente
WINDOW_DAYS = 7


class CurrencyNotFound(Exception):
    """Moeda que o PTAX não cota (vira 404)."""


class ProviderError(Exception):
    """PTAX fora do ar, lento ou com resposta inválida, e sem cotação antiga (vira 503)."""


@dataclass(frozen=True)
class Quote:
    """Cotação de 1 unidade da moeda em BRL."""

    buy: float  # cotacaoCompra
    sell: float  # cotacaoVenda
    when: datetime  # dataHoraCotacao do boletim


@dataclass(frozen=True)
class Rate:
    buy: float
    sell: float
    when: datetime
    cache: str  # "hit", "miss" ou "stale" (vai no header X-Cache)


@dataclass
class _Entry:
    value: object
    fetched_at: float  # quando veio do PTAX (relógio monotônico)
    expires_at: float  # até quando vale sem perguntar de novo
    stale: bool = False  # True: o PTAX falhou e este é um valor antigo


class Ptax:
    def __init__(
        self,
        base_url: str = DEFAULT_URL,
        timeout: float = 1.5,
        cache_seconds: float = 300,
        retry_seconds: float = 30,
        max_stale_seconds: float = 86400,
        client: httpx.Client | None = None,
        clock: Callable[[], float] = time.monotonic,
        today: Callable[[], date] = lambda: datetime.now(BRASILIA).date(),
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.cache_seconds = cache_seconds
        self.retry_seconds = retry_seconds
        self.max_stale_seconds = max_stale_seconds
        self.client = client or httpx.Client(timeout=timeout)
        self.clock = clock
        self.today = today
        self.calls = 0  # chamadas feitas ao PTAX (para medir o efeito do cache)
        self._cache: dict[str, _Entry] = {}
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    @classmethod
    def from_env(cls) -> "Ptax":
        env = os.environ.get
        return cls(
            base_url=env("PTAX_URL", DEFAULT_URL),
            timeout=float(env("PTAX_TIMEOUT", "1.5")),
            cache_seconds=float(env("CACHE_SECONDS", "300")),
            retry_seconds=float(env("RETRY_SECONDS", "30")),
            max_stale_seconds=float(env("MAX_STALE_SECONDS", "86400")),
        )

    # ---------- API pública ----------

    def currencies(self) -> list[str]:
        """Moedas que o PTAX cota, mais o BRL. A lista muda raramente: cache de 24 h."""
        codes, _ = self._cached("currencies", self._fetch_currencies, ttl=86400)
        return sorted(codes | {BRL})

    def rate(self, source: str, target: str) -> Rate:
        source, target = source.strip().upper(), target.strip().upper()
        supported = self.currencies()
        for code in (source, target):
            if not CODE.match(code) or code not in supported:
                raise CurrencyNotFound(code)

        q_from, s_from = self._quote(source)
        q_to, s_to = self._quote(target)
        statuses = {s_from, s_to}
        status = "stale" if "stale" in statuses else "miss" if "miss" in statuses else "hit"

        dates = [q.when for code, q in ((source, q_from), (target, q_to)) if code != BRL]
        return Rate(
            buy=round(q_from.buy / q_to.sell, 6),
            sell=round(q_from.sell / q_to.buy, 6),
            # a data do boletim mais antigo usado na conta
            when=min(dates) if dates else datetime.now(BRASILIA).replace(tzinfo=None),
            cache=status,
        )

    # ---------- cache ----------

    def _quote(self, code: str) -> tuple[Quote, str]:
        if code == BRL:
            return Quote(1.0, 1.0, datetime.now(BRASILIA).replace(tzinfo=None)), "hit"
        return self._cached(code, lambda: self._fetch_quote(code), ttl=self.cache_seconds)

    def _lock(self, key: str) -> threading.Lock:
        with self._locks_guard:
            return self._locks.setdefault(key, threading.Lock())

    def _cached(self, key: str, fetch: Callable[[], object], ttl: float):
        entry = self._cache.get(key)
        if entry and self.clock() < entry.expires_at:
            return entry.value, "stale" if entry.stale else "hit"

        with self._lock(key):
            # outra requisição pode ter atualizado enquanto esta esperava o lock
            entry = self._cache.get(key)
            now = self.clock()
            if entry and now < entry.expires_at:
                return entry.value, "stale" if entry.stale else "hit"
            try:
                value = fetch()
            except ProviderError:
                if entry and now - entry.fetched_at <= self.max_stale_seconds:
                    log.warning("PTAX falhou para %s: usando cotação antiga", key)
                    entry.expires_at = now + self.retry_seconds
                    entry.stale = True
                    return entry.value, "stale"
                raise
            self._cache[key] = _Entry(value, fetched_at=now, expires_at=now + ttl)
            return value, "miss"

    # ---------- chamadas ao PTAX ----------

    def _get(self, path: str, params: dict[str, str]) -> list[dict]:
        self.calls += 1
        start = time.perf_counter()
        try:
            resp = self.client.get(f"{self.base_url}/{path}", params={**params, "$format": "json"})
            resp.raise_for_status()
            values = resp.json()["value"]
            if not isinstance(values, list):
                raise ValueError("value não é lista")
            return values
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as e:
            raise ProviderError(f"PTAX: {e.__class__.__name__}") from e
        finally:
            log.info("PTAX %s em %.0f ms", path.split("(")[0], (time.perf_counter() - start) * 1000)

    def _fetch_currencies(self) -> set[str]:
        values = self._get("Moedas", {})
        codes = {v.get("simbolo") for v in values}
        codes.discard(None)
        if not codes:
            raise ProviderError("PTAX: lista de moedas vazia")
        return codes

    def _fetch_quote(self, code: str) -> Quote:
        end = self.today()
        start = end - timedelta(days=WINDOW_DAYS)
        values = self._get(
            "CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)",
            {
                "@moeda": f"'{code}'",
                "@dataInicial": f"'{start:%m-%d-%Y}'",
                "@dataFinalCotacao": f"'{end:%m-%d-%Y}'",
            },
        )
        try:
            latest = max(values, key=lambda v: v["dataHoraCotacao"])
            quote = Quote(
                buy=float(latest["cotacaoCompra"]),
                sell=float(latest["cotacaoVenda"]),
                when=datetime.fromisoformat(latest["dataHoraCotacao"]).replace(microsecond=0),
            )
        except (ValueError, KeyError, TypeError) as e:
            # lista vazia (sem boletim em 7 dias) ou campos faltando/inválidos
            raise ProviderError(f"PTAX: cotação inválida para {code}") from e
        if quote.buy <= 0 or quote.sell <= 0:
            raise ProviderError(f"PTAX: cotação não positiva para {code}")
        return quote
