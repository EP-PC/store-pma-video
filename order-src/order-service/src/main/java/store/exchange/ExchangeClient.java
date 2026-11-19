package store.exchange;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestHeader;

/**
 * Cliente Feign do Exchange (servico em Python, sem jar de contrato: a interface fica aqui).
 *
 * Contrato combinado (ver o .md de decisoes para o Exchange):
 *  - GET /exchange/{from}/{to}  (singular: e o que o gateway roteia, /exchange/**)
 *  - resposta {"sell": numero, "buy": numero, "date": "YYYY-MM-DD HH:MM:SS", "id-account": "..."}
 *  - exige o header id-account (sem ele, 401): o Order repassa o do usuario atual
 *  - moeda nao suportada: 4xx (400/404/422), que o Order traduz para 422
 *
 * O Order chama direto http://exchange:8080 (rede interna), sem passar pelo gateway.
 */
@FeignClient(name = "exchange", url = "http://exchange:8080")
public interface ExchangeClient {

    @GetMapping("/exchange/{from}/{to}")
    ResponseEntity<ExchangeOut> rate(
        @PathVariable("from") String from,
        @PathVariable("to") String to,
        @RequestHeader("id-account") String idAccount
    );

}
