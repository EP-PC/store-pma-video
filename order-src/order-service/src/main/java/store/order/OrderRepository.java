package store.order;

import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.repository.CrudRepository;

public interface OrderRepository extends CrudRepository<OrderModel, String> {

    // GET /orders: so os pedidos do usuario atual, mais recentes primeiro
    List<OrderModel> findByIdAccountOrderByDateDesc(String idAccount);

    // GET /orders/{id}: filtrar tambem pelo dono faz o pedido de outro usuario "nao existir" (404),
    // sem revelar que o id e valido. O EntityGraph traz os itens na mesma consulta (join),
    // entao nao depende de sessao aberta para carregar os itens depois.
    @EntityGraph(attributePaths = "items")
    Optional<OrderModel> findByIdAndIdAccount(String id, String idAccount);

}
