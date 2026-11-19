package store.order;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import org.assertj.core.api.ThrowableAssert.ThrowingCallable;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import feign.FeignException;
import feign.Request;
import feign.Response;
import store.product.ProductOut;

/**
 * Teste unitario do OrderService: sem Spring, sem banco, sem rede.
 * O repositorio e as consultas ao Product e ao Exchange (ProductLookup/ExchangeLookup) sao mocks.
 * O cache em si e testado no LookupCacheTest.
 */
@ExtendWith(MockitoExtension.class)
class OrderServiceTest {

    private static final String ACCOUNT = "0195ae95-5be7-7dd3-b35d-7a7d87c404fb";
    private static final String OTHER_ACCOUNT = "0195ae95-0000-7000-8000-000000000002";
    private static final String P1 = "0195abfb-7074-73a9-9d26-b4b9fbaab0a8";
    private static final String P2 = "0195abfe-e416-7052-be3b-27cdaf12a984";
    private static final String ORDER_ID = "0195ac33-73e5-7cb3-90ca-7b5e7e549569";

    @Mock
    private OrderRepository orderRepository;

    @Mock
    private ProductLookup productLookup;

    @Mock
    private ExchangeLookup exchangeLookup;

    @InjectMocks
    private OrderService orderService;

    // ---------- POST /orders ----------

    @Test
    void createComputesTotalsWithProductPricesAndSavesForCurrentAccount() {
        when(productLookup.find(P1)).thenReturn(product(P1, "10.12"));
        when(productLookup.find(P2)).thenReturn(product(P2, "0.62"));
        when(orderRepository.save(any(OrderModel.class))).thenAnswer(inv -> inv.getArgument(0));

        Order created = orderService.create(ACCOUNT, order(item(P1, 2), item(P2, 10)));

        assertThat(created.idAccount()).isEqualTo(ACCOUNT);
        assertThat(created.currency()).isEqualTo("USD");
        assertThat(created.date()).isNotNull();
        assertThat(created.date().getNano()).isZero();   // sem fracao: "2025-09-01T12:30:00"
        assertThat(created.items()).hasSize(2);
        // preco congelado no item e total = preco x quantidade
        assertThat(created.items().get(0).unitPrice()).isEqualByComparingTo("10.12");
        assertThat(created.items().get(0).total()).isEqualByComparingTo("20.24");
        assertThat(created.items().get(1).total()).isEqualByComparingTo("6.20");
        assertThat(created.total()).isEqualByComparingTo("26.44");
    }

    @Test
    void createWithUnknownProductReturns400AndDoesNotSave() {
        when(productLookup.find(P1)).thenThrow(feignError(404));

        assertStatus(() -> orderService.create(ACCOUNT, order(item(P1, 1))), HttpStatus.BAD_REQUEST);
        verify(orderRepository, never()).save(any());
    }

    @Test
    void createWithEmptyProductBodyReturns400() {
        // ex.: idProduct "health-check" casa GET /products/health-check (200 sem body)
        when(productLookup.find("health-check")).thenReturn(null);

        assertStatus(() -> orderService.create(ACCOUNT, order(item("health-check", 1))), HttpStatus.BAD_REQUEST);
        verify(orderRepository, never()).save(any());
    }

    @Test
    void createWithProductServiceDownReturns503() {
        when(productLookup.find(P1)).thenThrow(feignError(503));

        assertStatus(() -> orderService.create(ACCOUNT, order(item(P1, 1))), HttpStatus.SERVICE_UNAVAILABLE);
        verify(orderRepository, never()).save(any());
    }

    @Test
    void createWithoutItemsReturns400WithoutCallingProduct() {
        assertStatus(() -> orderService.create(ACCOUNT, Order.builder().items(List.of()).build()), HttpStatus.BAD_REQUEST);
        assertStatus(() -> orderService.create(ACCOUNT, Order.builder().build()), HttpStatus.BAD_REQUEST);
        assertStatus(() -> orderService.create(ACCOUNT, null), HttpStatus.BAD_REQUEST);
        verify(productLookup, never()).find(anyString());
    }

    @Test
    void createWithInvalidItemReturns400WithoutCallingProduct() {
        assertStatus(() -> orderService.create(ACCOUNT, order(item(P1, 0))), HttpStatus.BAD_REQUEST);
        assertStatus(() -> orderService.create(ACCOUNT, order(item(P1, -1))), HttpStatus.BAD_REQUEST);
        assertStatus(() -> orderService.create(ACCOUNT, order(item(P1, null))), HttpStatus.BAD_REQUEST);
        assertStatus(() -> orderService.create(ACCOUNT, order(item(" ", 1))), HttpStatus.BAD_REQUEST);
        // valida todos os itens antes da primeira chamada ao Product
        assertStatus(() -> orderService.create(ACCOUNT, order(item(P1, 1), item(P2, 0))), HttpStatus.BAD_REQUEST);
        verify(productLookup, never()).find(anyString());
    }

    @Test
    void createWithoutAccountReturns401() {
        assertStatus(() -> orderService.create(null, order(item(P1, 1))), HttpStatus.UNAUTHORIZED);
        assertStatus(() -> orderService.create(" ", order(item(P1, 1))), HttpStatus.UNAUTHORIZED);
        verify(productLookup, never()).find(anyString());
    }

    // ---------- GET /orders ----------

    @Test
    void findAllReturnsOnlyOrdersOfCurrentAccountWithoutItems() {
        when(orderRepository.findByIdAccountOrderByDateDesc(ACCOUNT)).thenReturn(List.of(storedOrder()));

        List<Order> orders = orderService.findAll(ACCOUNT);

        verify(orderRepository).findByIdAccountOrderByDateDesc(ACCOUNT);
        assertThat(orders).hasSize(1);
        assertThat(orders.get(0).id()).isEqualTo(ORDER_ID);
        assertThat(orders.get(0).total()).isEqualByComparingTo("26.44");
        assertThat(orders.get(0).items()).isNull();   // resumo: sem itens
    }

    @Test
    void findAllWithoutAccountReturns401() {
        assertStatus(() -> orderService.findAll(null), HttpStatus.UNAUTHORIZED);
        verify(orderRepository, never()).findByIdAccountOrderByDateDesc(any());
    }

    // ---------- GET /orders/{id} ----------

    @Test
    void findByIdOfOwnerReturnsOrderInUsdByDefault() {
        when(orderRepository.findByIdAndIdAccount(ORDER_ID, ACCOUNT)).thenReturn(Optional.of(storedOrder()));

        Order order = orderService.findById(ACCOUNT, ORDER_ID, null);

        assertThat(order.currency()).isEqualTo("USD");
        assertThat(order.items()).hasSize(2);
        assertThat(order.items().get(0).total()).isEqualByComparingTo("20.24");
        assertThat(order.total()).isEqualByComparingTo("26.44");
        verify(exchangeLookup, never()).sell(any(), any(), any());   // USD: sem chamada ao Exchange
    }

    @Test
    void findByIdOfAnotherAccountReturns404() {
        // o repositorio filtra por (id, dono): para outro usuario o pedido "nao existe"
        when(orderRepository.findByIdAndIdAccount(ORDER_ID, OTHER_ACCOUNT)).thenReturn(Optional.empty());

        assertStatus(() -> orderService.findById(OTHER_ACCOUNT, ORDER_ID, null), HttpStatus.NOT_FOUND);
        // com moeda tambem: o 404 vem antes, sem chamar o Exchange
        assertStatus(() -> orderService.findById(OTHER_ACCOUNT, ORDER_ID, "BRL"), HttpStatus.NOT_FOUND);
        verify(exchangeLookup, never()).sell(any(), any(), any());
    }

    @Test
    void findByIdWithoutAccountReturns401() {
        assertStatus(() -> orderService.findById(null, ORDER_ID, null), HttpStatus.UNAUTHORIZED);
        verify(orderRepository, never()).findByIdAndIdAccount(any(), any());
    }

    @Test
    void findByIdWithUsdCurrencyIsAccepted() {
        when(orderRepository.findByIdAndIdAccount(ORDER_ID, ACCOUNT)).thenReturn(Optional.of(storedOrder()));

        assertThat(orderService.findById(ACCOUNT, ORDER_ID, "usd").currency()).isEqualTo("USD");
        verify(exchangeLookup, never()).sell(any(), any(), any());
    }

    // ---------- GET /orders/{id}?currency= (Exchange) ----------

    @Test
    void findByIdWithCurrencyConvertsWithSellRateAndForwardsIdAccount() {
        when(orderRepository.findByIdAndIdAccount(ORDER_ID, ACCOUNT)).thenReturn(Optional.of(storedOrder()));
        // stub so para (USD, BRL, ACCOUNT): se o Order nao repassar o id-account, o teste falha
        when(exchangeLookup.sell("USD", "BRL", ACCOUNT)).thenReturn(new BigDecimal("6.00"));

        Order order = orderService.findById(ACCOUNT, ORDER_ID, "BRL");

        // mesmos numeros do exemplo do enunciado: 20.24 -> 121.44, 6.20 -> 37.20, total 158.64
        assertThat(order.currency()).isEqualTo("BRL");
        assertThat(order.items().get(0).total()).isEqualByComparingTo("121.44");
        assertThat(order.items().get(1).total()).isEqualByComparingTo("37.20");
        assertThat(order.total()).isEqualByComparingTo("158.64");
        assertThat(order.id()).isEqualTo(ORDER_ID);
        assertThat(order.items().get(0).idProduct()).isEqualTo(P1);
    }

    @Test
    void conversionRoundsEachItemAndTotalIsTheSumOfConvertedItems() {
        when(orderRepository.findByIdAndIdAccount(ORDER_ID, ACCOUNT)).thenReturn(Optional.of(storedOrder()));
        when(exchangeLookup.sell("USD", "BRL", ACCOUNT)).thenReturn(new BigDecimal("5.4321"));

        Order order = orderService.findById(ACCOUNT, ORDER_ID, "BRL");

        // 20.24 x 5.4321 = 109.945704 -> 109.95 ; 6.20 x 5.4321 = 33.67902 -> 33.68
        assertThat(order.items().get(0).total()).isEqualByComparingTo("109.95");
        assertThat(order.items().get(1).total()).isEqualByComparingTo("33.68");
        // soma dos itens convertidos (143.63), e nao 26.44 x 5.4321 = 143.62: os itens batem com o total
        assertThat(order.total()).isEqualByComparingTo("143.63");
    }

    @Test
    void currencyIsTrimmedAndUppercasedBeforeCallingExchange() {
        when(orderRepository.findByIdAndIdAccount(ORDER_ID, ACCOUNT)).thenReturn(Optional.of(storedOrder()));
        when(exchangeLookup.sell("USD", "EUR", ACCOUNT)).thenReturn(new BigDecimal("0.92"));

        assertThat(orderService.findById(ACCOUNT, ORDER_ID, " eur ").currency()).isEqualTo("EUR");
    }

    @Test
    void currencyUnknownToExchangeReturns422() {
        when(orderRepository.findByIdAndIdAccount(ORDER_ID, ACCOUNT)).thenReturn(Optional.of(storedOrder()));
        // qualquer um dos 4xx "moeda invalida" do Exchange vira 422 no Order
        when(exchangeLookup.sell("USD", "XYZ", ACCOUNT))
            .thenThrow(exchangeError(404), exchangeError(422), exchangeError(400));

        assertStatus(() -> orderService.findById(ACCOUNT, ORDER_ID, "XYZ"), HttpStatus.UNPROCESSABLE_CONTENT);
        assertStatus(() -> orderService.findById(ACCOUNT, ORDER_ID, "XYZ"), HttpStatus.UNPROCESSABLE_CONTENT);
        assertStatus(() -> orderService.findById(ACCOUNT, ORDER_ID, "XYZ"), HttpStatus.UNPROCESSABLE_CONTENT);
    }

    @Test
    void invalidCurrencyFormatReturns422WithoutCallingExchange() {
        when(orderRepository.findByIdAndIdAccount(ORDER_ID, ACCOUNT)).thenReturn(Optional.of(storedOrder()));

        assertStatus(() -> orderService.findById(ACCOUNT, ORDER_ID, "REAL"), HttpStatus.UNPROCESSABLE_CONTENT);
        assertStatus(() -> orderService.findById(ACCOUNT, ORDER_ID, "BR1"), HttpStatus.UNPROCESSABLE_CONTENT);
        assertStatus(() -> orderService.findById(ACCOUNT, ORDER_ID, "B"), HttpStatus.UNPROCESSABLE_CONTENT);
        verify(exchangeLookup, never()).sell(any(), any(), any());
    }

    @Test
    void exchangeDownReturns503() {
        when(orderRepository.findByIdAndIdAccount(ORDER_ID, ACCOUNT)).thenReturn(Optional.of(storedOrder()));
        when(exchangeLookup.sell("USD", "BRL", ACCOUNT)).thenThrow(exchangeError(503));

        assertStatus(() -> orderService.findById(ACCOUNT, ORDER_ID, "BRL"), HttpStatus.SERVICE_UNAVAILABLE);
    }

    @Test
    void invalidRateFromExchangeReturns503() {
        when(orderRepository.findByIdAndIdAccount(ORDER_ID, ACCOUNT)).thenReturn(Optional.of(storedOrder()));
        // null = resposta invalida do Exchange (sell ausente, zero ou corpo vazio; ver ExchangeLookup)
        when(exchangeLookup.sell("USD", "BRL", ACCOUNT)).thenReturn(null);

        assertStatus(() -> orderService.findById(ACCOUNT, ORDER_ID, "BRL"), HttpStatus.SERVICE_UNAVAILABLE);
    }

    // ---------- helpers ----------

    private static void assertStatus(ThrowingCallable call, HttpStatus expected) {
        assertThatThrownBy(call)
            .isInstanceOfSatisfying(ResponseStatusException.class,
                e -> assertThat(e.getStatusCode()).isEqualTo(expected));
    }

    private static Order order(OrderItem... items) {
        return Order.builder().items(List.of(items)).build();
    }

    private static OrderItem item(String idProduct, Integer quantity) {
        return OrderItem.builder().idProduct(idProduct).quantity(quantity).build();
    }

    private static ProductOut product(String id, String price) {
        return ProductOut.builder()
            .id(id).name("Produto " + id).price(new BigDecimal(price)).unit("un")
            .build();
    }

    // erro do Product
    private static FeignException feignError(int status) {
        return feignError(status, "http://product:8080/products/" + P1, "ProductController#findById(String)");
    }

    // erro do Exchange
    private static FeignException exchangeError(int status) {
        return feignError(status, "http://exchange:8080/exchange/USD/XYZ", "ExchangeClient#rate(String,String,String)");
    }

    // FeignException do status pedido, igual a que o Feign lanca de verdade (404 -> NotFound...)
    private static FeignException feignError(int status, String url, String methodKey) {
        Request request = Request.create(Request.HttpMethod.GET, url, Map.of(), null, StandardCharsets.UTF_8, null);
        Response response = Response.builder()
            .status(status).reason("error").request(request).headers(Map.of())
            .build();
        return FeignException.errorStatus(methodKey, response);
    }

    // pedido como viria do banco: 2 x 10.12 + 10 x 0.62 = 26.44
    private static OrderModel storedOrder() {
        return new OrderModel(Order.builder()
            .id(ORDER_ID)
            .idAccount(ACCOUNT)
            .date(LocalDateTime.of(2025, 9, 1, 12, 30, 0))
            .total(new BigDecimal("26.44"))
            .items(List.of(
                OrderItem.builder().id("item-1").idProduct(P1).quantity(2).unitPrice(new BigDecimal("10.12")).build(),
                OrderItem.builder().id("item-2").idProduct(P2).quantity(10).unitPrice(new BigDecimal("0.62")).build()))
            .build());
    }

}
