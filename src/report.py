"""Saídas: relatório da execução (JSON + HTML), fila de revisão humana (CSV), Excel e painel do gestor (HTML)."""
import csv
import json
from html import escape

from openpyxl import Workbook

from config import settings
from src import dashboard


def write_all(summary: dict, events: list, store) -> dict:
    out = settings.OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    (out / "relatorio_execucao.json").write_text(
        json.dumps({"resumo": summary, "eventos": events}, ensure_ascii=False, indent=2), encoding="utf-8")

    rows = "".join(
        f"<tr><td>{escape(str(e['arquivo']))}</td><td>{escape(str(e['resultado']))}</td>"
        f"<td>{escape(str(e.get('protocolo') or ''))}</td><td>{escape(str(e.get('detalhe') or ''))}</td></tr>"
        for e in events)
    resumo = "".join(f"<li>{escape(k)}: <b>{escape(str(v))}</b></li>" for k, v in summary.items())
    (out / "relatorio_execucao.html").write_text(
        f'<!doctype html><meta charset="utf-8"><title>Relatório</title><h1>Relatório da execução</h1>'
        f"<ul>{resumo}</ul><table border=1 cellpadding=4><tr><th>Arquivo</th><th>Resultado</th><th>Protocolo</th>"
        f"<th>Detalhe</th></tr>{rows}</table>", encoding="utf-8")

    review = store.review_queue()
    with open(out / "fila_revisao_humana.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["protocolo", "categoria_sugerida", "confianca", "motivo", "endereco", "texto_mascarado"])
        for r in review:
            w.writerow([r["protocolo"], r["categoria"], round(r["confianca"] or 0, 2), r["motivo_revisao"],
                        r["endereco"], r["texto_mascarado"]])

    wb = Workbook()
    ws = wb.active
    ws.title = "Ocorrencias"
    ws.append(["id", "categoria", "prioridade", "n_relatos", "endereco", "ticket", "status"])
    for o in store.all_occurrences():
        ws.append([o["id"], o["categoria"], o["prioridade"], o["n_relatos"], o["endereco"], o["ticket"], o["status"]])
    ws2 = wb.create_sheet("Revisao humana")
    ws2.append(["protocolo", "categoria_sugerida", "confianca", "motivo", "texto_mascarado"])
    for r in review:
        ws2.append([r["protocolo"], r["categoria"], round(r["confianca"] or 0, 2), r["motivo_revisao"], r["texto_mascarado"]])
    wb.save(out / "painel_gestor.xlsx")
    (out / "painel_gestor.html").write_text(
        dashboard.render(store, {"resumo": summary, "eventos": events}), encoding="utf-8")
    return {"json": str(out / "relatorio_execucao.json"), "html": str(out / "relatorio_execucao.html")}
