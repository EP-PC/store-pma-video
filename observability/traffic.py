# Gerador de trafego LEVE para o painel Store / Order do Grafana (demo local, NAO e teste de carga).
# Fala direto com o order e o product na rede do compose, sem gateway: manda id-account (e
# id-role ADMIN para criar os produtos) a mao. Roda num container ao lado do compose:
#
#   docker run --rm --network store_default -v "$PWD/observability/traffic.py:/traffic.py:ro" \
#     -e DURATION=90 python:3.13-alpine python -u /traffic.py
#
# CURRENCY=1 inclui conversoes de moeda (?currency=BRL/XYZ): so faz sentido com o exchange de pe.
import json
import os
import random
import threading
import time
import urllib.error
import urllib.request
from collections import Counter

ORDER = "http://order:8080"
PRODUCT = "http://product:8080"
DURATION = int(os.environ.get("DURATION", "90"))
THREADS = int(os.environ.get("THREADS", "4"))
PAUSE = float(os.environ.get("PAUSE", "0.05"))
CURRENCY = os.environ.get("CURRENCY", "0") == "1"
ACCOUNTS = ["0195ae95-5be7-7dd3-b35d-7a7d87c404f%d" % i for i in range(5)]


def call(method, url, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, None


# produtos de teste (o product aceita escrita com id-role ADMIN; sem gateway, o header vai a mao)
admin = {"id-account": ACCOUNTS[0], "id-role": "ADMIN"}
products = []
for name, price in [("Caneca", 10.12), ("Adesivo", 0.62), ("Camiseta", 25.90)]:
    status, p = call("POST", f"{PRODUCT}/products", {"name": name, "price": price, "unit": "un"}, admin)
    products.append(p["id"])
print("produtos:", products, flush=True)

orders = {a: [] for a in ACCOUNTS}
stats = Counter()
lock = threading.Lock()


def worker():
    end = time.time() + DURATION
    while time.time() < end:
        acc = random.choice(ACCOUNTS)
        h = {"id-account": acc}
        r = random.random()
        if r < 0.40 or not orders[acc]:
            items = [{"idProduct": random.choice(products), "quantity": random.randint(1, 5)}
                     for _ in range(random.randint(1, 3))]
            s, o = call("POST", f"{ORDER}/orders", {"items": items}, h)
            if s == 201:
                with lock:
                    orders[acc].append(o["id"])
            key = "POST /orders"
        elif r < 0.65:
            s, _ = call("GET", f"{ORDER}/orders", headers=h)
            key = "GET /orders"
        elif r < 0.85 or (not CURRENCY and r < 0.95):
            s, _ = call("GET", f"{ORDER}/orders/{random.choice(orders[acc])}", headers=h)
            key = "GET /orders/{id}"
        elif r < 0.95:
            s, _ = call("GET", f"{ORDER}/orders/{random.choice(orders[acc])}?currency=BRL", headers=h)
            key = "GET /orders/{id}?currency=BRL"
        elif r < 0.98 or not CURRENCY:
            s, _ = call("POST", f"{ORDER}/orders",
                        {"items": [{"idProduct": "00000000-0000-0000-0000-000000000000", "quantity": 1}]}, h)
            key = "POST /orders (produto inexistente)"
        else:
            s, _ = call("GET", f"{ORDER}/orders/{random.choice(orders[acc])}?currency=XYZ", headers=h)
            key = "GET /orders/{id}?currency=XYZ"
        with lock:
            stats[f"{key} -> {s}"] += 1
        time.sleep(PAUSE)


threads = [threading.Thread(target=worker) for _ in range(THREADS)]
for t in threads:
    t.start()
for t in threads:
    t.join()
for k, v in sorted(stats.items()):
    print(f"{v:5d}  {k}")
print("total:", sum(stats.values()), "requisicoes em", DURATION, "s", flush=True)
