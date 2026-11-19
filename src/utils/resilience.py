"""Isolamento de etapas: retry com backoff só para falha transitória + caminho seguro."""
import functools
import time

from config import settings
from src.utils.logger import get_logger

log = get_logger("resiliencia")


class TransientError(Exception):
    """Falha que vale a pena repetir (timeout, portal fora do ar, 5xx)."""


def safe_step(name, retries=None, base_delay=None, fallback=None):
    """Executa uma etapa sem derrubar o lote.

    - TransientError: repete com espera exponencial (1s, 2s, 4s...).
    - Qualquer outra exceção: repetir não adianta (dado inválido, bug) -> caminho seguro direto.
    - Esgotadas as tentativas: chama `fallback(*args, **kwargs)` se existir; senão devolve None.
    """
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            n = retries if retries is not None else settings.RETRY_ATTEMPTS
            delay = base_delay if base_delay is not None else settings.RETRY_BASE_DELAY_S
            for attempt in range(1, n + 1):
                try:
                    return fn(*args, **kwargs)
                except TransientError as exc:
                    log.warning("[%s] falha transitória (%d/%d): %s", name, attempt, n, exc)
                    if attempt < n:
                        time.sleep(delay * 2 ** (attempt - 1))
                except Exception as exc:  # noqa: BLE001 - fronteira de isolamento
                    log.error("[%s] erro não transitório, indo ao caminho seguro: %r", name, exc)
                    break
            log.error("[%s] caminho seguro acionado", name)
            return fallback(*args, **kwargs) if fallback else None
        return wrapper
    return deco
