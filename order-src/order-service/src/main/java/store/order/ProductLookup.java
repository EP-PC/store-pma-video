package store.order;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Component;

import store.product.ProductController;
import store.product.ProductOut;

/**
 * Consulta de produto no Product com cache (bottleneck 1). O POST /orders faz uma consulta
 * por item; pedidos seguidos com o mesmo produto reaproveitam a resposta do Redis.
 *
 * Fica fora do OrderService porque o @Cacheable funciona via proxy do Spring: um metodo
 * chamado de dentro da propria classe nao passaria pelo cache.
 */
@Component
public class ProductLookup {

    @Autowired
    private ProductController productController;   // cliente Feign do contrato store:product

    // So entra no cache produto encontrado: 404 (FeignException) e corpo vazio (null) nao ficam
    // guardados, entao um produto criado depois aparece na proxima consulta.
    @Cacheable(cacheNames = CacheConfig.PRODUCTS, unless = "#result == null")
    public ProductOut find(String idProduct) {
        return productController.findById(idProduct).getBody();
    }

}
