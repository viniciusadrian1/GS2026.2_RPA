"""Logger com arquivo em UTF-8 explícito (evita o bug de encoding do Windows)."""
import logging
import sys

from config.settings import OUTPUT_DIR

_FMT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def setup_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if getattr(root, "_bed_configured", False):
        return
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    root.setLevel(level)
    file_h = logging.FileHandler(OUTPUT_DIR / "execucao.log", encoding="utf-8")
    console = logging.StreamHandler(sys.stdout)
    for h in (file_h, console):
        h.setFormatter(logging.Formatter(_FMT))
        root.addHandler(h)
    root._bed_configured = True  # type: ignore[attr-defined]


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
