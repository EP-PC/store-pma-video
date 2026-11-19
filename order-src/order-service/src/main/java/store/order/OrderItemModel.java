package store.order;

import java.math.BigDecimal;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.NoArgsConstructor;
import lombok.Setter;
import lombok.experimental.Accessors;

// parte do agregado Order: e salvo/lido sempre atraves do OrderModel
@Entity
@Table(name = "order_items")
@Setter
@Accessors(chain = true, fluent = true)
@NoArgsConstructor
@AllArgsConstructor
public class OrderItemModel {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "id")
    private String id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "id_order")
    private OrderModel order;

    @Column(name = "id_product")
    private String idProduct;

    @Column(name = "quantity")
    private Integer quantity;

    @Column(name = "unit_price")
    private BigDecimal unitPrice;

    public OrderItemModel(OrderItem i, OrderModel order) {
        this.id = i.id();
        this.order = order;
        this.idProduct = i.idProduct();
        this.quantity = i.quantity();
        this.unitPrice = i.unitPrice();
    }

    public OrderItem to() {
        return OrderItem.builder()
            .id(this.id)
            .idProduct(this.idProduct)
            .quantity(this.quantity)
            .unitPrice(this.unitPrice)
            // o total do item nao e gravado: sai do preco congelado x quantidade
            .total(this.unitPrice.multiply(BigDecimal.valueOf(this.quantity)))
            .build();
    }

}
