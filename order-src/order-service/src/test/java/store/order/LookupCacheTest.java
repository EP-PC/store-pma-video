package store.order;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.CacheManager;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.cache.concurrent.ConcurrentMapCacheManager;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Import;
import org.springframework.data.redis.serializer.JacksonJsonRedisSerializer;
import org.springframework.http.ResponseEntity;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.context.junit.jupiter.SpringJUnitConfig;

import feign.FeignException;
import feign.Request;
import feign.Response;
import store.exchange.ExchangeClient;
import store.exchange.ExchangeOut;
import store.product.ProductController;
import store.product.ProductOut;

/**
 * Teste do bottleneck 1 (caching): ProductLookup e ExchangeLookup num contexto Spring com
 * cache LIGADO (em memoria, no lugar do Redis), e os clientes Feign mockados para contar
 * quantas chamadas HTTP de fato aconteceriam.
 */
@SpringJUnitConfig(LookupCacheTest.Config.class)
class LookupCacheTest {

    @Configuration
    @EnableCaching
    @Import({ ProductLookup.class, ExchangeLookup.class })
    static class Config {
        @Bean
        CacheManager cacheManager() {
            return new ConcurrentMapCacheManager(CacheConfig.PRODUCTS, CacheConfig.RATES);
        }
    }

    private static final String USER_A = "0195ae95-5be7-7dd3-b35d-7a7d87c404fb";
    private static final String USER_B = "0195ae95-0000-7000-8000-000000000002";
    private static final String P1 = "0195abfb-7074-73a9-9d26-b4b9fbaab0a8";
    private static final String P2 = "0195abfe-e416-7052-be3b-27cdaf12a984";

    @MockitoBean
    private ProductController productController;

    @MockitoBean
    private ExchangeClient exchangeClient;

    @Autowired
    private ProductLookup productLookup;

    @Autowired
    private ExchangeLookup exchangeLookup;

    @Autowired
    private CacheManager cacheManager;

    @BeforeEach
    void clearCaches() {
        cacheManager.getCacheNames().forEach(name -> cacheManager.getCache(name).clear());
    }

    // ---------- products ----------

    @Test
    void sameProductIsFetchedFromProductOnlyOnce() {
        when(productController.findById(P1)).thenReturn(ResponseEntity.ok(product(P1, "10.12")));

        for (int i = 0; i < 5; i++) {
            assertThat(productLookup.find(P1).price()).isEqualByComparingTo("10.12");
        }

        verify(productController, times(1)).findById(P1);   // 5 consultas, 1 chamada HTTP
    }

    @Test
    void differentProductsAreCachedSeparately() {
        when(productController.findById(P1)).thenReturn(ResponseEntity.ok(product(P1, "10.12")));
        when(productController.findById(P2)).thenReturn(ResponseEntity.ok(product(P2, "0.62")));

        productLookup.find(P1);
        productLookup.find(P2);
        productLookup.find(P1);
        productLookup.find(P2);

        verify(productController, times(1)).findById(P1);
        verify(productController, times(1)).findById(P2);
    }

    @Test
    void unknownProductIsNotCached() {
        // 404 nao fica no cache: se o produto for criado depois, a proxima consulta ja o encontra
        when(productController.findById(P1)).thenThrow(feignError(404));

        assertThatThrownBy(() -> productLookup.find(P1)).isInstanceOf(FeignException.NotFound.class);
        assertThatThrownBy(() -> productLookup.find(P1)).isInstanceOf(FeignException.NotFound.class);

        verify(productController, times(2)).findById(P1);
    }

    @Test
    void emptyProductBodyIsNotCached() {
        when(productController.findById("health-check")).thenReturn(ResponseEntity.ok().build());

        assertThat(productLookup.find("health-check")).isNull();
        assertThat(productLookup.find("health-check")).isNull();

        verify(productController, times(2)).findById("health-check");
    }

    // ---------- rates ----------

    @Test
    void rateIsSharedBetweenUsers() {
        // a chave e "USD-BRL" (sem o id-account): a consulta do usuario B usa a cotacao buscada para A
        when(exchangeClient.rate("USD", "BRL", USER_A)).thenReturn(ResponseEntity.ok(rate("6.00")));

        assertThat(exchangeLookup.sell("USD", "BRL", USER_A)).isEqualByComparingTo("6.00");
        assertThat(exchangeLookup.sell("USD", "BRL", USER_B)).isEqualByComparingTo("6.00");

        verify(exchangeClient, times(1)).rate(any(), any(), any());
    }

    @Test
    void differentCurrenciesAreCachedSeparately() {
        when(exchangeClient.rate("USD", "BRL", USER_A)).thenReturn(ResponseEntity.ok(rate("6.00")));
        when(exchangeClient.rate("USD", "EUR", USER_A)).thenReturn(ResponseEntity.ok(rate("0.92")));

        assertThat(exchangeLookup.sell("USD", "BRL", USER_A)).isEqualByComparingTo("6.00");
        assertThat(exchangeLookup.sell("USD", "EUR", USER_A)).isEqualByComparingTo("0.92");
        assertThat(exchangeLookup.sell("USD", "BRL", USER_A)).isEqualByComparingTo("6.00");

        verify(exchangeClient, times(2)).rate(any(), any(), any());
    }

    @Test
    void invalidRateReturnsNullAndIsNotCached() {
        // sell ausente, sell zero e corpo vazio: null (o OrderService responde 503) e sem cache
        when(exchangeClient.rate("USD", "BRL", USER_A))
            .thenReturn(ResponseEntity.ok(rate(null)), ResponseEntity.ok(rate("0")), ResponseEntity.ok().build());

        assertThat(exchangeLookup.sell("USD", "BRL", USER_A)).isNull();
        assertThat(exchangeLookup.sell("USD", "BRL", USER_A)).isNull();
        assertThat(exchangeLookup.sell("USD", "BRL", USER_A)).isNull();

        verify(exchangeClient, times(3)).rate(any(), any(), any());
    }

    @Test
    void exchangeErrorIsNotCached() {
        when(exchangeClient.rate("USD", "XYZ", USER_A)).thenThrow(feignError(404));

        assertThatThrownBy(() -> exchangeLookup.sell("USD", "XYZ", USER_A)).isInstanceOf(FeignException.NotFound.class);
        assertThatThrownBy(() -> exchangeLookup.sell("USD", "XYZ", USER_A)).isInstanceOf(FeignException.NotFound.class);

        verify(exchangeClient, times(2)).rate(any(), any(), any());
    }

    // ---------- serializacao usada no Redis (CacheConfig) ----------

    @Test
    void cachedValuesSurviveRedisJsonSerialization() {
        JacksonJsonRedisSerializer<ProductOut> products = new JacksonJsonRedisSerializer<>(ProductOut.class);
        JacksonJsonRedisSerializer<BigDecimal> rates = new JacksonJsonRedisSerializer<>(BigDecimal.class);
        ProductOut product = product(P1, "10.12");

        assertThat(products.deserialize(products.serialize(product))).isEqualTo(product);
        assertThat(rates.deserialize(rates.serialize(new BigDecimal("5.4321")))).isEqualByComparingTo("5.4321");
    }

    // ---------- helpers ----------

    private static ProductOut product(String id, String price) {
        return ProductOut.builder().id(id).name("Produto " + id).price(new BigDecimal(price)).unit("un").build();
    }

    private static ExchangeOut rate(String sell) {
        return ExchangeOut.builder()
            .sell(sell == null ? null : new BigDecimal(sell))
            .buy(new BigDecimal("5.90"))
            .date("2026-11-18 12:00:00")
            .idAccount(USER_A)
            .build();
    }

    private static FeignException feignError(int status) {
        Request request = Request.create(Request.HttpMethod.GET, "http://service:8080/", Map.of(), null,
            StandardCharsets.UTF_8, null);
        Response response = Response.builder().status(status).reason("error").request(request).headers(Map.of()).build();
        return FeignException.errorStatus("Client#method()", response);
    }

}
