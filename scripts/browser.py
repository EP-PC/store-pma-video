#!/usr/bin/env python3
"""Grava o navegador (Chromium headless, 1920x1080) com o Playwright.

    browser.py grafana SEGUNDOS   painel Store / Order do Grafana com tráfego real
    browser.py docs               passeio pelo site MkDocs (servido em :8000)
"""
import shutil
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

W, H = 1920, 1080
OUT = Path("videos")


def smooth_scroll(page, total_px, step=6, wait_ms=16):
    for _ in range(total_px // step):
        page.mouse.wheel(0, step)
        page.wait_for_timeout(wait_ms)


def grafana(page, seconds):
    page.goto("http://localhost:3000/d/order?orgId=1&refresh=5s&from=now-5m&to=now&kiosk&theme=dark")
    page.wait_for_timeout(seconds * 1000)


def docs(page):
    base = "http://127.0.0.1:8000/store-pma-docs/"
    page.mouse.move(W - 40, H // 2)
    for path, scroll in [("", 900), ("projeto/arquitetura/", 1500), ("projeto/bottlenecks/", 1800),
                         ("projeto/custos/", 1400)]:
        page.goto(base + path)
        page.wait_for_timeout(2500)  # Mermaid e MathJax renderizam
        smooth_scroll(page, scroll)
        page.wait_for_timeout(1500)


def main():
    scene = sys.argv[1]
    tmp = OUT / f"tmp-{scene}"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": W, "height": H}, color_scheme="dark",
                                  record_video_dir=str(tmp), record_video_size={"width": W, "height": H})
        page = ctx.new_page()
        if scene == "grafana":
            grafana(page, int(sys.argv[2]))
        else:
            docs(page)
        video = page.video.path()
        ctx.close()
        browser.close()
    shutil.move(video, OUT / f"{scene}.webm")
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    main()
