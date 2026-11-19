-- pedido: valores sempre em USD (a conversao de moeda e feita na leitura, via Exchange)
CREATE TABLE orders.orders (
    id VARCHAR(36) PRIMARY KEY,
    id_account VARCHAR(36) NOT NULL,
    date TIMESTAMP NOT NULL,
    total NUMERIC(12,2) NOT NULL
);

-- GET /orders filtra pelo dono
CREATE INDEX idx_orders_id_account ON orders.orders (id_account);

-- item do pedido: parte do agregado Order (so existe dentro de um pedido).
-- unit_price guarda o preco do produto no momento da compra: se o produto
-- mudar de preco depois, o pedido antigo nao muda.
CREATE TABLE orders.order_items (
    id VARCHAR(36) PRIMARY KEY,
    id_order VARCHAR(36) NOT NULL REFERENCES orders.orders (id),
    id_product VARCHAR(36) NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12,2) NOT NULL
);

-- o Postgres nao cria indice para FK automaticamente; os itens sao lidos por pedido
CREATE INDEX idx_order_items_id_order ON orders.order_items (id_order);
