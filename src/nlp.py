"""NLP leve e local: mascaramento de dados pessoais, normalização e extração de endereço."""
import re
import unicodedata
from typing import Optional

_PII_PATTERNS = [
    (re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), "[CPF]"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[EMAIL]"),
    (re.compile(r"(?:\+?55\s?)?\(?\b\d{2}\)?\s?9?\d{4}[-\s]?\d{4}\b"), "[TELEFONE]"),
]

_ADDR_RE = re.compile(
    r"\b(?:Rua|Avenida|Av\.|Travessa|Praça|Alameda)\s+"
    r"(?:(?:d[aeo]s?|de)\s+)?[A-ZÀ-Ú][\wà-úÀ-Ú]*"
    r"(?:\s+(?:(?:d[aeo]s?|de)\s+)?[A-ZÀ-Ú][\wà-úÀ-Ú]*){0,2}"
)


def mask_pii(text: str) -> str:
    """LGPD: mascara CPF, e-mail e telefone ANTES de qualquer outra etapa (e de qualquer API)."""
    for pattern, token in _PII_PATTERNS:
        text = pattern.sub(token, text)
    return text


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def normalize(text: str) -> str:
    text = strip_accents(text.lower())
    text = re.sub(r"[^a-z0-9\s\[\]]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_address(text: str) -> Optional[str]:
    m = _ADDR_RE.search(text)
    return m.group(0).strip() if m else None
