# Roteiro do vídeo (rascunho: os tempos são acertados depois da montagem)

Ritmo de leitura: ~2,5 palavras por segundo. Fale em tom de conversa; pode encurtar.

## Abertura
Esse é o store-pma, uma loja de produtos feita de microsserviços, do grupo 05: eu, o Pedro e o Enzo.

## Arquitetura
Tudo entra por um gateway, que é o único serviço exposto. Ele valida o login no auth e repassa quem é
o usuário para os outros serviços. Account, product e order são em Java com Spring, cada um com o seu
schema no Postgres; o order tem um Redis de cache; e o exchange, em Python, busca a cotação no Banco
Central. Na AWS isso roda num EKS com dois nós, com o banco no RDS e um load balancer na frente, tudo
criado por CloudFormation. E a cada push na main, o Jenkins builda, publica a imagem no Docker Hub e
faz o deploy no cluster.

## Demo: a loja
Aqui é a loja rodando de verdade. Sem login, o gateway barra. A Ana se cadastra e faz login, e o token
volta num cookie. Ela tenta cadastrar produto e leva 403, porque só o admin pode. O admin cadastra, a
Ana faz o pedido, e o mesmo pedido aparece em reais: o order chamou o exchange, que consultou o Banco
Central. Moeda inválida dá 422.

## Kubernetes
Os mesmos manifestos do EKS, aplicados num cluster de teste: os pods só recebem tráfego quando o
health-check responde.

## HPA
Com carga, a CPU do gateway passa de 50% e o HPA cria réplicas sozinho.

## Bottlenecks
Cada um resolveu dois gargalos. O Pedro colocou HPA no gateway, que derrubou o p95 de 770 para 320
milissegundos, e readiness probe, que acabou com os 40 segundos de erro a cada deploy. O Enzo colocou
Redis no order e Prometheus com Grafana. E eu fiz o cache do exchange e a varredura de vulnerabilidades.

## Grafana
Esse é o painel do order com tráfego: requisições, latência e o acerto do cache.

## Exchange: cache
Sem cache, cada cotação levava 234 milissegundos e uma chamada ao Banco Central. Com cache, caiu para
3,7 milissegundos, e cem requisições viraram duas chamadas.

## Exchange: segurança
No pipeline, o pip-audit acha 15 vulnerabilidades nas versões antigas e zero nas atuais, e o Trivy
barra a imagem se tiver falha grave com correção.

## Custos
Na AWS isso custa uns 34 centavos de dólar por hora, então a gente sobe e derruba com um script. O
ponto fraco de disponibilidade é o banco numa zona só.

## Documentação e fecho
Está tudo documentado no MkDocs. A loja funciona de ponta a ponta, e os próximos passos seriam banco
Multi-AZ, réplicas e autoscaling do cluster.
