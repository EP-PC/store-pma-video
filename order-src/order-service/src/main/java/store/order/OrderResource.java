package store.order;

import java.net.URI;
import java.util.List;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;

// as rotas e os parametros (@RequestHeader, @PathVariable, @RequestParam, @RequestBody)
// vem das anotacoes do contrato OrderController; aqui so a camada HTTP
@RestController
public class OrderResource implements OrderController {

    @Autowired
    private OrderService orderService;

    @Override
    public ResponseEntity<OrderOut> create(String idAccount, OrderIn in) {
        Order created = orderService.create(idAccount, OrderParser.to(in));
        URI location = ServletUriComponentsBuilder.fromCurrentRequest()
            .path("/{id}")
            .buildAndExpand(created.id())
            .toUri();
        return ResponseEntity.created(location).body(OrderParser.to(created));
    }

    @Override
    public ResponseEntity<List<OrderSummaryOut>> findAll(String idAccount) {
        return ResponseEntity.ok(OrderParser.toSummary(orderService.findAll(idAccount)));
    }

    @Override
    public ResponseEntity<OrderOut> findById(String idAccount, String id, String currency) {
        return ResponseEntity.ok(OrderParser.to(orderService.findById(idAccount, id, currency)));
    }

    @Override
    public ResponseEntity<Void> healthCheck() {
        return ResponseEntity.ok().build();
    }

}
