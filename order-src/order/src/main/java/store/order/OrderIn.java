package store.order;

import java.util.List;

import lombok.Builder;

// body do POST /orders: {"items": [{"idProduct": "...", "quantity": 2}]}
@Builder
public record OrderIn(
    List<OrderItemIn> items
) {}
