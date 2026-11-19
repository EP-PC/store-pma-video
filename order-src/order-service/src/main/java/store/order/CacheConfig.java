package store.order;

import java.math.BigDecimal;
import java.time.Duration;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.cache.autoconfigure.RedisCacheManagerBuilderCustomizer;
import org.springframework.cache.Cache;
import org.springframework.cache.annotation.CachingConfigurer;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.cache.interceptor.CacheErrorHandler;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.cache.RedisCacheConfiguration;
import org.springframework.data.redis.serializer.JacksonJsonRedisSerializer;
import org.springframework.data.redis.serializer.RedisSerializationContext.SerializationPair;
import org.springframework.data.redis.serializer.RedisSerializer;

import lombok.extern.slf4j.Slf4j;
import store.product.ProductOut;

/**
 * Bottleneck 1 (caching): cache no Redis das consultas que o Order faz a outros servicos.
 *
 *  - products: GET /products/{id} no Product (preco e existencia do produto), usado no POST /orders
 *  - rates:    cotacao USD -> moeda no Exchange, usada no GET /orders/{id}?currency=
 *
 * TTL curto (padrao 60 s): preco e cotacao mudam, mas ate 1 minuto de defasagem e aceitavel
 * e corta as chamadas HTTP repetidas. Valores em JSON (legivel no redis-cli), chaves com
 * prefixo "order:" (ex.: order:products::<id>) para nao colidir com outro servico no mesmo Redis.
 */
@Slf4j
@Configuration
@EnableCaching
public class CacheConfig implements CachingConfigurer {

    public static final String PRODUCTS = "products";
    public static final String RATES = "rates";

    @Bean
    public RedisCacheManagerBuilderCustomizer orderCaches(@Value("${store.order.cache.ttl:60s}") Duration ttl) {
        return builder -> builder
            .withCacheConfiguration(PRODUCTS, config(ttl, new JacksonJsonRedisSerializer<>(ProductOut.class)))
            .withCacheConfiguration(RATES, config(ttl, new JacksonJsonRedisSerializer<>(BigDecimal.class)));
    }

    private static RedisCacheConfiguration config(Duration ttl, RedisSerializer<?> serializer) {
        return RedisCacheConfiguration.defaultCacheConfig()
            .entryTtl(ttl)
            .disableCachingNullValues()
            .prefixCacheNameWith("order:")
            .serializeValuesWith(SerializationPair.fromSerializer(serializer));
    }

    // Redis fora do ar NAO derruba o Order: o erro do cache vira um aviso no log e o metodo
    // segue sem cache (chama o Product/Exchange direto). O cache e otimizacao, nao dependencia.
    @Override
    public CacheErrorHandler errorHandler() {
        return new CacheErrorHandler() {
            @Override
            public void handleCacheGetError(RuntimeException e, Cache cache, Object key) {
                log.warn("Cache {} indisponivel na leitura (key {}): {}", cache.getName(), key, e.getMessage());
            }

            @Override
            public void handleCachePutError(RuntimeException e, Cache cache, Object key, Object value) {
                log.warn("Cache {} indisponivel na escrita (key {}): {}", cache.getName(), key, e.getMessage());
            }

            @Override
            public void handleCacheEvictError(RuntimeException e, Cache cache, Object key) {
                log.warn("Cache {} indisponivel no evict (key {}): {}", cache.getName(), key, e.getMessage());
            }

            @Override
            public void handleCacheClearError(RuntimeException e, Cache cache) {
                log.warn("Cache {} indisponivel no clear: {}", cache.getName(), e.getMessage());
            }
        };
    }

}
