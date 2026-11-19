"""Portal do gestor SIMULADO (só para o protótipo). Rodar: uvicorn mock_portal.app:app --port 8000"""
from html import escape

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="Portal do Gestor (simulado)")
_TICKETS: dict = {}

_FORM = """<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Novo chamado</title>
<body><h1>Portal do Gestor - Novo chamado</h1>
<form method="post" action="/novo">
<label>Protocolo <input id="protocolo" name="protocolo" required></label><br>
<label>Categoria <select id="categoria" name="categoria">
 <option>buraco</option><option>iluminacao</option><option>lixo</option><option>ruido</option><option>outros</option>
</select></label><br>
<label>Prioridade <select id="prioridade" name="prioridade">
 <option>baixa</option><option>media</option><option>alta</option><option>urgente</option></select></label><br>
<label>Endereço <input id="endereco" name="endereco"></label><br>
<label>Descrição <textarea id="descricao" name="descricao"></textarea></label><br>
<button id="enviar" type="submit">Registrar</button></form></body></html>"""


class Chamado(BaseModel):
    protocolo: str
    categoria: str
    prioridade: str
    endereco: str = ""
    descricao: str = ""


def _create(data: dict) -> dict:
    # Idempotência: mesmo protocolo devolve o mesmo chamado (não duplica).
    if data["protocolo"] not in _TICKETS:
        _TICKETS[data["protocolo"]] = {"ticket": f"TK-{len(_TICKETS) + 1:05d}", **data}
    return _TICKETS[data["protocolo"]]


@app.get("/", response_class=HTMLResponse)
def home():
    return ('<!doctype html><meta charset="utf-8"><title>Portal do Gestor</title>'
            "<h1>Portal do Gestor (simulado)</h1><ul>"
            '<li><a href="/gestor">Painel do gestor (Bairro em Dia)</a></li>'
            '<li><a href="/painel">Chamados registrados pelo robô (sistema do órgão)</a></li>'
            '<li><a href="/novo">Formulário de novo chamado</a></li>'
            '<li><a href="/chamados">Chamados em JSON</a></li></ul>')


@app.get("/painel", response_class=HTMLResponse)
def painel():
    rows = "".join(
        f"<tr><td>{escape(t['ticket'])}</td><td>{escape(t['protocolo'])}</td><td>{escape(t['categoria'])}</td>"
        f"<td>{escape(t['prioridade'])}</td><td>{escape(t.get('endereco') or '')}</td>"
        f"<td>{escape(t.get('descricao') or '')}</td></tr>" for t in _TICKETS.values())
    vazio = "" if _TICKETS else "<p>Nenhum chamado ainda. Rode o robô (python main.py) com o portal no ar.</p>"
    return ('<!doctype html><meta charset="utf-8"><title>Painel</title><h1>Chamados registrados</h1>' + vazio +
            '<table border=1 cellpadding=6><tr><th>Chamado</th><th>Protocolo</th><th>Categoria</th>'
            f"<th>Prioridade</th><th>Endereço</th><th>Descrição</th></tr>{rows}</table>")


@app.get("/gestor", response_class=HTMLResponse)
def gestor():
    """Painel do gestor do Bairro em Dia, lendo o banco real (atualiza sozinho a cada 10 s)."""
    from config import settings
    from src import dashboard
    from src.protocol import Store

    if not settings.DB_PATH.exists():
        return dashboard.render(None, refresh=True)
    store = Store()
    try:
        return dashboard.render(store, refresh=True)
    finally:
        store.close()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/novo", response_class=HTMLResponse)
def form():
    return _FORM


@app.post("/novo", response_class=HTMLResponse)
def submit(protocolo: str = Form(...), categoria: str = Form(...), prioridade: str = Form(...),
           endereco: str = Form(""), descricao: str = Form("")):
    t = _create(dict(protocolo=protocolo, categoria=categoria, prioridade=prioridade,
                     endereco=endereco, descricao=descricao))
    return f'<!doctype html><meta charset="utf-8"><body>Chamado registrado: <span id="ticket">{t["ticket"]}</span></body>'


@app.post("/api/chamados")
def api_submit(c: Chamado):
    return _create(c.model_dump())


@app.get("/chamados")
def list_tickets():
    return list(_TICKETS.values())
