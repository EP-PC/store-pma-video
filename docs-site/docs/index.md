# store-pma · documentação individual

???+ info inline end "Edição"

    Platforms, Microservices, DevOps and APIs
    Insper · 2026.2

## Aluno e grupo

**Pedro Garcia** ([garciapp2](https://github.com/garciapp2)), responsável pelo **Exchange**, pelos
bottlenecks dele, pela análise de custos, PaaS e SLA, por esta documentação e pelo vídeo.

**Grupo 05** (organização [EP-PC](https://github.com/EP-PC) no GitHub, conta AWS `pmapi-bcc-grupo05`):

| Integrante | GitHub | O que fez no projeto |
|---|---|---|
| Pedro | [pedrohmm1](https://github.com/pedrohmm1) | Gateway, Auth, Account e Product; compose, Minikube, EKS na AWS (`up.ps1`/`down.ps1`), Jenkins e CI/CD, teste de carga com HPA |
| Enzo Perego | [EnzoPerego](https://github.com/EnzoPerego) | Order (contrato + service), Redis do Order, Prometheus e Grafana |
| Pedro Garcia | [garciapp2](https://github.com/garciapp2) | Exchange (Python, PTAX do BCB), cache e varredura de vulnerabilidades, custos/PaaS/SLA, documentação e vídeo |

## Entregas do projeto

Tabela de notas da [página do projeto](https://insper.github.io/platform/2026.2/exercises/project/):

| Item | Peso | Status | Onde |
|---|---|---|---|
| Gateway | 5% | :material-check: | [Serviços](projeto/servicos.md#gateway) |
| Auth | 5% | :material-check: | [Serviços](projeto/servicos.md#auth) |
| Account | 5% | :material-check: | [Serviços](projeto/servicos.md#account) |
| Exchange | 5% | :material-check: | [Exchange](projeto/exchange.md) |
| Bottlenecks (≥ 2 por integrante) | 20% | :material-check: | [Bottlenecks](projeto/bottlenecks.md) |
| AWS | 5% | :material-check: | [Arquitetura](projeto/arquitetura.md#na-aws) |
| EKS | 10% | :material-check: | [Como rodar](projeto/como-rodar.md#aws-eks) |
| Jenkins (CI/CD) | 10% | :material-check: | [CI/CD](projeto/cicd.md) |
| Load Testing | 15% | :material-check: | [Teste de carga](projeto/load-test.md) |
| PaaS, Custos e SLA | 10% | :material-check: | [Custos](projeto/custos.md) |
| MkDocs | 10% | :material-check: | esta documentação |

Além da tabela: **Product** e **Order** (serviços extras do projeto), **vídeo de apresentação**
([Apresentação](apresentacao.md)) e **declaração de uso de IA** ([Uso de IA](ia.md)).

## Repositórios

| Repositório | O que tem |
|---|---|
| [EP-PC/store-pma](https://github.com/EP-PC/store-pma) | root: submódulos, compose, scripts da AWS, Jenkins, teste de carga |
| [EP-PC/Gateway](https://github.com/EP-PC/Gateway) | gateway (Spring Cloud Gateway) |
| [EP-PC/Auth-service](https://github.com/EP-PC/Auth-service) | autenticação (JWT) |
| [EP-PC/Account](https://github.com/EP-PC/Account) · [EP-PC/Account-service](https://github.com/EP-PC/Account-service) | contrato e implementação do Account |
| [EP-PC/Product](https://github.com/EP-PC/Product) · [EP-PC/Product-service](https://github.com/EP-PC/Product-service) | contrato e implementação do Product |
| [EP-PC/Order](https://github.com/EP-PC/Order) · [EP-PC/Order-service](https://github.com/EP-PC/Order-service) | contrato e implementação do Order |
| [EP-PC/Exchange-service](https://github.com/EP-PC/Exchange-service) | Exchange (Python) |
| [garciapp2/store-pma-docs](https://github.com/garciapp2/store-pma-docs) | esta documentação |

!!! note "Repositórios privados"

    Parte dos repositórios da organização é privada (store-pma, Gateway, Order, Order-service,
    Exchange-service). O código de cada serviço também está descrito nas páginas desta
    documentação.
