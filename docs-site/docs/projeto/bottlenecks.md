# Bottlenecks

A [página de apresentação](https://insper.github.io/platform/2026.2/exercises/project/presentation/)
pede **pelo menos 2 bottlenecks por integrante**. As opções estão na página
[Bottlenecks](https://insper.github.io/platform/2026.2/exercises/bottlenecks/): caching,
observability, messaging, load balancing, vulnerability scanning, payment processing e RBAC/OAuth2.

| Integrante | Bottleneck 1 | Bottleneck 2 |
|---|---|---|
| Pedro Garcia (Exchange) | **Caching**: cache das cotações com fallback | **Vulnerability scanning**: pip-audit + Trivy no pipeline |
| Enzo Perego (Order) | **Caching**: Redis para preços e cotações | **Observability**: Prometheus + Grafana |
| Pedro (Gateway, Auth, Account, Product) | **Load balancing / escala**: HPA do gateway | **Disponibilidade no deploy**: readinessProbe |

## Pedro Garcia (Exchange)

### 1. Cache das cotações com fallback

**Problema.** Cada conversão chamava o PTAX do Banco Central (~230 ms). Além da latência, o
Exchange ficava preso à disponibilidade de um serviço público: se o PTAX caísse, toda conversão
de pedido do Order virava 503. E o site pede para **não fazer teste de carga contra o PTAX**.

**Solução** (`ptax.py`):

- cache em memória **por moeda**, TTL de 5 min (`CACHE_SECONDS`). Como a cotação é a mesma para
  todos os usuários, a de um aproveita a do outro;
- **um lock por moeda** (*single flight*): com o cache vazio e várias requisições ao mesmo tempo,
  só uma vai ao PTAX; as outras esperam e usam o valor que ela trouxe;
- **fallback**: se o PTAX falhar e houver uma cotação de até 24 h (`MAX_STALE_SECONDS`), o serviço
  responde com ela (`X-Cache: stale`) em vez de 503, e só tenta o PTAX de novo a cada 30 s
  (`RETRY_SECONDS`), para não martelar um serviço que está fora;
- lista de moedas em cache por 24 h: moeda inválida (`XYZ`) dá 404 sem chamar o PTAX.

```python title="ptax.py (trecho)"
with self._lock(key):                      # uma busca por moeda por vez
    entry = self._cache.get(key)
    now = self.clock()
    if entry and now < entry.expires_at:   # outra requisição já atualizou
        return entry.value, "hit"
    try:
        value = fetch()                     # PTAX
    except ProviderError:
        if entry and now - entry.fetched_at <= self.max_stale_seconds:
            entry.expires_at = now + self.retry_seconds
            entry.stale = True
            return entry.value, "stale"     # cotação antiga em vez de 503
        raise
    self._cache[key] = _Entry(value, fetched_at=now, expires_at=now + ttl)
    return value, "miss"
```

**Como testar.** `bench/bench.py` dispara 100 × `GET /exchange/USD/BRL` (5 em paralelo) e conta o
header `X-Cache`. Rodei uma vez com `CACHE_SECONDS=0` (cache desligado) e outra com o padrão,
sempre com o serviço recém-iniciado e contra o PTAX real (18/11/2026):

| | Sem cache | Com cache | Diferença |
|---|---|---|---|
| Latência p50 | 233,9 ms | 3,7 ms | **−98%** |
| Latência p95 | 279,7 ms | 5,5 ms | **−98%** |
| Vazão | 20 req/s | 347 req/s | **17×** |
| Chamadas ao PTAX | 101 | 2 | **−98%** |

```text
== SEM cache ==
requisicoes: 100 (5 em paralelo) em 4.92 s -> 20 req/s
X-Cache: {'miss': 100}
latencia ms: p50=233.9 p95=279.7 max=387.4
chamadas PTAX: 101
== COM cache (servico frio) ==
requisicoes: 100 (5 em paralelo) em 0.29 s -> 347 req/s
X-Cache: {'miss': 1, 'hit': 99}
latencia ms: p50=3.7 p95=5.5 max=216.3
chamadas PTAX: 2
```

As 5 primeiras requisições chegaram juntas com o cache vazio e só **uma** foi ao PTAX: o lock
funcionou. A outra chamada é a lista de moedas. O fallback está coberto pelos testes
`test_ptax_fora_serve_cotacao_antiga` e `test_cotacao_antiga_demais_vira_503`, que usam um PTAX
simulado e um relógio falso.

**Relação com o Order.** O Order também guarda a cotação no Redis por 60 s. As duas camadas se
completam: a do Order evita a chamada de rede ao Exchange; a do Exchange protege o PTAX quando
há várias réplicas do Order, quando alguém chama `/exchange` direto pelo gateway e quando o PTAX
cai. O Order tinha apontado como próximo passo cachear "moeda inválida"; no Exchange, moeda
inválida já responde 404 sem chamar o PTAX, porque a lista de moedas fica em cache por 24 h.

**Limite.** O cache vive na memória do processo: com N réplicas, cada pod faz no máximo uma
chamada por moeda a cada 5 min. Para compartilhar entre pods, o próximo passo seria Redis.

### 2. Varredura de vulnerabilidades no pipeline

**Problema.** Uma dependência com vulnerabilidade conhecida, ou uma imagem base desatualizada,
chegava ao Docker Hub e ao EKS sem ninguém perceber: o pipeline só buildava e publicava.

**Solução** (`Dockerfile` + `Jenkinsfile`):

1. **`Test & Audit`**: `docker build --target test` roda `pytest` e
   [`pip-audit`](https://github.com/pypa/pip-audit) (base de vulnerabilidades do PyPI/OSV) nas
   versões fixadas em `requirements.txt`. Teste falhando ou vulnerabilidade conhecida param o
   build. Roda dentro do Docker porque o Jenkins não tem Python.
2. **`Image Scan`**: o [Trivy](https://trivy.dev) varre a imagem final (pacotes Debian da imagem
   base + pacotes Python) e **barra a publicação** se houver vulnerabilidade **HIGH ou CRITICAL
   com correção disponível** (`--ignore-unfixed --exit-code 1`).
3. Endurecimento: versões fixas, `docker build --pull` (imagem base sempre atualizada), imagem
   final sem root (`USER 10001`) e `runAsNonRoot: true` no Kubernetes.

```groovy title="Jenkinsfile (trecho)"
stage('Image Scan') {
    steps {
        sh "docker build -t ${env.SERVICE}:scan ."
        sh """
            docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
                -v trivy-cache:/root/.cache/ ${env.TRIVY} image --scanners vuln \
                --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 ${env.SERVICE}:scan
        """
    }
}
```

**Como testar.** Rodei o `pip-audit` (18/11/2026) em dois conjuntos de dependências:

| Dependências | Resultado do `pip-audit` | Pipeline |
|---|---|---|
| antigas: `fastapi==0.109.0`, `uvicorn==0.27.0`, `httpx==0.26.0` | **15 vulnerabilidades em 2 pacotes** (14 no `starlette`, 1 no `fastapi`) | para no `Test & Audit` |
| atuais: `fastapi==0.165.0`, `uvicorn==0.54.0`, `httpx==0.28.1` | **nenhuma vulnerabilidade conhecida** | segue |

**Por que barrar só HIGH/CRITICAL com correção.** Barrar tudo pararia o pipeline por falhas sem
correção disponível na imagem base, sobre as quais o grupo não tem o que fazer. O que tem
correção vira ação concreta: subir a versão ou rebuildar com `--pull`.

## Enzo Perego (Order)

### 1. Cache com Redis

**Problema.** O `POST /orders` chama o Product uma vez **por item**, e o
`GET /orders/{id}?currency=` chama o Exchange, que consulta uma API externa.

**Solução.** `@Cacheable` do Spring com um Redis próprio (`order-redis`): produtos e cotações
por 60 s. Só respostas válidas entram no cache, e se o Redis cair o Order segue funcionando sem
cache (`CacheErrorHandler`).

| Requisição | Sem cache (p50) | Com cache (p50) | Chamadas externas |
|---|---|---|---|
| `GET /orders/{id}?currency=BRL` | 335 ms | **10 ms** | Exchange: 30 → **1** |
| `POST /orders` (2 itens) | 19 ms | **11 ms** | Product: 60 → **2** |

### 2. Observabilidade (Prometheus + Grafana)

**Problema.** Sem métricas, não dava para saber onde o Order gastava tempo nem se o cache
acertava.

**Solução.** Actuator + Micrometer numa porta de management separada (8081, inacessível pelo
gateway), Prometheus coletando a cada 5 s e painel **Store / Order** provisionado no Grafana
(profile `observability` do compose).

| Medida (90 s de tráfego, ~5.500 requisições) | Valor |
|---|---|
| Acerto do cache | `products` 96,1%, `rates` 83,8% |
| `GET /orders/{id}` | p50 2,4 ms, p95 284 ms |
| Conexões ativas no pool do banco | no máximo 2 de 10 |

O painel mostrou que o p95 alto vinha de moedas **inválidas**, que não entram no cache.

## Pedro (Gateway, Auth, Account, Product)

### 1. Gateway saturando CPU → HPA

Com 800 usuários, o gateway bateu no limite de CPU (500m) e as requisições fizeram fila. Com o
**HPA** (1 → 4 réplicas em ~40 s), o p95 caiu de 770 para **320 ms (−58%)** e o p99 de 1.400 para
910 ms (−35%), sem erros. Detalhes em [Teste de carga](load-test.md).

### 2. Deploy derrubando a API → readinessProbe

Sem probe, o Kubernetes mandava tráfego para o pod novo antes do Spring terminar de subir: ~40 s
de HTTP 503 a cada deploy. Com `readinessProbe`, o rollout passou a perder no máximo 1 requisição.
Detalhes em [CI/CD](cicd.md#deploy-sem-derrubar-a-api-readinessprobe).
