package store.order;

import lombok.Builder;

// referencia ao produto no item: so o id, como no enunciado ("product": {"id": "..."})
@Builder
public record ProductRefOut(
    String id
) {}
