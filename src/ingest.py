"""Entrada: lê relatos da caixa (inbox) e valida. Dado inválido vira erro explícito, nunca exceção solta."""
import json
from datetime import datetime
from pathlib import Path

from src.schemas import Attachment, Report


class InvalidReport(ValueError):
    pass


def parse_report(raw: dict) -> Report:
    if not isinstance(raw, dict):
        raise InvalidReport("conteúdo não é um objeto JSON")
    rid = str(raw.get("id", "")).strip()
    if not rid:
        raise InvalidReport("campo 'id' ausente")

    atts = []
    for a in raw.get("anexos") or []:
        if not isinstance(a, dict) or a.get("tipo") not in ("foto", "audio") or not a.get("arquivo"):
            raise InvalidReport("anexo mal formado (esperado {tipo: foto|audio, arquivo})")
        atts.append(Attachment(kind=a["tipo"], path=str(a["arquivo"])))

    text = raw.get("texto")
    if text is not None and not isinstance(text, str):
        raise InvalidReport("'texto' deve ser string")
    text = (text or "").strip()
    has_audio = any(a.kind == "audio" for a in atts)
    if len(text) < 10 and not has_audio:
        raise InvalidReport("texto ausente/curto demais e sem áudio para transcrever")

    lat, lon = raw.get("lat"), raw.get("lon")
    if (lat is None) != (lon is None):
        raise InvalidReport("lat e lon devem vir juntos")
    if lat is not None:
        try:
            lat, lon = float(lat), float(lon)
        except (TypeError, ValueError):
            raise InvalidReport("lat/lon não numéricos")
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise InvalidReport(f"coordenadas fora do intervalo válido: {lat}, {lon}")
    address = (raw.get("endereco") or "").strip() or None
    if lat is None and not address and not text:
        raise InvalidReport("sem localização")

    created = raw.get("data") or datetime.now().isoformat(timespec="seconds")
    try:
        datetime.fromisoformat(str(created))
    except ValueError:
        raise InvalidReport(f"data inválida: {created!r}")

    return Report(id=rid, text=text, created_at=str(created), lat=lat, lon=lon,
                  address=address, reporter_ref=str(raw.get("morador_ref", "anonimo")),
                  attachments=atts)


def load_file(path: Path) -> Report:
    """Levanta InvalidReport (ou OSError/JSONDecodeError convertidos) com mensagem clara."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise InvalidReport("arquivo ausente")
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise InvalidReport(f"JSON corrompido: {exc}")
    return parse_report(raw)
