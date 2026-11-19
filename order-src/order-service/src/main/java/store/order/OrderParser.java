package store.order;

import java.util.List;

// conversoes entre o JSON do contrato (In/Out) e o dominio (Order/OrderItem)
public class OrderParser {

    public static Order to(OrderIn in) {
        return in == null ? null :
            Order.builder()
                .items(in.items() == null ? null : in.items().stream().map(OrderParser::to).toList())
                .build();
    }

    private static OrderItem to(OrderItemIn in) {
        return in == null ? null :
            OrderItem.builder()
                .idProduct(in.idProduct())
                .quantity(in.quantity())
                .build();
    }

    public static OrderOut to(Order o) {
        return o == null ? null :
            OrderOut.builder()
                .id(o.id())
                .date(o.date())
                .currency(o.currency())
                .items(o.items() == null ? null : o.items().stream().map(OrderParser::to).toList())
                .total(o.total())
                .build();
    }

    private static OrderItemOut to(OrderItem i) {
        return OrderItemOut.builder()
            .id(i.id())
            .product(ProductRefOut.builder().id(i.idProduct()).build())
            .quantity(i.quantity())
            .total(i.total())
            .build();
    }

    public static OrderSummaryOut toSummary(Order o) {
        return OrderSummaryOut.builder()
            .id(o.id())
            .date(o.date())
            .total(o.total())
            .build();
    }

    public static List<OrderSummaryOut> toSummary(List<Order> orders) {
        return orders.stream().map(OrderParser::toSummary).toList();
    }

}
