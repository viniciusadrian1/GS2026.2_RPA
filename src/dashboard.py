"""Painel do gestor: HTML com dados REAIS (banco SQLite + relatório da última execução). Sem JavaScript."""
import json
from datetime import datetime
from html import escape
from typing import Optional

from config import settings
from src import priority

ORDEM = {"urgente": 0, "alta": 1, "media": 2, "baixa": 3}
ROTULO = {"urgente": "Urgente", "alta": "Alta", "media": "Média", "baixa": "Baixa"}
CAT = {"buraco": "Buraco", "iluminacao": "Iluminação", "lixo": "Lixo", "ruido": "Ruído", "outros": "Outros"}
MODO = {"playwright": "navegador (Playwright)", "http": "HTTP direto", "desligado": "desligado"}

_CSS = """
body{margin:0;background:#F4F6F3;font-family:Inter,system-ui,-apple-system,'Segoe UI',sans-serif;color:#17202A}
.w{max-width:1280px;margin:0 auto;padding:32px;box-sizing:border-box;display:flex;flex-direction:column;gap:24px}
h1,h2{font-family:'Space Grotesk',Inter,system-ui,sans-serif;margin:0}
h1{font-size:36px;line-height:1.1;margin-top:4px}h2{font-size:20px}
.top{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:flex-end;gap:16px}
.eyebrow{font-size:13px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#0F6B63}
.meta{display:flex;flex-direction:column;align-items:flex-end;gap:8px;font-size:13px;color:#4A5563}
.tag{background:#DCEFEA;color:#0B4A44;padding:4px 10px;border-radius:999px;font-weight:600}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:16px}
.card{background:#fff;border:1px solid #E1E5DF;border-radius:12px}
.kpi{padding:18px}.kpi .l{font-size:13px;color:#4A5563}
.kpi .v{font-family:'Space Grotesk',Inter,sans-serif;font-size:36px;font-weight:700}.kpi .s{font-size:12px;color:#4A5563}
.row{display:flex;flex-wrap:wrap;gap:24px;align-items:flex-start}
.sub{font-size:13px;color:#4A5563;margin-top:2px}.pad{padding:18px}
.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;min-width:620px}
th{text-align:left;font-size:12px;font-weight:600;color:#4A5563;padding:10px 14px;letter-spacing:.04em;text-transform:uppercase}
td{padding:13px 14px;border-top:1px solid #E1E5DF;font-size:14px;vertical-align:top}
td small{display:block;font-size:12px;color:#4A5563}
.pill{padding:3px 10px;border-radius:999px;font-size:12px;font-weight:600;white-space:nowrap}
.urgente{background:#8E1B1B;color:#fff}.alta{background:#C2410C;color:#fff}.media{background:#FDE8B0;color:#5A3B00}.baixa{background:#E1E5DF;color:#17202A}
.rev{border:1px solid #E1E5DF;border-radius:10px;padding:14px;background:#FAFBF9}
.rev b{display:block;font-size:12px;color:#4A5563}.rev p{font-size:14px;margin:6px 0 0;overflow-wrap:anywhere}
.bar{height:10px;background:#E1E5DF;border-radius:6px;margin-top:4px}.bar i{display:block;height:10px;background:#0F6B63;border-radius:6px}
.hl td:first-child{color:#4A5563;width:38%}.hl table{min-width:0}.empty{color:#4A5563;padding:18px}
"""


def load_report() -> dict:
    try:
        return json.loads((settings.OUTPUT_DIR / "relatorio_execucao.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - sem relatório ainda: o painel mostra "—"
        return {}


_ACENTO = {"crianca": "criança", "inundacao": "inundação"}


def _motivo(m: Optional[str]) -> str:
    if "audio_sem_transcricao" in (m or ""):
        return "áudio sem transcrição"
    out = []
    for part in (m or "").split(";"):
        if part.startswith("baixa_confianca"):
            try:
                out.append(f"confiança baixa ({float(part.split('(')[1].rstrip(')')) * 100:.0f}%)")
            except (IndexError, ValueError):
                out.append("confiança baixa")
        elif part:
            out.append({"fora_do_escopo": "fora do escopo", "audio_sem_transcricao": "áudio sem transcrição",
                        "sem_localizacao": "sem localização"}.get(part, part))
    return " · ".join(out) or "revisão"


def _kpi(label, value, sub):
    return (f'<div class="card kpi"><div class="l">{escape(label)}</div><div class="v">{escape(str(value))}</div>'
            f'<div class="s">{escape(sub)}</div></div>')


def render(store, report: Optional[dict] = None, refresh: bool = False) -> str:
    report = report if report is not None else load_report()
    s = report.get("resumo", {})
    events = report.get("eventos", [])
    occs = sorted(store.all_occurrences(), key=lambda o: (ORDEM.get(o["prioridade"], 9), -o["n_relatos"])) if store else []
    review = store.review_queue() if store else []
    no_portal = sum(1 for o in occs if o["ticket"])
    pii = store.conn.execute("SELECT COUNT(*) FROM relatos WHERE texto_mascarado LIKE '%[CPF]%' OR "
                             "texto_mascarado LIKE '%[TELEFONE]%' OR texto_mascarado LIKE '%[EMAIL]%'").fetchone()[0] if store else 0

    rows = ""
    for o in occs:
        _, reasons = priority.score(o["categoria"], store.representative_text(o["id"]))
        sinais = [_ACENTO.get(k, k) for k in (r.split("'")[1] for r in reasons if r.startswith("sinal:"))]
        notas = []
        if sinais:
            notas.append("Sinais: " + ", ".join(sinais))
        if o["n_relatos"] >= settings.DEDUP_ESCALATE_AT:
            notas.append(f"Prioridade subiu: {o['n_relatos']} moradores relataram")
        nota = f"<small>{escape(' · '.join(notas))}</small>" if notas else ""
        chamado = escape(o["ticket"]) if o["ticket"] else "<small>aguardando portal</small>"
        rows += (f'<tr><td><span class="pill {escape(o["prioridade"])}">{ROTULO.get(o["prioridade"], o["prioridade"])}</span></td>'
                 f'<td>{escape(CAT.get(o["categoria"], o["categoria"]))}</td>'
                 f'<td>{escape(o["endereco"] or "sem endereço")}{nota}</td><td>{o["n_relatos"]}</td><td>{chamado}</td></tr>')
    tabela = (f'<div class="scroll"><table><tr><th>Prioridade</th><th>Categoria</th><th>Local</th><th>Relatos</th>'
              f'<th>Chamado</th></tr>{rows}</table></div>') if occs else '<div class="empty">Nenhuma ocorrência ainda. Rode <code>python main.py --demo</code>.</div>'

    fila = "".join(f'<div class="rev"><b>{escape(r["protocolo"])} · {escape(_motivo(r["motivo_revisao"]))}</b>'
                   f'<p>{escape(r["texto_mascarado"] or "(sem texto: relato só em áudio)")}</p></div>' for r in review)
    fila = fila or '<div class="empty">Nada aguardando revisão.</div>'

    cats = {}
    for o in occs:
        cats[o["categoria"]] = cats.get(o["categoria"], 0) + 1
    top = max(cats.values()) if cats else 1
    barras = "".join(f'<div><div style="display:flex;justify-content:space-between"><span>{escape(CAT.get(c, c))}</span><b>{n}</b></div>'
                     f'<div class="bar"><i style="width:{n / top * 100:.0f}%"></i></div></div>'
                     for c, n in sorted(cats.items(), key=lambda x: -x[1])) or '<div class="empty">Sem dados.</div>'

    motivos_rej = sorted({(e.get("detalhe") or "").split(":")[0] for e in events if e.get("resultado") == "rejeitado"})
    saude = [("Portal do órgão (RPA)", f"{no_portal} de {len(occs)} chamados registrados"),
             ("Modo do robô", MODO.get(s.get("modo_robo", ""), s.get("modo_robo", "—"))),
             ("Entradas rejeitadas", f"{s.get('rejeitado', 0)}" + (": " + "; ".join(motivos_rej) if motivos_rej else "")),
             ("Dados pessoais", f"{pii} relato(s) com CPF, telefone ou e-mail mascarados"),
             ("Idempotência", f"{s.get('ja_processado', 0)} relato(s) repetido(s) ignorado(s) na última execução")]
    saude_html = "".join(f"<tr><td>{escape(k)}</td><td>{escape(v)}</td></tr>" for k, v in saude)

    dur = f"{s['duracao_s']:.1f} s".replace(".", ",") if "duracao_s" in s else "—"
    kpis = "".join([
        _kpi("Relatos lidos", s.get("arquivos_lidos", "—"), f"última execução · {s.get('rejeitado', 0)} rejeitados"),
        _kpi("Ocorrências abertas", len(occs), f"{s.get('agrupado_em_existente', 0)} relatos agrupados na última execução"),
        _kpi("Registradas no portal", f"{no_portal} de {len(occs)}", "chamados criados pelo robô"),
        _kpi("Revisão humana", len(review), "aguardam um atendente"),
        _kpi("Duração da execução", dur, "execução automática")])
    meta = '<meta http-equiv="refresh" content="10">' if refresh else ""
    return (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'{meta}<title>Bairro em Dia — Painel do gestor</title>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Space+Grotesk:wght@500;700&display=swap">'
            f'<style>{_CSS}</style></head><body><div class="w">'
            '<div class="top"><div><div class="eyebrow">Bairro em Dia</div><h1>Painel do gestor</h1></div>'
            f'<div class="meta"><span class="tag">Dados sintéticos</span><span>Gerado em {datetime.now():%d/%m/%Y %H:%M}</span></div></div>'
            f'<div class="kpis">{kpis}</div>'
            '<div class="row"><div class="card" style="flex:1 1 640px;min-width:0;overflow:hidden"><div class="pad" style="padding-bottom:8px">'
            '<h2>Ocorrências abertas</h2><div class="sub">Ordenadas por prioridade. Relatos do mesmo problema (até 80 m) viram uma só ocorrência.</div></div>'
            f'{tabela}</div>'
            '<div class="card pad" style="flex:1 1 320px;min-width:0;display:flex;flex-direction:column;gap:14px"><div>'
            '<h2>Fila de revisão humana</h2><div class="sub">O que o robô não resolve com segurança vem para cá.</div></div>'
            f'{fila}</div></div>'
            '<div class="row"><div class="card pad" style="flex:1 1 360px"><h2 style="margin-bottom:14px">Ocorrências por categoria</h2>'
            f'<div style="display:flex;flex-direction:column;gap:12px;font-size:14px">{barras}</div></div>'
            f'<div class="card pad hl" style="flex:1 1 360px"><h2 style="margin-bottom:8px">Saúde do robô</h2><table>{saude_html}</table></div></div>'
            '</div></body></html>')
