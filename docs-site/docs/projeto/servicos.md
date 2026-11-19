# Serviços e endpoints

Todos os endpoints abaixo são chamados **pelo gateway** (`http://<host>:8080`). Exceto as rotas
abertas, todos exigem o cookie `__store_jwt_token` do login.

## Autenticação

1. `POST /auth/register` cria a conta (papel `USER`).
2. `POST /auth/login` devolve o cookie `__store_jwt_token` (JWT HMAC, `HttpOnly`, 1 h).
3. Em toda rota protegida, o gateway chama `POST /auth/solve` com o token e, se for válido,
   repassa `id-account` (UUID da conta) e `id-role` (`USER`/`ADMIN`) ao serviço.
4. Sem cookie, ou com cookie inválido, o gateway responde **401** sem chamar o serviço.

**Rotas abertas** (sem login), em `RouterValidator.java` do gateway: `POST /auth/register`,
`POST /auth/login`, `GET /auth/logout`, os health-checks e `GET /products/**` (vitrine pública).

O primeiro **ADMIN** é criado pelo seed do Account, a partir de `ACCOUNT_ADMIN_EMAIL` e
`ACCOUNT_ADMIN_HASH` (SHA-256 da senha em Base64), que vêm do `.env`/Secret.

## Gateway

Spring Cloud Gateway. Roteia `/auth/**`, `/accounts/**`, `/products/**`, `/orders/**` e
`/exchange/**` para `http://<serviço>:8080` e aplica o filtro de autenticação. É o único Service
`LoadBalancer`; os demais são `ClusterIP`.

## Auth

| Endpoint | Entrada | Resposta |
|---|---|---|
| `POST /auth/register` | `{name, email, password}` | 201 `{id, name, email, role}`; 400/409 |
| `POST /auth/login` | `{email, password}` | 200 + cookie; 401 |
| `GET /auth/logout` | — | 200 + cookie expirado |
| `GET /auth/me` | header `id-account` | 200 `{id, name, email, role}`; 401 |
| `POST /auth/solve` | `{token}` | 200 `{idAccount, role}`; 401 (uso interno do gateway) |
| `GET /auth/health-check` | — | 200 |

## Account

| Endpoint | Pelo gateway (`id-account`) | Interno (Auth, sem `id-account`) |
|---|---|---|
| `POST /accounts`, `POST /accounts/login` | 403 | permitido |
| `GET /accounts` | só `ADMIN` | permitido |
| `GET /accounts/{id}`, `DELETE /accounts/{id}` | dono ou `ADMIN` | permitido |
| `GET /accounts/health-check` | permitido | permitido |

A senha é guardada como hash; o Account nunca devolve o hash.

## Product

| Endpoint | Resposta | Quem pode |
|---|---|---|
| `GET /products`, `GET /products/{id}` | 200 (404 se não existe) | todos, sem login |
| `POST /products` | 201 + `Location` | só `ADMIN` (403 para `USER`) |
| `DELETE /products/{id}` | 204 | só `ADMIN` |
| `GET /products/health-check` | 200 | todos |

Contrato publicado como jar (`store:product:1.0.0`, repo `EP-PC/Product`) com o
`@FeignClient` que o Order usa.

## Order

| Endpoint | Resposta | Erros |
|---|---|---|
| `POST /orders` `{items: [{idProduct, quantity}]}` | 201 | 400 (produto inexistente), 401, 503 |
| `GET /orders` | 200, pedidos do usuário `{id, date, total}` | 401 |
| `GET /orders/{id}` | 200, valores em USD | 404 (não existe ou é de outro usuário) |
| `GET /orders/{id}?currency=XXX` | 200, valores convertidos pelo Exchange | 422 (moeda não suportada), 503 |
| `GET /orders/health-check` | 200 | — |

O preço vem do Product no momento do pedido e fica gravado em USD. Na conversão, cada item é
multiplicado pelo `sell` do Exchange (2 casas, `HALF_UP`) e o total é a soma dos itens
convertidos.

## Exchange

| Endpoint | Resposta |
|---|---|
| `GET /exchange/{from}/{to}` | 200 `{sell, buy, date, id-account}`; 401, 404, 503 |
| `GET /exchange/currencies` | moedas suportadas |
| `GET /exchange/health-check` | 200, sem login |

Detalhes na página [Exchange](exchange.md).
