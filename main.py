"""Ponto de entrada único do Bairro em Dia.

  python main.py --demo                  # sobe o portal simulado, processa a inbox e gera relatórios
  python main.py --manter-portal         # idem, e deixa o portal aberto para você abrir no navegador
  python main.py --sem-portal            # processa sem o robô do portal
  python main.py --consultar BED-XXXX    # morador acompanha o protocolo
  python main.py --perguntar "texto"     # assistente
  python main.py --treinar               # (re)treina o classificador
  python main.py --demo --loop 10        # repete a cada 10 min, sem intervenção
"""
import argparse
import json
import subprocess
import sys
import time
from urllib.parse import urlparse

import requests

from config import settings
from src import assistant, classifier, report
from src.pipeline import Pipeline
from src.protocol import Store
from src.rpa_portal import PortalRobot
from src.utils.logger import get_logger, setup_logging

log = get_logger("main")


def start_mock_portal():
    port = str(urlparse(settings.PORTAL_URL).port or 8000)
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "mock_portal.app:app", "--port", port,
                             "--log-level", "warning"], cwd=str(settings.BASE_DIR))
    for _ in range(40):
        try:
            if requests.get(f"{settings.PORTAL_URL}/health", timeout=1).ok:
                log.info("Portal simulado no ar em %s", settings.PORTAL_URL)
                return proc
        except requests.exceptions.RequestException:
            time.sleep(0.25)
    proc.terminate()
    raise RuntimeError("portal simulado não subiu")


def run_once(args):
    store = Store()
    portal_proc = start_mock_portal() if args.demo else None
    try:
        clf = classifier.Classifier()
        if args.sem_portal:
            summary, events = Pipeline(store, clf).run(args.inbox)
        else:
            with PortalRobot() as robot:
                summary, events = Pipeline(store, clf, robot).run(args.inbox)
        paths = report.write_all(summary, events, store)
        print("\n=== RESUMO DA EXECUÇÃO ===")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print("Relatórios:", paths["html"])
        print("Painel do gestor:", settings.OUTPUT_DIR / "painel_gestor.html")
        if args.manter_portal and portal_proc:
            print(f"\nPortal no ar para você olhar: {settings.PORTAL_URL}/gestor (painel do gestor), "
                  f"{settings.PORTAL_URL}/painel (chamados do órgão), /novo (formulário)")
            try:
                input("Pressione ENTER para encerrar o portal... ")
            except EOFError:
                pass
    finally:
        store.close()
        if portal_proc:
            portal_proc.terminate()


def main():
    p = argparse.ArgumentParser(description="Bairro em Dia - robô de triagem de relatos")
    p.add_argument("--inbox", default=str(settings.INBOX_DIR))
    p.add_argument("--demo", action="store_true", help="sobe o portal simulado automaticamente")
    p.add_argument("--sem-portal", action="store_true")
    p.add_argument("--manter-portal", action="store_true", help="com --demo: mantém o portal aberto até você apertar ENTER")
    p.add_argument("--consultar", metavar="PROTOCOLO")
    p.add_argument("--perguntar", metavar="TEXTO")
    p.add_argument("--treinar", action="store_true")
    p.add_argument("--loop", type=float, metavar="MINUTOS")
    args = p.parse_args()
    if args.manter_portal:
        args.demo = True
    setup_logging()

    if args.treinar:
        classifier.train()
        return
    if args.perguntar:
        res = assistant.answer(args.perguntar)
        print(res["resposta"])
        origem = "LLM (Groq) reescrevendo a base" if res["llm"] else "base de serviços (sem LLM)"
        print(f"\n[fonte: {res['fonte']} | gerada por: {origem}]")
        return
    if args.consultar:
        store = Store()
        res = store.consultar(args.consultar)
        print(json.dumps(res, ensure_ascii=False, indent=2) if res else "Protocolo não encontrado.")
        return
    if args.loop:
        while True:
            run_once(args)
            time.sleep(args.loop * 60)
    run_once(args)


if __name__ == "__main__":
    main()
