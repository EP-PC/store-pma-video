package store.order;

import java.util.List;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestParam;

/**
 * Contrato do Order (store:order): o order-service implementa esta interface
 * (OrderResource) e qualquer outro servico pode consumi-la via Feign.
 *
 * O id-account e o header que o Gateway injeta depois de validar o JWT (o dono do pedido).
 * Fica required = false de proposito: com true, o Spring responderia 400 quando faltasse;
 * assim o OrderService decide e responde 401 (usuario nao logado).
 */
@FeignClient(name = "order", url = "http://order:8080")
public interface OrderController {

    @PostMapping("/orders")
    ResponseEntity<OrderOut> create(
        @RequestHeader(value = "id-account", required = false) String idAccount,
        @RequestBody OrderIn in
    );

    @GetMapping("/orders")
    ResponseEntity<List<OrderSummaryOut>> findAll(
        @RequestHeader(value = "id-account", required = false) String idAccount
    );

    // currency opcional: sem ele, valores em USD (moeda em que o banco guarda)
    @GetMapping("/orders/{id}")
    ResponseEntity<OrderOut> findById(
        @RequestHeader(value = "id-account", required = false) String idAccount,
        @PathVariable("id") String id,
        @RequestParam(value = "currency", required = false) String currency
    );

    @GetMapping("/orders/health-check")
    ResponseEntity<Void> healthCheck();

}
