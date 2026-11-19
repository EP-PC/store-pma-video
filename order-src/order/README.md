# Order

Contrato do microserviço **Order** da store (`store:order:1.0.0`). A implementação está em
[EP-PC/Order-service](https://github.com/EP-PC/Order-service).

O contrato é um jar sem lógica: a interface `OrderController` define as rotas HTTP
(`@FeignClient` + anotações do Spring MVC) e os records definem o JSON. O order-service
implementa a interface (`OrderResource implements OrderController`); outro serviço que queira
chamar o Order pode usar a mesma interface como cliente Feign. Assim servidor e cliente compilam
contra o mesmo jar e não divergem em path ou campos.

## Conteúdo (`store.order`)

| Tipo | Uso |
|---|---|
| `OrderController` | `POST /orders`, `GET /orders`, `GET /orders/{id}?currency=`, `GET /orders/health-check`; o header `id-account` (injetado pelo gateway) faz parte das assinaturas |
| `OrderIn`, `OrderItemIn` | body do `POST /orders`: `{"items": [{"idProduct", "quantity"}]}` |
| `OrderOut`, `OrderItemOut`, `ProductRefOut` | resposta do `POST` e do `GET /orders/{id}`: `{id, date, currency, items: [{id, product: {id}, quantity, total}], total}` |
| `OrderSummaryOut` | cada linha do `GET /orders`: `{id, date, total}` |

O `id-account` é declarado com `required = false` de propósito: com `true`, o Spring
responderia 400 quando ele faltasse; assim o order-service decide e responde 401.

## Instalação

Java 25 e Maven 3.9+:

```bash
mvn clean install   # instala store:order:1.0.0 no ~/.m2
```

No Jenkins, o job `order` faz o mesmo (`Jenkinsfile`), e o pipeline do order-service o dispara
antes de compilar.

## Uso

```xml
<dependency>
    <groupId>store</groupId>
    <artifactId>order</artifactId>
    <version>1.0.0</version>
</dependency>
```

Para consumir como cliente Feign: `@EnableFeignClients(basePackages = "store.order")` e
`@Autowired OrderController`. O próprio order-service **não** escaneia `store.order` com
`@EnableFeignClients`: ele implementa a interface, e um cliente Feign da mesma interface
entraria em conflito com o `OrderResource`.
