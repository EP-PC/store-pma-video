package store.order;

import java.math.BigDecimal;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Component;

import store.exchange.ExchangeClient;
import store.exchange.ExchangeOut;

/**
 * Cotacao no Exchange com cache (bottleneck 1). Devolve so a taxa "sell" (a usada na conversao).
 */
@Component
public class ExchangeLookup {

    @Autowired
    private ExchangeClient exchangeClient;         // cliente Feign do Exchange (Python)

    // A cotacao e a mesma para todos os usuarios: a chave e so "from-to" (ex.: USD-BRL), sem o
    // id-account, entao a consulta de um usuario aproveita a cotacao buscada para outro.
    // Resposta invalida (sem body, sell ausente ou <= 0) devolve null e NAO entra no cache;
    // erros do Exchange (FeignException) tambem nao.
    @Cacheable(cacheNames = CacheConfig.RATES, key = "#from + '-' + #to", unless = "#result == null")
    public BigDecimal sell(String from, String to, String idAccount) {
        ExchangeOut exchange = exchangeClient.rate(from, to, idAccount).getBody();
        if (exchange == null || exchange.sell() == null || exchange.sell().signum() <= 0) {
            return null;
        }
        return exchange.sell();
    }

}
