"""Mede o efeito do cache do Exchange (bottleneck 1).

Dispara N requisições GET /exchange/USD/BRL com C threads e mostra a latência (p50/p95/máx)
e quantas foram "miss" (o PTAX foi chamado), lendo o header X-Cache.

    python bench/bench.py --url http://127.0.0.1:8080 --n 100 --c 5

Rode uma vez com o serviço normal e outra com CACHE_SECONDS=0 (sem cache) e compare.
Não aumente muito o N sem cache: o PTAX é um serviço público do Banco Central.
"""

import argparse
import statistics
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import httpx

p = argparse.ArgumentParser()
p.add_argument("--url", default="http://127.0.0.1:8080")
p.add_argument("--path", default="/exchange/USD/BRL")
p.add_argument("--n", type=int, default=100)
p.add_argument("--c", type=int, default=5)
args = p.parse_args()

headers = {"id-account": "0195ae95-5be7-7dd3-b35d-7a7d87c404fb"}
client = httpx.Client(base_url=args.url, headers=headers, timeout=10)


def one(_):
    start = time.perf_counter()
    r = client.get(args.path)
    return (time.perf_counter() - start) * 1000, r.status_code, r.headers.get("X-Cache", "-")


wall = time.perf_counter()
with ThreadPoolExecutor(args.c) as pool:
    results = list(pool.map(one, range(args.n)))
wall = time.perf_counter() - wall

lat = sorted(r[0] for r in results)
print(f"requisicoes: {args.n} ({args.c} em paralelo) em {wall:.2f} s -> {args.n / wall:.0f} req/s")
print(f"status: {dict(Counter(r[1] for r in results))}")
print(f"X-Cache: {dict(Counter(r[2] for r in results))}")
print(
    f"latencia ms: p50={statistics.median(lat):.1f} "
    f"p95={lat[int(len(lat) * 0.95) - 1]:.1f} max={lat[-1]:.1f}"
)
