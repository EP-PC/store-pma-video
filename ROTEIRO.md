# Roteiro para gravar a narração

**Como gravar:** leia os 9 blocos em ordem, no seu ritmo, e deixe **uns 2 segundos de silêncio
entre um bloco e outro** (é por essas pausas que eu corto e encaixo cada cena). Pode ser numa
tomada só ou um arquivo por bloco. Qualquer gravador serve (Gravador de Voz do Windows, celular).
Salve em `store-pma-video/audio/`. Total esperado: ~1 min 50 s (~270 palavras).

Pode trocar palavras para soar natural; só mantenha os números.

---

**1 · Abertura** (tela: título e nomes)
> Esse é o store-pma, uma loja de produtos feita de microsserviços. Grupo 05: eu, Pedro Garcia, o Pedro e o Enzo.

**2 · Arquitetura** (tela: diagrama dos serviços, depois a AWS e o CI/CD)
> Tudo entra por um gateway, o único serviço exposto: ele valida o login no auth e repassa quem é o usuário. Account, product e order são em Java; o exchange, que eu fiz, é em Python e busca a cotação no Banco Central. Na AWS isso roda num EKS com dois nós e o banco no RDS, e cada push passa pelo Jenkins até o deploy.

**3 · A loja funcionando** (tela: terminal com as requisições pelo gateway)
> Essa é a loja rodando de verdade. Sem login, o gateway barra. A Ana se cadastra e entra; tenta cadastrar um produto e leva 403, porque só o admin pode. Ela faz um pedido de 119 dólares, e o mesmo pedido sai em reais: o order chamou o exchange. Moeda que não existe dá 422.

**4 · Kubernetes e HPA** (tela: pods subindo; depois 3 painéis com o HPA)
> Os mesmos manifestos do EKS num cluster de teste: os pods sobem e só recebem tráfego quando o health-check responde. Com carga, a CPU do gateway passa de 160% do alvo e o HPA sobe de uma para quatro réplicas.

**5 · Bottlenecks do grupo** (tela: tabela com os 6 bottlenecks)
> Cada um resolveu dois gargalos. O Pedro colocou HPA, que cortou o p95 de 770 para 320 milissegundos, e readiness probe, que acabou com os 40 segundos de erro em cada deploy. O Enzo colocou Redis no order e Prometheus com Grafana.

**6 · Grafana** (tela: painel do order com tráfego)
> Aqui o painel dele com tráfego de verdade: requisições, latência e o acerto do cache.

**7 · Os meus bottlenecks** (tela: benchmark do cache; depois pip-audit e Trivy)
> Os meus foram no exchange. O cache levou a cotação de uns 800 milissegundos para 4, com duas chamadas ao Banco Central em vez de cem. E a varredura de vulnerabilidades: o Trivy barrou a imagem com duas falhas graves, eu corrigi no Dockerfile e ela passou.

**8 · Custos** (tela: custo por hora e SLA)
> Na AWS isso custa uns 34 centavos de dólar por hora, então a gente sobe e derruba com um script. O ponto fraco de disponibilidade é o banco numa zona só.

**9 · Fecho** (tela: conclusão e link da documentação)
> Está tudo documentado no MkDocs. A loja funciona de ponta a ponta, e os próximos passos são banco Multi-AZ, mais réplicas e autoscaling do cluster.
