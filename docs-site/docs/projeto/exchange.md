# Exchange (meu serviço)

Microsserviço de câmbio em **Python 3.13 + FastAPI**, que usa como API externa o **PTAX do Banco
Central do Brasil**. Enunciado: [Exchange API](https://insper.github.io/platform/2026.2/exercises/exchange/).
Código: [EP-PC/Exchange-service](https://github.com/EP-PC/Exchange-service), submódulo
`api/exchange-service` do store-pma.

## Contrato

O Order já estava pronto e testado contra um contrato combinado
([`EXCHANGE.md`](https://github.com/EP-PC/store-pma/blob/main/EXCHANGE.md)). O Exchange segue esse
contrato, então entrou no projeto **sem mudar o Order nem o gateway**.

| Item | Decisão |
|---|---|
| Endpoint | `GET /exchange/{from}/{to}` (singular: é a rota que o gateway já tinha, `/exchange/**`) |
| Autenticação | header `id-account` (posto pelo gateway); sem ele, **401** |
| Resposta 200 | `{"sell": 5.8102, "buy": 5.8096, "date": "2026-11-18 13:08:44", "id-account": "..."}` |
| Moeda não suportada | **404** (o Order devolve 422 ao cliente) |
| PTAX fora/erro | **503** (o Order devolve 503) |
| Health-check | `GET /exchange/health-check`: 200, sem login |
| Tempo | o Order espera até 5 s; o Exchange limita cada chamada ao PTAX a 1,5 s |

`sell` e `buy` são a cotação de **1 `from` em `to`**. O Order usa o `sell` (taxa de venda): para
pagar em reais um pedido em dólar, o cliente compra dólar, e a casa de câmbio vende.

!!! note "Por que o singular"

    O enunciado escreve `GET /exchanges/{from}/{to}` no título, mas o exemplo dele é
    `GET /exchange/USD/EUR`. O gateway já roteava `/exchange/**`; com o plural, a rota do gateway
    teria que mudar.

## Por que o PTAX

O site da disciplina avisa que algumas APIs de câmbio gratuitas **bloqueiam requisições vindas da
AWS**: o serviço funciona no notebook e falha no EKS. O PTAX é público, não pede chave nem
cadastro e responde de qualquer lugar. Sem chave, o serviço também não precisa de Secret.

O site oferece um "BACEN Service" pronto. **Não usei**: escrevi o serviço do zero porque o
pronto não segue o contrato do Order (devolve 422 sem o header em vez de 401 e escuta na porta
8000) e porque o cache dele não seria um bottleneck implementado por mim.

## Como a cotação é calculada

O PTAX só cota moedas em reais: para cada moeda, compra `c` e venda `v` de 1 unidade em BRL.
Para `USD → EUR`, o serviço faz a **taxa cruzada** passando pelo real:

$$
\text{buy} = \frac{c_{USD}}{v_{EUR}} \qquad \text{sell} = \frac{v_{USD}}{c_{EUR}}
$$

- `buy`: o mercado compra seus dólares (paga `c_USD` reais) e te vende euros (cobra `v_EUR`).
- `sell`: o mercado te vende dólares e compra seus euros. Por isso `sell > buy` (o spread).
- O BRL vale 1, então `USD → BRL` é a própria cotação do dólar.
- O serviço busca os boletins dos **últimos 7 dias** e usa o mais recente: fim de semana e
  feriado não têm boletim.
- Moedas suportadas: a lista `/Moedas` do PTAX (AUD, CAD, CHF, DKK, EUR, GBP, JPY, NOK, SEK, USD)
  mais o BRL. Qualquer outra (`XYZ`, `REAL`) dá 404 sem chamar o PTAX.

## Código

| Arquivo | O que faz |
|---|---|
| `main.py` | rotas FastAPI, checagem do `id-account`, tradução de erros em 401/404/503, header `X-Cache` |
| `ptax.py` | cliente do PTAX (`httpx`), taxa cruzada e **cache** (bottleneck 1) |
| `tests/test_exchange.py` | 14 testes com o PTAX simulado (`httpx.MockTransport`) e relógio falso |
| `bench/bench.py` | medição de latência e chamadas ao PTAX (bottleneck 1) |
| `Dockerfile` | `python:3.13-slim` em 3 estágios: base, test (pytest + pip-audit) e final (sem root) |
| `k8s/k8s.yaml` | Deployment + Service `exchange:8080`, probes no health-check, 64–128 Mi |
| `Jenkinsfile` | Test & Audit → Image Scan (Trivy) → Build & Push → Deploy to EKS |

```python title="main.py (trecho)"
@app.get("/exchange/{source}/{target}")
def exchange(source: str, target: str, response: Response,
             id_account: str | None = Header(default=None)) -> dict:
    account = require_account(id_account)          # 401 sem o header
    try:
        rate = ptax.rate(source, target)            # cache + PTAX
    except CurrencyNotFound as e:
        raise HTTPException(status_code=404, detail=f"Currency not supported: {e}")
    except ProviderError:
        raise HTTPException(status_code=503, detail="Exchange rate provider unavailable")
    response.headers["X-Cache"] = rate.cache        # hit, miss ou stale
    return {"sell": rate.sell, "buy": rate.buy,
            "date": rate.when.strftime("%Y-%m-%d %H:%M:%S"), "id-account": account}
```

`Header(default=None)` é importante: sem o default, o FastAPI responderia **422** quando o header
falta, e o contrato pede **401**.

## Testes

| Teste | Garante |
|---|---|
| campos e tipos | `sell`/`buy` numéricos, `date` no formato certo, `id-account` igual ao header, boletim mais recente |
| taxa cruzada | `USD/EUR` e `BRL/USD` batem com as fórmulas |
| 401 | sem header ou header vazio, sem chamar o PTAX |
| 404 | `XYZ` e `REAL` |
| 503 | PTAX fora sem cache, PTAX sem boletim |
| health-check | 200 sem header e sem chamar o PTAX |
| cache | 50 requisições → 1 chamada; expira em 5 min; serve cotação antiga com o PTAX fora |

Teste manual contra o PTAX real (18/11/2026):

```text
GET /exchange/USD/BRL  -> 200 {"sell":5.8102,"buy":5.8096,"date":"2026-11-18 13:08:44",...}  X-Cache: miss
GET /exchange/USD/EUR  -> 200 {"sell":0.912091,"buy":0.911739,...}
GET /exchange/usd/jpy  -> 200 {"sell":159.314505,"buy":159.254386,...}
GET /exchange/USD/XYZ  -> 404
GET /exchange/USD/BRL  (sem id-account) -> 401
GET /exchange/health-check -> 200 {}
GET /exchange/USD/BRL  (de novo) -> 200  X-Cache: hit
```

## Integração no store-pma

1. `git submodule add -b main https://github.com/EP-PC/Exchange-service.git api/exchange-service`.
2. `api/compose.yaml`: serviço `exchange` (`build: ./exchange-service`), sem porta publicada.
3. `aws/up.ps1`: `exchange-service` na lista de manifestos e `exchange` no `rollout status`.
4. `README.md` do root: linha do Exchange na tabela de serviços.
5. Gateway e Order: **nada mudou**. O `build.sh`/`build.ps1` também não (Python não usa Maven).

Os bottlenecks do Exchange estão em [Bottlenecks](bottlenecks.md#pedro-garcia-exchange).
