"""Regras de prioridade (explicáveis): categoria base + sinais de risco no texto."""
from src.nlp import normalize

_BASE = {"buraco": 2, "iluminacao": 2, "lixo": 1, "ruido": 1, "outros": 0}
_RISK = {
    "acidente": 2, "caiu": 2, "ferid": 2, "fio exposto": 3, "choque": 2, "curto circuito": 2,
    "crianca": 1, "escola": 1, "hospital": 1, "idoso": 1, "cadeirante": 1,
    "esgoto": 1, "rato": 1, "inundacao": 2, "madrugada": 1, "assalto": 1, "perigoso": 1,
}
LEVELS = ["baixa", "media", "alta", "urgente"]


def score(category: str, text: str):
    t = normalize(text)
    s = _BASE.get(category, 0)
    reasons = [f"base:{category}={s}"]
    for key, w in _RISK.items():
        if key in t:
            s += w
            reasons.append(f"sinal:'{key}'+{w}")
    return s, reasons


def level_from_score(s: int) -> str:
    return LEVELS[0 if s <= 1 else 1 if s <= 3 else 2 if s <= 4 else 3]


def prioritize(category: str, text: str):
    s, reasons = score(category, text)
    return level_from_score(s), reasons


def escalate(level: str) -> str:
    return LEVELS[min(LEVELS.index(level) + 1, len(LEVELS) - 1)]
