package store.order;

import java.math.BigDecimal;
import java.time.LocalDateTime;

import lombok.Builder;

// cada linha do GET /orders: so id, date e total (sem itens)
@Builder
public record OrderSummaryOut(
    String id,
    LocalDateTime date,
    BigDecimal total
) {}
