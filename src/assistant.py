"""Assistente: recupera a resposta numa base de serviços (TF-IDF). LLM (Groq) é opcional e só reescreve
o que foi recuperado; resposta vazia/inválida ou erro -> resposta determinística da base."""
import json
from functools import lru_cache

import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import settings
from src.nlp import mask_pii, normalize
from src.utils.logger import get_logger
from src.utils.resilience import TransientError, safe_step

log = get_logger("assistente")
MIN_SIM = 0.08
DISCLAIMER = "Em risco imediato, ligue 190, 192, 193 ou 199."


@lru_cache(maxsize=1)
def _kb():
    items = json.loads(settings.KNOWLEDGE_PATH.read_text(encoding="utf-8"))
    docs = [normalize(f'{i["titulo"]} {i["palavras_chave"]}') for i in items]
    vec = TfidfVectorizer(ngram_range=(1, 2)).fit(docs)
    return items, vec, vec.transform(docs)


def _template(item: dict) -> str:
    steps = "\n".join(f"{n}. {s}" for n, s in enumerate(item["como_solicitar"], 1))
    return (f'{item["titulo"]} — órgão responsável: {item["orgao"]}.\n'
            f'Como pedir:\n{steps}\nPrazo de referência: {item["prazo_ref"]}.')


def _llm_rewrite(question: str, item: dict) -> str:
    if not settings.GROQ_API_KEY:
        raise RuntimeError("sem GROQ_API_KEY")
    try:
        r = requests.post(
            settings.GROQ_URL, timeout=settings.HTTP_TIMEOUT_S * 2,
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            json={"model": settings.GROQ_MODEL, "temperature": 0.2, "messages": [
                {"role": "system", "content": "Você orienta moradores. Responda em português, curto e "
                 "SOMENTE com base no contexto. Se faltar informação, diga que não sabe."},
                {"role": "user", "content": f"Contexto:\n{_template(item)}\n\nPergunta: {mask_pii(question)}"}]})
    except requests.exceptions.RequestException as exc:
        raise TransientError(exc.__class__.__name__) from exc
    if r.status_code >= 500:
        raise TransientError(f"LLM {r.status_code}")
    r.raise_for_status()
    text = (r.json()["choices"][0]["message"].get("content") or "").strip()
    if len(text) < 20:  # resposta vazia/inválida
        raise ValueError("resposta do LLM vazia ou curta")
    return text


def answer(question: str) -> dict:
    items, vec, mat = _kb()
    sims = cosine_similarity(vec.transform([normalize(question)]), mat)[0]
    best = int(sims.argmax())
    if sims[best] < MIN_SIM:
        return {"resposta": "Não encontrei essa informação. Procure o canal oficial de atendimento da sua "
                            f"prefeitura. {DISCLAIMER}", "fonte": None, "llm": False, "similaridade": float(sims[best])}
    item = items[best]
    base = _template(item)
    text, used_llm = base, False
    if settings.GROQ_API_KEY:
        out = safe_step("llm", retries=2, fallback=lambda *a, **k: None)(_llm_rewrite)(question, item)
        if out:
            text, used_llm = out, True
    return {"resposta": f"{text}\n{DISCLAIMER}", "fonte": item["id"], "llm": used_llm,
            "similaridade": float(sims[best])}
