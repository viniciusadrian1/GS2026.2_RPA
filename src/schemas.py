from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Attachment:
    kind: str  # "foto" | "audio"
    path: str


@dataclass
class Report:
    """Relato do morador. `reporter_ref` é um apelido/hash, nunca dado pessoal real."""
    id: str
    text: str
    created_at: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    address: Optional[str] = None
    reporter_ref: str = "anonimo"
    attachments: list = field(default_factory=list)
    # preenchidos ao longo do pipeline
    text_norm: str = ""
    review_reasons: list = field(default_factory=list)
