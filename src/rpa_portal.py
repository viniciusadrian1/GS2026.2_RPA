"""Robô que registra a ocorrência no portal do gestor como um funcionário faria.
Primário: Playwright (navegador). Fallback: HTTP direto. Portal fora do ar -> TransientError (retry)."""
import requests

from config import settings
from src.utils.logger import get_logger
from src.utils.resilience import TransientError

log = get_logger("rpa")


class PortalRobot:
    def __init__(self, base_url: str = settings.PORTAL_URL, use_playwright: bool = settings.USE_PLAYWRIGHT):
        self.base_url = base_url.rstrip("/")
        self.use_playwright = use_playwright
        self._pw = None
        self._browser = None
        self.mode = "http"

    def __enter__(self):
        if self.use_playwright:
            try:
                from playwright.sync_api import sync_playwright
                self._pw = sync_playwright().start()
                self._browser = self._pw.chromium.launch(headless=settings.HEADLESS, slow_mo=settings.SLOW_MO_MS)
                self.mode = "playwright"
                log.info("Robô em modo navegador (Playwright)")
            except Exception as exc:  # noqa: BLE001 - navegador ausente não pode parar o robô
                log.warning("Playwright indisponível (%s); usando HTTP direto", str(exc)[:120])
                self._close()
        return self

    def __exit__(self, *exc):
        self._close()

    def _close(self):
        try:
            if self._browser:
                self._browser.close()
            if self._pw:
                self._pw.stop()
        except Exception:  # noqa: BLE001
            pass
        self._browser = self._pw = None

    def register(self, payload: dict) -> str:
        """Devolve o número do chamado. Idempotente: o portal reconhece `protocolo` repetido."""
        if self._browser:
            try:
                return self._register_browser(payload)
            except TransientError:
                raise
            except Exception as exc:  # noqa: BLE001
                log.warning("Falha no navegador (%s); tentando HTTP", str(exc)[:120])
        return self._register_http(payload)

    def _register_browser(self, p: dict) -> str:
        from playwright.sync_api import Error as PWError
        from playwright.sync_api import TimeoutError as PWTimeout

        page = self._browser.new_page()
        try:
            page.goto(f"{self.base_url}/novo", timeout=settings.HTTP_TIMEOUT_S * 1000)
            page.fill("#protocolo", p["protocolo"])
            page.select_option("#categoria", p["categoria"])
            page.select_option("#prioridade", p["prioridade"])
            page.fill("#endereco", p.get("endereco") or "não informado")
            page.fill("#descricao", p["descricao"])
            page.click("#enviar")
            page.wait_for_selector("#ticket", timeout=settings.HTTP_TIMEOUT_S * 1000)
            return page.inner_text("#ticket").strip()
        except PWTimeout as exc:
            raise TransientError(f"timeout no portal: {exc}") from exc
        except PWError as exc:
            if "ERR_CONNECTION" in str(exc) or "ERR_NAME" in str(exc):
                raise TransientError("portal fora do ar") from exc
            raise
        finally:
            page.close()

    def _register_http(self, p: dict) -> str:
        try:
            r = requests.post(f"{self.base_url}/api/chamados", json={
                "protocolo": p["protocolo"], "categoria": p["categoria"], "prioridade": p["prioridade"],
                "endereco": p.get("endereco") or "não informado", "descricao": p["descricao"]},
                timeout=settings.HTTP_TIMEOUT_S)
        except requests.exceptions.RequestException as exc:
            raise TransientError(f"portal inacessível: {exc.__class__.__name__}") from exc
        if r.status_code >= 500:
            raise TransientError(f"portal respondeu {r.status_code}")
        if r.status_code >= 400:
            raise ValueError(f"portal recusou o chamado ({r.status_code}): {r.text[:100]}")
        return r.json()["ticket"]
