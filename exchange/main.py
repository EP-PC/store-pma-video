"""Exchange: cotação de moedas para o store-pma (contrato com o Order em store-pma/EXCHANGE.md).

GET /exchange/{from}/{to}   cotação de 1 `from` em `to` (exige o header id-account)
GET /exchange/currencies    moedas suportadas (exige o header id-account)
GET /exchange/health-check  200 sem login, para as probes do Kubernetes

O gateway já validou o JWT e injeta o header id-account; aqui só conferimos que ele veio.
"""

import logging

from fastapi import FastAPI, Header, HTTPException, Response

from ptax import CurrencyNotFound, Ptax, ProviderError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="exchange", docs_url=None, redoc_url=None, openapi_url=None)
ptax = Ptax.from_env()


def require_account(id_account: str | None) -> str:
    # Header() converte id_account em "id-account". Sem default=None, o FastAPI devolveria
    # 422 quando o header falta; o contrato pede 401.
    if not id_account or not id_account.strip():
        raise HTTPException(status_code=401, detail="Not authenticated")
    return id_account


# declarado antes de /exchange/{source}/{target} por clareza (não conflita: tem um segmento a menos)
@app.get("/exchange/health-check")
def health_check() -> dict:
    return {}


@app.get("/exchange/currencies")
def currencies(id_account: str | None = Header(default=None)) -> list[str]:
    require_account(id_account)
    try:
        return ptax.currencies()
    except ProviderError:
        raise HTTPException(status_code=503, detail="Exchange rate provider unavailable")


@app.get("/exchange/{source}/{target}")
def exchange(
    source: str,
    target: str,
    response: Response,
    id_account: str | None = Header(default=None),
) -> dict:
    account = require_account(id_account)
    try:
        rate = ptax.rate(source, target)
    except CurrencyNotFound as e:
        raise HTTPException(status_code=404, detail=f"Currency not supported: {e}")
    except ProviderError:
        raise HTTPException(status_code=503, detail="Exchange rate provider unavailable")

    response.headers["X-Cache"] = rate.cache
    return {
        "sell": rate.sell,
        "buy": rate.buy,
        "date": rate.when.strftime("%Y-%m-%d %H:%M:%S"),
        "id-account": account,
    }
