package store.order;

import java.math.BigDecimal;

import lombok.Builder;

// total = quantity x preco unitario do produto no momento do pedido
@Builder
public record OrderItemOut(
    String id,
    ProductRefOut product,
    Integer quantity,
    BigDecimal total
) {}
