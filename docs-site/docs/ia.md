# Declaração de uso de IA

A [página do projeto](https://insper.github.io/platform/2026.2/exercises/project/) permite o uso de
IA na implementação, limitado a tarefas específicas, e exige que ele seja declarado: o que foi
feito com IA e o que foi feito pelo integrante. Esta declaração cobre a minha parte (Pedro
Garcia). Os outros integrantes declaram o uso deles nas próprias documentações.

**Ferramenta:** Claude Code (Anthropic), como assistente no terminal.

## O que foi feito com ajuda de IA

| Parte | Uso da IA |
|---|---|
| Exchange: `main.py`, `ptax.py` | rascunho do código a partir do contrato do `EXCHANGE.md` e do enunciado |
| Testes (`tests/`) e `bench/bench.py` | rascunho dos testes e do script de medição |
| `Dockerfile`, `k8s/k8s.yaml`, `Jenkinsfile` | adaptação dos modelos do Order-service para Python |
| Medições dos bottlenecks | execução dos comandos de medição e organização dos números |
| Custos | leitura dos templates da AWS e consulta dos preços na Price List |
| Esta documentação | rascunho do texto das páginas a partir dos READMEs do grupo |

## O que foi feito por mim

- escolha do escopo (o que faltava no projeto) e das decisões: PTAX como API externa, os dois
  bottlenecks, repositório privado, onde publicar;
- revisão de todo o código, dos testes e do texto antes de cada commit;
- execução e conferência dos testes e das medições;
- gravação do vídeo de apresentação.

!!! warning "Revisar antes de entregar"

    Ajuste esta lista para refletir exatamente o que você fez e revisou. A disciplina exige que
    cada integrante saiba explicar e defender tudo o que entregou, inclusive a parte feita com IA.
