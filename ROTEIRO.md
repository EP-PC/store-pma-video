# Roteiro para gravar a narração

**Como gravar:** leia os 9 blocos em ordem, no seu ritmo, com **uns 2 segundos de silêncio entre
um bloco e outro** (eu corto essas pausas na montagem; elas só marcam onde cada cena começa).
Uma tomada só ou um arquivo por bloco, salvo em `store-pma-video/audio/`. Pode trocar palavras;
mantenha os números, que são os que aparecem na tela. ~300 palavras, ~1 min 55 s.

---

**1 · Abertura** · tela: título e nomes
> Esse é o store-pma, do grupo 05: o Pedro, o Enzo e o Pedro Garcia. É uma loja online, com cadastro, produtos e pedidos, feita em microsserviços.

**2 · Arquitetura** · tela: diagrama dos serviços, depois a AWS e o CI/CD
> A entrada é um gateway, o único serviço exposto. Ele valida o login com o auth e repassa a identidade do usuário. Atrás dele estão o account, o product e o order, em Java com Spring, e o exchange, em Python, que busca a cotação no Banco Central. Na AWS, isso roda num EKS com dois nós e o banco no RDS, e o Jenkins builda e faz o deploy a cada push.

**3 · Demonstração** · tela: terminal com as requisições pelo gateway
> Aqui a loja rodando. Sem login, o gateway barra. Um usuário cria a conta e entra; se tenta cadastrar produto, recebe 403, porque só admin pode. Ele faz um pedido e pede o total em reais: o order consulta o exchange e converte na hora. Moeda que não existe volta 422.

**4 · Kubernetes e teste de carga** · tela: pods subindo, depois o HPA
> No Kubernetes, os pods só recebem tráfego quando o health-check responde. No teste de carga, a CPU do gateway passa do alvo e o HPA escala de uma para quatro réplicas.

**5 · Bottlenecks** · tela: tabela com os 6 bottlenecks e quem fez cada um
> Foram seis bottlenecks, dois por integrante. No gateway, o HPA baixou o p95 de 770 para 320 milissegundos, e a readiness probe acabou com os erros durante o deploy. No order, entrou cache com Redis e monitoramento com Prometheus e Grafana.

**6 · Grafana** · tela: painel do order
> Esse é o painel do order com tráfego real: requisições, latência e acerto do cache.

**7 · Exchange** · tela: benchmark do cache, depois o Trivy
> No exchange, um cache de cotações levou a resposta de uns 800 milissegundos para 4 e cortou as chamadas ao Banco Central. E a varredura de segurança no pipeline pegou duas falhas graves na imagem, que foram corrigidas antes de publicar.

**8 · Custos** · tela: custo por hora e SLA
> Na AWS, o ambiente custa cerca de 34 centavos de dólar por hora, por isso ele sobe e é derrubado por script. O ponto fraco de disponibilidade hoje é o banco numa zona só.

**9 · Conclusão** · tela: site da documentação e fecho
> A documentação completa está no MkDocs. A loja funciona de ponta a ponta, e os próximos passos são banco em várias zonas, mais réplicas e autoscaling do cluster.
