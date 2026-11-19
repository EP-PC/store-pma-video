package store.order;

import java.math.BigDecimal;

import lombok.Builder;
import lombok.Data;
import lombok.experimental.Accessors;

@Builder
@Data
@Accessors(fluent = true)
public class OrderItem {

    private String id;
    private String idProduct;
    private Integer quantity;
    // preco do produto no momento do pedido (USD)
    private BigDecimal unitPrice;
    // unitPrice x quantity
    private BigDecimal total;

}
