#!/usr/bin/env bash
# Cena: a loja inteira funcionando pelo gateway (cadastro, login, papéis, pedido, conversão).
source "$(dirname "$0")/lib.sh"
H=:8080
export HTTPIE_CONFIG_DIR=/tmp/httpie

title "store-pma · a loja rodando de ponta a ponta"

note "9 containers; só o gateway publica porta (8080)"
run "docker compose ps --format 'table {{.Service}}\t{{.Image}}\t{{.Status}}' | grep -v -E 'prometheus|grafana'" 3

note "sem login, o gateway barra antes de chegar no serviço"
run "http --print=h $H/exchange/USD/BRL" 2.5

note "cadastro e login: o JWT volta num cookie HttpOnly"
run "http --print=b POST $H/auth/register name=Ana email=ana@store.dev password=senha-da-ana" 2
run "http --session=ana --print=h POST $H/auth/login email=ana@store.dev password=senha-da-ana" 3

note "papéis: USER não cadastra produto, ADMIN cadastra"
run "http --session=ana --print=h POST $H/products name=Teclado price:=49.90 unit=un" 2
quiet "http --session=admin POST $H/auth/login email=\$ADMIN_EMAIL password=\$ADMIN_PASS"
run "http --session=admin --print=b POST $H/products name=Teclado price:=49.90 unit=un" 1.2
run "http --session=admin --print=b POST $H/products name=Mouse price:=19.90 unit=un" 2
P1=$(http --session=admin --print=b $H/products | jq -r '.[] | select(.name=="Teclado") | .id' | head -1)
P2=$(http --session=admin --print=b $H/products | jq -r '.[] | select(.name=="Mouse") | .id' | head -1)

note "pedido da Ana: o order consulta o product para validar e pegar o preço"
run "http --session=ana --print=b POST $H/orders items[0][idProduct]=\$P1 items[0][quantity]:=2 items[1][idProduct]=\$P2 items[1][quantity]:=1" 2.5
ID=$(http --session=ana --print=b $H/orders | jq -r '.[0].id')

note "o mesmo pedido em reais: o order chama o exchange, que consulta o Banco Central"
run "http --session=ana --print=b \"$H/orders/\$ID?currency=BRL\"" 3.5

note "a cotação direto no exchange: o id-account é o da Ana, posto pelo gateway"
run "http --session=ana --print=hb $H/exchange/USD/BRL" 3.5

note "moeda que não existe: 422"
run "http --session=ana --pretty=all --print=h \"$H/orders/\$ID?currency=XYZ\" | head -1" 3
