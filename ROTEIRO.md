# Roteiro para gravar a narração

**Como gravar:** leia os 9 blocos em ordem, como se estivesse explicando pra alguém, e deixe
**uns 2 segundos de silêncio entre um bloco e outro** (eu corto essas pausas na montagem; elas só
servem pra eu achar onde cada cena começa). Uma tomada só ou um arquivo por bloco. Salve em
`store-pma-video/audio/`. Fale no seu jeito: troque palavras à vontade, só mantenha os números.

~310 palavras, ~2 minutos.

---

**1 · Abertura** · tela: título e nomes
> Oi, eu sou o Pedro Garcia, e esse é o store-pma, a loja online que o grupo 05 montou inteira em microsserviços.

**2 · Como funciona** · tela: diagrama dos serviços, depois a AWS e o Jenkins
> Toda requisição entra pelo gateway, que é a única porta aberta pra fora. Ele confere o login no auth e repassa quem é o usuário. Atrás dele estão o account, o product e o order, em Java, e o exchange, que foi a minha parte, em Python. Na AWS tudo roda num EKS, com o banco no RDS, e o Jenkins faz o deploy sozinho a cada push.

**3 · A loja funcionando** · tela: terminal com as requisições
> Agora a loja rodando de verdade. Sem login, o gateway barra. A Ana cria a conta e entra, mas cadastrar produto ela não pode: dá 403, isso é coisa de admin. Aí ela faz um pedido, e quando pede o valor em reais, o order chama o exchange e converte na hora. Moeda inventada dá 422.

**4 · Kubernetes e teste de carga** · tela: pods subindo, depois o HPA
> No Kubernetes são os mesmos arquivos do EKS, e o pod só recebe tráfego quando o health-check responde. No teste de carga, a CPU do gateway estoura e o HPA sobe de uma pra quatro réplicas sozinho.

**5 · Os gargalos do grupo** · tela: tabela com os 6 bottlenecks
> Cada um atacou dois gargalos. O Pedro fez esse HPA, que derrubou a latência de 770 pra 320 milissegundos, e a readiness probe, que acabou com o erro no deploy. O Enzo colocou cache com Redis e monitoramento com Prometheus e Grafana.

**6 · Grafana** · tela: painel do order
> Esse é o painel dele, com tráfego de verdade passando.

**7 · Os meus gargalos** · tela: benchmark do cache, depois o Trivy
> Os meus foram no exchange. O cache guarda a cotação, então em vez de ir no Banco Central toda vez, a resposta caiu de uns 800 milissegundos pra 4. E no pipeline, o Trivy achou duas falhas graves na imagem; eu corrigi e agora ela passa.

**8 · Custos** · tela: custo por hora e SLA
> Ligado na AWS, isso custa uns 34 centavos de dólar por hora, então a gente sobe e derruba com um script. O ponto fraco é o banco numa zona só.

**9 · Fecho** · tela: site da documentação e conclusão
> Tá tudo documentado no MkDocs. A loja funciona de ponta a ponta, e o próximo passo seria deixar o banco e o cluster mais resistentes a falha. Valeu!
