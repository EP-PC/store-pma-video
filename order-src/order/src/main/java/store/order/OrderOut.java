package store.order;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

import lombok.Builder;

// resposta do POST /orders e do GET /orders/{id}; currency diz em que moeda estao os totais
@Builder
public record OrderOut(
    String id,
    LocalDateTime date,
    String currency,
    List<OrderItemOut> items,
    BigDecimal total
) {}
