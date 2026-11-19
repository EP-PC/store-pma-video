# Atividades individuais

A página de apresentação pede, além do projeto, a documentação e o código das atividades feitas.
As atividades da seção *Exercises → Individual* do site (por exemplo,
[Exchange API](https://insper.github.io/platform/2026.2/exercises/exchange/)) e onde cada uma está:

| Atividade | Situação | Onde |
|---|---|---|
| Exchange API | feita por mim, dentro do projeto | [Exchange](projeto/exchange.md) · [EP-PC/Exchange-service](https://github.com/EP-PC/Exchange-service) |
| Bottlenecks | 2 feitos por mim, no Exchange | [Bottlenecks](projeto/bottlenecks.md#pedro-garcia-exchange) |
| Jenkins | pipeline do Exchange (testes, varredura, push, deploy) | [CI/CD](projeto/cicd.md) · `Jenkinsfile` do Exchange-service |
| Product API | feita no projeto por outro integrante (Pedro) | [Serviços](projeto/servicos.md#product) |
| Order API | feita no projeto por outro integrante (Enzo) | [Serviços](projeto/servicos.md#order) |
| MiniKube | manifestos `k8s/k8s.yaml` de cada serviço, inclusive o Exchange | [Como rodar](projeto/como-rodar.md#minikube) |

## O que eu fiz

- **Exchange**: serviço em FastAPI sobre o PTAX do Banco Central, no contrato combinado com o
  Order; 14 testes automatizados; Dockerfile em 3 estágios; manifesto Kubernetes; Jenkinsfile.
- **Integração** no store-pma: submódulo, compose, `up.ps1` e README.
- **Bottlenecks**: cache com fallback (medido: p50 −98%, chamadas ao PTAX −98%) e varredura de
  vulnerabilidades (pip-audit + Trivy) no pipeline.
- **Custos, PaaS e SLA**: levantamento dos recursos reais da AWS e preços conferidos na Price
  List da AWS.
- **Esta documentação** e o **vídeo** de apresentação.
