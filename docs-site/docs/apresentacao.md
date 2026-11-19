# Apresentação

A [página de apresentação](https://insper.github.io/platform/2026.2/exercises/project/presentation/)
pede um vídeo de **1 a 2 minutos** com: introdução, arquitetura, demonstração, desafios
(bottlenecks) e conclusão.

## Vídeo

!!! warning "Vídeo"

    Depois de gravar e subir no YouTube como **não listado**, troque `VIDEO_ID` abaixo pelo id do
    vídeo e apague este aviso.

<!--
<iframe width="100%" height="470" src="https://www.youtube.com/embed/VIDEO_ID" allowfullscreen></iframe>
-->

## Roteiro (1 min 50 s)

| Tempo | Parte | O que aparece | Fala (resumo) |
|---|---|---|---|
| 0:00–0:15 | Introdução | slide de título | store-pma: loja de produtos em microsserviços, grupo 05, 3 integrantes |
| 0:15–0:40 | Arquitetura | slide do diagrama | gateway único na frente; auth, account, product, order em Java; exchange em Python; PostgreSQL no RDS; EKS na AWS; Jenkins faz build, push e deploy |
| 0:40–1:10 | Demo | terminal/Postman | login → `GET /exchange/USD/BRL` (cotação do PTAX) → `POST /orders` → `GET /orders/{id}?currency=BRL` (pedido em reais) → `?currency=XYZ` dá 422 |
| 1:10–1:40 | Bottlenecks | slide com a tabela | HPA do gateway (p95 −58%), readinessProbe, Redis + Prometheus/Grafana no Order, cache do Exchange (p50 234 → 3,7 ms, 101 → 2 chamadas ao PTAX) e varredura de vulnerabilidades no pipeline |
| 1:40–1:50 | Conclusão | slide final | funcionando de ponta a ponta; próximos passos: RDS Multi-AZ, réplicas, Cluster Autoscaler |

## Teste de carga

O vídeo do teste de carga com HPA (exigido pela página de Load Testing) está em
[Teste de carga e HPA](projeto/load-test.md#video-do-teste-com-hpa).
