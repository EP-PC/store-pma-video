package store.order;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.openfeign.EnableFeignClients;

// clientes Feign: ProductController (contrato store:product) e ExchangeClient (store.exchange),
// os dois fora do scan padrao de store.order.
// store.order fica DE FORA de proposito: o OrderController tambem e @FeignClient e viraria
// um cliente Feign, conflitando com o OrderResource (que implementa a mesma interface).
@EnableFeignClients(basePackages = { "store.product", "store.exchange" })
@SpringBootApplication
public class OrderServiceApplication {

    public static void main(String[] args) {
        SpringApplication.run(OrderServiceApplication.class, args);
    }

}
