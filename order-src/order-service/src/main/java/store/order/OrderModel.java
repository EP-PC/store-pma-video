package store.order;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

import jakarta.persistence.CascadeType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.OneToMany;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.NoArgsConstructor;
import lombok.Setter;
import lombok.experimental.Accessors;

/**
 * Raiz do agregado Order: os itens so existem dentro de um pedido.
 * Por isso nao ha OrderItemRepository: o cascade salva os itens junto com o pedido.
 */
@Entity
@Table(name = "orders")
@Setter
@Accessors(chain = true, fluent = true)
@NoArgsConstructor
@AllArgsConstructor
public class OrderModel {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "id")
    private String id;

    @Column(name = "id_account")
    private String idAccount;

    @Column(name = "date")
    private LocalDateTime date;

    @Column(name = "total")
    private BigDecimal total;

    // mappedBy: quem tem a FK (id_order) e o OrderItemModel
    @OneToMany(mappedBy = "order", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<OrderItemModel> items = new ArrayList<>();

    public OrderModel(Order o) {
        this.id = o.id();
        this.idAccount = o.idAccount();
        this.date = o.date();
        this.total = o.total();
        if (o.items() != null) {
            o.items().forEach(i -> this.items.add(new OrderItemModel(i, this)));
        }
    }

    // com itens: GET /orders/{id} e resposta do POST
    public Order to() {
        return Order.builder()
            .id(this.id)
            .idAccount(this.idAccount)
            .date(this.date)
            .total(this.total)
            .items(this.items.stream().map(OrderItemModel::to).toList())
            .build();
    }

    // sem itens: o GET /orders nao precisa deles (e nao dispara uma consulta de itens por pedido)
    public Order toSummary() {
        return Order.builder()
            .id(this.id)
            .idAccount(this.idAccount)
            .date(this.date)
            .total(this.total)
            .build();
    }

}
