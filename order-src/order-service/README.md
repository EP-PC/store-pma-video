# Order-service

Implementação do microserviço **Order** da store (contrato em `store:order`, repo
[EP-PC/Order](https://github.com/EP-PC/Order)). Pedidos pertencem ao usuário logado, referenciam
produtos do **Product** e podem ser exibidos em outra moeda via **Exchange**.

## Rodando localmente

Pré-requisitos: Java 25, Maven 3.9+ e os dois contratos no `~/.m2`
(`mvn install` nos repos `Order` e `Product`, ou o `api/build.sh` do store-pma).

```bash
mvn clean package          # compila e roda os 42 testes
docker compose up --build  # Postgres + Redis + order na 8080
```

O `compose.yaml` deste repo sobe só o Postgres, o Redis do cache e o order (o Flyway cria o
schema `orders` na primeira subida). Sem o product de pé, o `POST /orders` com itens válidos responde 503.
Para o fluxo completo (gateway + auth + account + product + order), use o compose do
[store-pma](https://github.com/EP-PC/store-pma). Os dois usam `name: store` e a porta 8080:
deixe só um de pé por vez e derrube **sem** `-v`.

## API

Base `/orders`. IDs são UUID; valores em `BigDecimal`, guardados em **USD**.

| Endpoint | Sucesso | Erros |
|---|---|---|
| `POST /orders` | 201 + `Location` + body | 400 (itens inválidos ou produto inexistente), 401, 503 (Product fora) |
| `GET /orders` | 200 + lista `{id, date, total}` do usuário | 401 |
| `GET /orders/{id}` | 200, valores em USD | 401, 404 (não existe ou é de outro usuário) |
| `GET /orders/{id}?currency=XXX` | 200, valores convertidos | 401, 404, 422 (moeda não suportada), 503 (Exchange fora) |
| `GET /orders/health-check` | 200 | — |

Exemplo (`POST /orders`):

```json
{ "items": [ { "idProduct": "0195abfb-7074-73a9-9d26-b4b9fbaab0a8", "quantity": 2 } ] }
```

```json
{
  "id": "0195ac33-73e5-7cb3-90ca-7b5e7e549569",
  "date": "2025-09-01T12:30:00",
  "currency": "USD",
  "items": [
    { "id": "01961b9a-...", "product": { "id": "0195abfb-..." }, "quantity": 2, "total": 20.24 }
  ],
  "total": 20.24
}
```

Erros seguem o mesmo formato dos outros serviços:
`{timestamp, status, error, message, path}`.

## Identidade (headers do gateway)

O gateway valida o JWT e injeta `id-account` (dono do pedido) em toda rota protegida,
apagando o que o cliente tentar enviar. `/orders/**` não é rota aberta: sem login, o próprio
gateway já responde 401. Se a requisição chegar sem `id-account` (ex.: chamada direta, sem
gateway), o order também responde **401**.

- `GET /orders` lista só os pedidos do `id-account`.
- `GET /orders/{id}` de outro usuário responde **404** (o pedido "não existe" para ele; não
  revela que o id é válido).

## Product (validação e preço)

Para cada item, o order chama `GET http://product:8080/products/{id}` pelo cliente Feign do
contrato `store:product` (`ProductController`).

- Produto inexistente (404 no Product) → **400** no order (regra do enunciado).
- Product fora do ar, 5xx ou timeout → **503**.
- Todos os itens são validados (`items` não vazio, `idProduct` preenchido, `quantity > 0`)
  **antes** da primeira chamada ao Product.
- O preço atual do produto é **congelado** no item (`unit_price`): se o produto mudar de preço
  depois, o pedido antigo não muda. Total do item = `unit_price × quantity`; total do pedido =
  soma dos itens.

## Conversão de moeda (Exchange)

Sem `currency` (ou `currency=USD`), os valores voltam em USD sem chamar o Exchange. Com outra
moeda, o order chama `GET http://exchange:8080/exchange/USD/{moeda}` repassando o header
`id-account` e:

- usa a taxa **`sell`** (para pagar em outra moeda um valor em dólar, o cliente compra dólar);
- converte o total de **cada item** e arredonda em 2 casas (`HALF_UP`); o total do pedido é a
  **soma dos itens convertidos** (os itens exibidos sempre somam o total);
- normaliza a moeda (`" eur "` → `EUR`); formato que não é de 3 letras → **422** sem chamar
  o Exchange;
- Exchange responde 400/404/422 (moeda desconhecida) → **422**;
- Exchange fora do ar, 5xx, timeout ou `sell` inválido → **503**.

O contrato completo do Exchange (path, resposta, erros) está no
[`EXCHANGE.md`](https://github.com/EP-PC/store-pma/blob/main/EXCHANGE.md) do store-pma.

Os dois clientes Feign têm timeout de **2 s** para conectar e **5 s** para ler
(`application.yaml`): o padrão do Feign esperaria até 60 s, segurando a requisição do usuário.

## Bottleneck 1: cache com Redis

**Problema.** Toda requisição do Order depende de outro serviço pela rede: o `POST /orders` faz
uma chamada ao Product **por item** (preço e existência do produto), e o
`GET /orders/{id}?currency=` faz uma chamada ao Exchange, que por sua vez consulta uma API de
câmbio externa (centenas de milissegundos). Pedidos seguidos repetem as mesmas consultas.

**Solução.** Cache do Spring (`@Cacheable`) com um Redis próprio do order (`order-redis`):

| Cache | Chave | Valor | TTL |
|---|---|---|---|
| `products` | `order:products::<idProduct>` | produto (JSON) | 60 s |
| `rates` | `order:rates::USD-<moeda>` | taxa `sell` | 60 s |

- A cotação é a mesma para todos os usuários: a chave não inclui o `id-account`, então a
  consulta de um usuário aproveita a de outro.
- Só entra no cache resposta válida: produto inexistente (404), corpo vazio, taxa inválida e
  erros não são guardados (um produto criado depois aparece na consulta seguinte).
- Até 60 s de defasagem no preço/cotação é o custo aceito (TTL configurável em
  `store.order.cache.ttl`).
- **Redis fora do ar não derruba o order**: o `CacheErrorHandler` (`CacheConfig`) registra um
  aviso e a requisição segue sem cache, chamando o Product/Exchange direto.
- O `@Cacheable` fica em classes próprias (`ProductLookup`, `ExchangeLookup`) porque funciona
  via proxy do Spring: uma chamada de dentro do próprio `OrderService` não passaria pelo cache.

**Resultado medido** (compose local, 30 requisições seguidas de cada tipo; Exchange simulado com
300 ms de latência, como uma API externa; mesmo código com `SPRING_CACHE_TYPE=none` x Redis):

| Requisição | Sem cache (p50 / média) | Com cache (p50 / média) | Chamadas externas |
|---|---|---|---|
| `GET /orders/{id}?currency=BRL` | 335 ms / 357 ms | **10 ms / 67 ms** | Exchange: 30 → **1** |
| `POST /orders` (2 itens) | 19 ms / 33 ms | **11 ms / 18 ms** | Product: 60 → **2** |

No Redis: 87 hits e 3 misses (2 produtos + 1 cotação). A média com cache inclui a primeira
requisição (cache vazio + aquecimento da JVM). Com o Redis desligado, as mesmas requisições
continuaram respondendo 200/201 (sem cache, ~0,5 s a mais pelo timeout do Redis).

## Bottleneck 2: observabilidade (Prometheus + Grafana)

**Problema.** Sem métricas, não dá para saber onde o order gasta tempo, quantas chamadas faz ao
Product e ao Exchange, se o cache está acertando ou se o pool do banco está no limite. As
medições do bottleneck 1 precisaram de scripts feitos à mão.

**Solução.**

- **No order:** `spring-boot-starter-actuator` + `micrometer-registry-prometheus` +
  `feign-micrometer`. As métricas ficam em `GET :8081/actuator/prometheus`, numa **porta de
  management separada**: o gateway só encaminha `/orders/**` para a 8080, então elas nunca ficam
  acessíveis de fora (pela 8080, `/actuator/prometheus` responde 404). Histogramas de latência
  ligados para as rotas (`http.server.requests`) e para as chamadas Feign (`http.client.requests`),
  o que permite calcular p95/p99. Todas as métricas levam o rótulo `application="order"`.
- **No store-pma:** Prometheus (coleta a cada 5 s) e Grafana no profile `observability` do
  `api/compose.yaml` (só sobem quando pedidos), com a fonte de dados e o painel **Store / Order**
  provisionados por arquivo (`api/observability/`), sem configurar nada na tela.

| Painel | Métrica |
|---|---|
| Requisições/s, erros (4xx+5xx), latência p95 | `http_server_requests_seconds_*` por rota e status |
| Chamadas ao Product e ao Exchange e latência p95 | `http_client_requests_seconds_*` por `clientName` (Feign) |
| Acerto do cache (bottleneck 1) | `cache_gets_total` por cache e resultado (hit/miss) |
| Conexões ativas no pool do banco | `hikaricp_connections_active` |
| Heap da JVM | `jvm_memory_used_bytes{area="heap"}` |

```bash
cd store-pma/api
docker compose --profile observability up --build -d
# Grafana: http://localhost:3000 (painel Store / Order, sem login)
# Prometheus: http://localhost:9090
```

**Resultado** (90 s de tráfego misto contra o order, 4 clientes simultâneos, cerca de 5.500
requisições; Exchange simulado com 300 ms de latência; números lidos no Prometheus):

| Medida | Valor |
|---|---|
| `GET /orders` | p50 3,8 ms / p95 10,1 ms |
| `POST /orders` | p50 3,9 ms / p95 11,9 ms |
| `GET /orders/{id}` (com e sem `currency`) | p50 2,4 ms / **p95 284 ms** |
| Acerto do cache | `products` **96,1%**, `rates` 83,8% |
| Chamadas ao Product | 173 para cerca de 2.400 pedidos (o resto saiu do cache) |
| Conexões ativas no pool do banco | máximo 2 (de 10) |
| Heap da JVM | máximo 104 MB |

**O que o painel mostrou.** O p95 do `GET /orders/{id}` (284 ms) ficou muito acima do p50
(2,4 ms). O painel de chamadas Feign explica: quase todas as chamadas ao Exchange vieram de
pedidos com moeda **inválida** (`?currency=XYZ`), porque o cache, de propósito, não guarda erros;
cada uma paga a latência do Exchange. As conversões válidas (`BRL`) saem do cache. Próximo passo
possível: guardar também "moeda não suportada" no cache por alguns minutos. O pool do banco nunca
passou de 2 conexões ativas, o que confirma que o banco não é o gargalo nesse cenário.

## Banco

Schema `orders` (Flyway, `src/main/resources/db/migration`):

- `orders` (`id`, `id_account`, `date`, `total`) — índice em `id_account` (listagem por dono);
- `order_items` (`id`, `id_order`, `id_product`, `quantity`, `unit_price`) — FK para o pedido,
  índice em `id_order` e `CHECK (quantity > 0)`.

`OrderModel` é a **raiz do agregado**: os itens são salvos em cascata com o pedido, por isso não
existe `OrderItemRepository`. O detalhe carrega pedido + itens numa consulta só
(`@EntityGraph`), e a listagem não carrega itens. O `spring.jpa.open-in-view` está desligado:
a conexão volta ao pool logo após cada consulta, em vez de ficar presa durante a chamada ao
Exchange.

## Testes

```bash
mvn test
```

| Classe | Tipo | O que cobre |
|---|---|---|
| `OrderServiceTest` (20) | unitário (Mockito, sem Spring) | criação, validações, produto inexistente, Product/Exchange fora, 401, listagem por dono, 404 de outro usuário, conversão (taxa `sell`, arredondamento, normalização, 4xx → 422, taxa inválida) |
| `OrderResourceTest` (13) | integração HTTP (`@WebMvcTest` + MockMvc, `OrderService` real) | rotas, header `id-account`, status, `Location`, formato do JSON (igual ao enunciado), JSON malformado |
| `LookupCacheTest` (9) | contexto Spring com cache ligado (em memória) | bottleneck 1: mesma consulta = 1 chamada HTTP, cotação compartilhada entre usuários, 404/corpo vazio/taxa inválida/erros fora do cache, serialização JSON do Redis |

Banco, Redis, Product e Exchange são mocks ou substituídos em memória: os testes não precisam
de Postgres, Redis nem rede, e rodam no Jenkins.

## Kubernetes

Manifestos em `k8s/k8s.yaml`: Deployment + Service `ClusterIP` 8080 com o nome `order`, e o
Redis do cache (`order-redis`, `ClusterIP` 6379, `maxmemory` 96 MB com descarte LRU). O container
também abre a porta 8081 (métricas do Prometheus), que fica fora do Service. Pré-requisito:
o Postgres do repo root já aplicado (`postgres-configmap`, `postgres-secrets` e Service `postgres`).
O order não tem segredo próprio: usa só as credenciais do banco.

Imagem no Docker Hub: [`enzoperego/order`](https://hub.docker.com/r/enzoperego/order). A tag do
manifesto é o commit do código. A imagem é publicada para **linux/amd64 e linux/arm64**: um
`docker build` simples num Mac M1/M2 gera só arm64, que não roda nos nós amd64 do EKS.

```bash
mvn package
docker buildx create --use --name order-multi --driver docker-container
docker buildx build --platform linux/amd64,linux/arm64 --push \
  -t enzoperego/order:<commit> -t enzoperego/order:latest .
docker buildx rm order-multi
kubectl apply -f k8s/k8s.yaml
kubectl port-forward svc/order 8082:8080
curl -H 'id-account: 0195ae95-5be7-7dd3-b35d-7a7d87c404fb' http://localhost:8082/orders
```

`readinessProbe` `httpGet` em `/orders/health-check` (o site da disciplina pede que as probes
chamem o health-check do serviço; o pod só recebe tráfego quando o Spring terminou de subir),
requests/limits de 256Mi–512Mi e `JAVA_TOOL_OPTIONS=-XX:MaxRAMPercentage=50`, como no product.

## CI/CD (Jenkins)

Estágios do `Jenkinsfile`:

1. `Dependencies`: dispara os jobs `order` (contrato deste serviço) e `product` (contrato do Product).
2. `Build`: `mvn -B clean package` **com os testes** (diferente dos outros serviços, que usam
   `-DskipTests`): um teste falhando para o pipeline antes de publicar a imagem. O relatório
   aparece na página do build (plugin JUnit).
3. `Build & Push Image`: publica `enzoperego/order:latest` e `enzoperego/order:<BUILD_ID>`
   (linux/amd64 e linux/arm64) no Docker Hub.
4. `Deploy to EKS`: igual ao do product (`kubectl set image` + `rollout status` no cluster
   `eks-store`; pula sem falhar se o cluster estiver desligado).

Jobs necessários no Jenkins: `order` (repo `EP-PC/Order`), `product` (repo `EP-PC/Product`) e
`order-service` (este repo), todos Pipeline from SCM, branch `*/main`.
