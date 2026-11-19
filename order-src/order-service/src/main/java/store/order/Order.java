package store.order;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

import lombok.Builder;
import lombok.Data;
import lombok.experimental.Accessors;

// objeto de dominio: e o que o OrderService manipula (nem JSON, nem entidade JPA)
@Builder
@Data
@Accessors(fluent = true)
public class Order {

    private String id;
    private String idAccount;
    private LocalDateTime date;
    // moeda dos totais na resposta; no banco e sempre USD
    private String currency;
    private List<OrderItem> items;
    private BigDecimal total;

}
