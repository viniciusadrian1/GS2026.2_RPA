"""Anexos: foto (remove EXIF/GPS antes de guardar) e áudio (transcrição local opcional)."""
from pathlib import Path

from config import settings
from src.utils.logger import get_logger

log = get_logger("anexos")


def sanitize_image(src: Path, dst_dir: Path) -> Path:
    """Reescreve a imagem só com os pixels: EXIF (incl. GPS) não é copiado."""
    from PIL import Image  # import tardio: dependência só necessária com foto

    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / Path(src).name
    with Image.open(src) as img:
        clean = Image.frombytes(img.mode, img.size, img.tobytes())  # só pixels, sem metadados
        clean.save(dst)
    return dst


def transcribe_audio(path: Path) -> str:
    """Whisper local (faster-whisper). Levanta exceção se desligado/indisponível -> revisão humana."""
    if not settings.ENABLE_ASR:
        raise RuntimeError("ASR desativado (ENABLE_ASR=0)")
    if not Path(path).exists():
        raise FileNotFoundError(f"áudio ausente: {path}")
    from faster_whisper import WhisperModel  # opcional; ImportError cai no caminho seguro

    model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(path), language="pt")
    text = " ".join(s.text.strip() for s in segments).strip()
    if not text:
        raise ValueError("transcrição vazia")
    return text
