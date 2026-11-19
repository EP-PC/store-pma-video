package store.order;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import feign.FeignException;
import feign.Request;
import feign.Response;
import store.exchange.ExchangeClient;
import store.exchange.ExchangeOut;
import store.product.ProductController;
import store.product.ProductOut;

/**
 * Teste de integracao da camada HTTP: requisicoes de verdade (MockMvc) passando pelo
 * OrderResource -> OrderService (REAL) -> OrderExceptionHandler, com mock so nas pontas
 * (banco, Product e Exchange). Cobre rotas, header id-account, status, Location e formato do JSON.
 */
// ProductLookup/ExchangeLookup reais (sem cache: o @WebMvcTest nao carrega o CacheConfig),
// chamando os clientes Feign mockados abaixo
@WebMvcTest(OrderResource.class)
@Import({ OrderService.class, ProductLookup.class, ExchangeLookup.class })
class OrderResourceTest {

    private static final String ACCOUNT = "0195ae95-5be7-7dd3-b35d-7a7d87c404fb";
    private static final String OTHER_ACCOUNT = "0195ae95-0000-7000-8000-000000000002";
    private static final String P1 = "0195abfb-7074-73a9-9d26-b4b9fbaab0a8";
    private static final String P2 = "0195abfe-e416-7052-be3b-27cdaf12a984";
    private static final String ORDER_ID = "0195ac33-73e5-7cb3-90ca-7b5e7e549569";
    private static final String ISO_SECONDS = "\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}";

    private static final String BODY = """
        {
            "items": [
                { "idProduct": "%s", "quantity": 2 },
                { "idProduct": "%s", "quantity": 10 }
            ]
        }
        """.formatted(P1, P2);

    @Autowired
    private MockMvc mvc;

    @MockitoBean
    private OrderRepository orderRepository;

    @MockitoBean
    private ProductController productController;

    @MockitoBean
    private ExchangeClient exchangeClient;

    // ---------- POST /orders ----------

    @Test
    void postCreatesOrderAndReturns201WithLocationAndBody() throws Exception {
        when(productController.findById(P1)).thenReturn(product(P1, "10.12"));
        when(productController.findById(P2)).thenReturn(product(P2, "0.62"));
        when(orderRepository.save(any(OrderModel.class))).thenAnswer(inv -> {
            OrderModel model = inv.getArgument(0);
            return model.id(ORDER_ID);   // simula o UUID gerado pelo banco
        });

        mvc.perform(post("/orders").header("id-account", ACCOUNT)
                .contentType(MediaType.APPLICATION_JSON).content(BODY))
            .andExpect(status().isCreated())
            .andExpect(header().string("Location", "http://localhost/orders/" + ORDER_ID))
            .andExpect(jsonPath("$.id").value(ORDER_ID))
            .andExpect(jsonPath("$.date").value(org.hamcrest.Matchers.matchesPattern(ISO_SECONDS)))
            .andExpect(jsonPath("$.currency").value("USD"))
            .andExpect(jsonPath("$.items.length()").value(2))
            .andExpect(jsonPath("$.items[0].product.id").value(P1))
            .andExpect(jsonPath("$.items[0].quantity").value(2))
            .andExpect(jsonPath("$.items[0].total").value(20.24))
            .andExpect(jsonPath("$.items[1].product.id").value(P2))
            .andExpect(jsonPath("$.items[1].total").value(6.2))
            .andExpect(jsonPath("$.total").value(26.44));
    }

    @Test
    void postWithUnknownProductReturns400() throws Exception {
        when(productController.findById(P1)).thenThrow(feignError(404));

        mvc.perform(post("/orders").header("id-account", ACCOUNT)
                .contentType(MediaType.APPLICATION_JSON).content(BODY))
            .andExpect(status().isBadRequest())
            .andExpect(jsonPath("$.status").value(400))
            .andExpect(jsonPath("$.message").value("Product not found: " + P1));
        verify(orderRepository, never()).save(any());
    }

    @Test
    void postWithMalformedJsonReturns400() throws Exception {
        mvc.perform(post("/orders").header("id-account", ACCOUNT)
                .contentType(MediaType.APPLICATION_JSON).content("{\"items\": [{\"quantity\": \"abc\"}]}"))
            .andExpect(status().isBadRequest())
            .andExpect(jsonPath("$.message").value("Malformed or invalid request body"));
    }

    @Test
    void postWithoutIdAccountReturns401() throws Exception {
        mvc.perform(post("/orders").contentType(MediaType.APPLICATION_JSON).content(BODY))
            .andExpect(status().isUnauthorized())
            .andExpect(jsonPath("$.status").value(401))
            .andExpect(jsonPath("$.path").value("/orders"));
        verify(orderRepository, never()).save(any());
    }

    // ---------- GET /orders ----------

    @Test
    void getOrdersReturnsSummariesOfCurrentAccount() throws Exception {
        when(orderRepository.findByIdAccountOrderByDateDesc(ACCOUNT)).thenReturn(List.of(storedOrder()));

        mvc.perform(get("/orders").header("id-account", ACCOUNT))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.length()").value(1))
            .andExpect(jsonPath("$[0].id").value(ORDER_ID))
            .andExpect(jsonPath("$[0].date").value("2025-09-01T12:30:00"))
            .andExpect(jsonPath("$[0].total").value(26.44))
            .andExpect(jsonPath("$[0].items").doesNotExist());   // {id, date, total} apenas
    }

    @Test
    void getOrdersWithoutIdAccountReturns401() throws Exception {
        mvc.perform(get("/orders"))
            .andExpect(status().isUnauthorized());
    }

    // ---------- GET /orders/{id} ----------

    @Test
    void getOrderByIdReturnsDetailsInUsd() throws Exception {
        when(orderRepository.findByIdAndIdAccount(ORDER_ID, ACCOUNT)).thenReturn(Optional.of(storedOrder()));

        mvc.perform(get("/orders/{id}", ORDER_ID).header("id-account", ACCOUNT))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.id").value(ORDER_ID))
            .andExpect(jsonPath("$.date").value("2025-09-01T12:30:00"))
            .andExpect(jsonPath("$.currency").value("USD"))
            .andExpect(jsonPath("$.items[0].id").value("item-1"))
            .andExpect(jsonPath("$.items[0].product.id").value(P1))
            .andExpect(jsonPath("$.items[0].quantity").value(2))
            .andExpect(jsonPath("$.items[0].total").value(20.24))
            .andExpect(jsonPath("$.total").value(26.44));
    }

    @Test
    void getOrderOfAnotherAccountReturns404() throws Exception {
        when(orderRepository.findByIdAndIdAccount(ORDER_ID, OTHER_ACCOUNT)).thenReturn(Optional.empty());

        mvc.perform(get("/orders/{id}", ORDER_ID).header("id-account", OTHER_ACCOUNT))
            .andExpect(status().isNotFound())
            .andExpect(jsonPath("$.message").value("Order not found"));
    }

    @Test
    void getOrderWithoutIdAccountReturns401() throws Exception {
        mvc.perform(get("/orders/{id}", ORDER_ID))
            .andExpect(status().isUnauthorized());
    }

    @Test
    void getOrderInBrlReturnsConvertedTotals() throws Exception {
        when(orderRepository.findByIdAndIdAccount(ORDER_ID, ACCOUNT)).thenReturn(Optional.of(storedOrder()));
        when(exchangeClient.rate("USD", "BRL", ACCOUNT)).thenReturn(ResponseEntity.ok(ExchangeOut.builder()
            .sell(new BigDecimal("6.00")).buy(new BigDecimal("5.90"))
            .date("2026-11-18 12:00:00").idAccount(ACCOUNT).build()));

        // mesmo JSON do exemplo ?currency=BRL do enunciado
        mvc.perform(get("/orders/{id}", ORDER_ID).param("currency", "BRL").header("id-account", ACCOUNT))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.id").value(ORDER_ID))
            .andExpect(jsonPath("$.date").value("2025-09-01T12:30:00"))
            .andExpect(jsonPath("$.currency").value("BRL"))
            .andExpect(jsonPath("$.items[0].product.id").value(P1))
            .andExpect(jsonPath("$.items[0].quantity").value(2))
            .andExpect(jsonPath("$.items[0].total").value(121.44))
            .andExpect(jsonPath("$.items[1].total").value(37.2))
            .andExpect(jsonPath("$.total").value(158.64));
    }

    @Test
    void getOrderWithUnsupportedCurrencyReturns422() throws Exception {
        when(orderRepository.findByIdAndIdAccount(ORDER_ID, ACCOUNT)).thenReturn(Optional.of(storedOrder()));
        when(exchangeClient.rate("USD", "XYZ", ACCOUNT))
            .thenThrow(feignError(404, "http://exchange:8080/exchange/USD/XYZ", "ExchangeClient#rate(String,String,String)"));

        mvc.perform(get("/orders/{id}", ORDER_ID).param("currency", "XYZ").header("id-account", ACCOUNT))
            .andExpect(status().isUnprocessableContent())
            .andExpect(jsonPath("$.status").value(422))
            .andExpect(jsonPath("$.message").value("Currency not supported: XYZ"));
    }

    @Test
    void getOrderWithExchangeDownReturns503() throws Exception {
        when(orderRepository.findByIdAndIdAccount(ORDER_ID, ACCOUNT)).thenReturn(Optional.of(storedOrder()));
        when(exchangeClient.rate("USD", "BRL", ACCOUNT))
            .thenThrow(feignError(503, "http://exchange:8080/exchange/USD/BRL", "ExchangeClient#rate(String,String,String)"));

        mvc.perform(get("/orders/{id}", ORDER_ID).param("currency", "BRL").header("id-account", ACCOUNT))
            .andExpect(status().isServiceUnavailable())
            .andExpect(jsonPath("$.message").value("Exchange service unavailable"));
    }

    @Test
    void healthCheckReturns200() throws Exception {
        mvc.perform(get("/orders/health-check"))
            .andExpect(status().isOk());
    }

    // ---------- helpers ----------

    private static ResponseEntity<ProductOut> product(String id, String price) {
        return ResponseEntity.ok(ProductOut.builder()
            .id(id).name("Produto " + id).price(new BigDecimal(price)).unit("un")
            .build());
    }

    private static FeignException feignError(int status) {
        return feignError(status, "http://product:8080/products/" + P1, "ProductController#findById(String)");
    }

    private static FeignException feignError(int status, String url, String methodKey) {
        Request request = Request.create(Request.HttpMethod.GET, url, Map.of(), null, StandardCharsets.UTF_8, null);
        Response response = Response.builder()
            .status(status).reason("error").request(request).headers(Map.of())
            .build();
        return FeignException.errorStatus(methodKey, response);
    }

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
