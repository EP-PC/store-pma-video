package store.order;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Locale;
import java.util.regex.Pattern;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import feign.FeignException;
import lombok.extern.slf4j.Slf4j;
import store.product.ProductOut;

@Slf4j
@Service
public class OrderService {

    // moeda em que o banco guarda os valores
    public static final String USD = "USD";

    // codigo de moeda ISO 4217: 3 letras (USD, BRL, EUR...)
    private static final Pattern CURRENCY_CODE = Pattern.compile("[A-Z]{3}");

    @Autowired
    private OrderRepository orderRepository;

    // consultas ao Product e ao Exchange com cache no Redis (bottleneck 1; ver CacheConfig)
    @Autowired
    private ProductLookup productLookup;

    @Autowired
    private ExchangeLookup exchangeLookup;

    // Sem @Transactional de proposito: as chamadas ao Product (HTTP) acontecem antes,
    // sem segurar conexao do banco; o save() abre a propria transacao e grava pedido + itens.
    public Order create(String idAccount, Order order) {
        requireAccount(idAccount);
        validate(order);   // tudo validado antes de chamar o Product

        List<OrderItem> items = order.items().stream()
            .map(this::price)
            .toList();

        BigDecimal total = items.stream()
            .map(OrderItem::total)
            .reduce(BigDecimal.ZERO, BigDecimal::add);

        Order toSave = Order.builder()
            .idAccount(idAccount)
            // sem fracao de segundo: sai como "2025-09-01T12:30:00", igual ao enunciado
            .date(LocalDateTime.now().truncatedTo(ChronoUnit.SECONDS))
            .items(items)
            .total(total)
            .build();

        return orderRepository.save(new OrderModel(toSave)).to().currency(USD);
    }

    public List<Order> findAll(String idAccount) {
        requireAccount(idAccount);
        return orderRepository.findByIdAccountOrderByDateDesc(idAccount).stream()
            .map(OrderModel::toSummary)
            .toList();
    }

    // pedido de outro usuario: 404 (o repositorio filtra pelo dono).
    // O 404 vem antes da moeda: pedido alheio com ?currency=XXX continua 404, sem chamar o Exchange.
    public Order findById(String idAccount, String id, String currency) {
        requireAccount(idAccount);
        Order order = orderRepository.findByIdAndIdAccount(id, idAccount)
            .map(OrderModel::to)
            .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Order not found"));
        return convert(order, currency, idAccount);
    }

    // Banco em USD. Sem currency (ou USD): devolve como esta, sem chamar o Exchange.
    // Outra moeda: busca a cotacao USD -> moeda e converte o total de CADA item
    // (arredondado em 2 casas); o total do pedido e a soma dos itens convertidos,
    // assim os itens exibidos sempre somam o total exibido.
    private Order convert(Order order, String currency, String idAccount) {
        String target = currency == null ? "" : currency.trim().toUpperCase(Locale.ROOT);
        if (target.isEmpty() || USD.equals(target)) {
            return order.currency(USD);
        }
        if (!CURRENCY_CODE.matcher(target).matches()) {
            // formato invalido (ex.: "REAL", "BR1"): nem chega a chamar o Exchange
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_CONTENT, "Currency not supported: " + currency);
        }

        BigDecimal rate = rate(target, idAccount);

        List<OrderItem> items = order.items().stream()
            .map(i -> OrderItem.builder()
                .id(i.id())
                .idProduct(i.idProduct())
                .quantity(i.quantity())
                .unitPrice(i.unitPrice())                        // continua em USD (nao sai no JSON)
                .total(i.total().multiply(rate).setScale(2, RoundingMode.HALF_UP))
                .build())
            .toList();

        BigDecimal total = items.stream()
            .map(OrderItem::total)
            .reduce(BigDecimal.ZERO, BigDecimal::add);

        return Order.builder()
            .id(order.id())
            .idAccount(order.idAccount())
            .date(order.date())
            .currency(target)
            .items(items)
            .total(total)
            .build();
    }

    // Cotacao USD -> moeda no Exchange. Usa "sell" (taxa de venda): para pagar um valor em
    // dolar com outra moeda, o cliente precisa COMPRAR dolar, e a casa de cambio VENDE.
    // O id-account e repassado porque o Exchange so atende usuario logado.
    private BigDecimal rate(String to, String idAccount) {
        BigDecimal sell;
        try {
            sell = exchangeLookup.sell(USD, to, idAccount);
        } catch (FeignException.BadRequest | FeignException.NotFound | FeignException.UnprocessableEntity e) {
            // o Exchange nao conhece a moeda
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_CONTENT, "Currency not supported: " + to);
        } catch (FeignException e) {
            throw translate(e, "Exchange");
        }
        // null = resposta invalida do Exchange (sem body, sell ausente ou <= 0)
        if (sell == null) {
            log.error("Invalid exchange rate for USD -> {}", to);
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "Invalid exchange rate");
        }
        return sell;
    }

    // id-account vem do Gateway (depois de validar o JWT); sem ele = usuario nao logado
    private void requireAccount(String idAccount) {
        if (idAccount == null || idAccount.isBlank()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Missing id-account");
        }
    }

    private void validate(Order order) {
        if (order == null || order.items() == null || order.items().isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Items are required");
        }
        for (OrderItem item : order.items()) {
            if (item == null) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Item is required");
            }
            if (item.idProduct() == null || item.idProduct().isBlank()) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "idProduct is required");
            }
            if (item.quantity() == null || item.quantity() <= 0) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Quantity must be greater than zero");
            }
        }
    }

    // busca o produto no Product e congela o preco atual no item
    private OrderItem price(OrderItem item) {
        ProductOut product = findProduct(item.idProduct());
        return OrderItem.builder()
            .idProduct(product.id())
            .quantity(item.quantity())
            .unitPrice(product.price())
            .total(product.price().multiply(BigDecimal.valueOf(item.quantity())))
            .build();
    }

    // produto inexistente -> 400 (regra do enunciado); Product fora do ar -> 503
    private ProductOut findProduct(String idProduct) {
        ProductOut product;
        try {
            product = productLookup.find(idProduct);
        } catch (FeignException.NotFound e) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Product not found: " + idProduct);
        } catch (FeignException e) {
            throw translate(e, "Product");
        }
        // corpo vazio (ex.: idProduct "health-check" casa GET /products/health-check, que responde 200 sem body)
        if (product == null || product.id() == null || product.price() == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Product not found: " + idProduct);
        }
        return product;
    }

    // mesmo criterio do AuthService: conexao recusada/timeout (status -1) ou 5xx -> 503.
    // Qualquer outro status inesperado (ex.: 401 do Exchange, que indicaria header nao repassado)
    // vira 500 no ExceptionHandler.
    private RuntimeException translate(FeignException e, String service) {
        if (e.status() < 0 || e.status() >= 500) {
            log.error("{} service unavailable: {}", service, e.getMessage());
            return new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, service + " service unavailable");
        }
        return e;
    }

}
