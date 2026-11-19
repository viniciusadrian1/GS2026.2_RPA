"""Tira prints (PNG) do painel do gestor e do relatório da execução, para anexar como evidência.
Uso: python scripts/capturar_prints.py [prefixo]    (rode depois de `python main.py --demo`)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from playwright.sync_api import sync_playwright  # noqa: E402

from config import settings  # noqa: E402

prefixo = sys.argv[1] if len(sys.argv) > 1 else ""
destino = settings.BASE_DIR / "docs" / "evidencias" / "prints"
destino.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    for nome in ("painel_gestor", "relatorio_execucao"):
        arquivo = settings.OUTPUT_DIR / f"{nome}.html"
        if not arquivo.exists():
            print("não encontrei", arquivo, "- rode python main.py --demo antes")
            continue
        page.goto(arquivo.as_uri())
        page.wait_for_timeout(800)
        page.screenshot(path=str(destino / f"{prefixo}{nome}.png"), full_page=True)
        print("salvo:", destino / f"{prefixo}{nome}.png")
    browser.close()
