"""Configuração central. Segredos vêm só de variáveis de ambiente / .env (nunca do código)."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # python-dotenv é conveniência, não requisito
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
INBOX_DIR = DATA_DIR / "inbox"
KNOWLEDGE_PATH = DATA_DIR / "knowledge" / "servicos.json"
TRAIN_CSV = DATA_DIR / "synthetic" / "treino.csv"
OUTPUT_DIR = BASE_DIR / "output"
MODEL_PATH = BASE_DIR / "models" / "classifier.joblib"
DB_PATH = OUTPUT_DIR / "protocolos.db"

PORTAL_URL = os.getenv("PORTAL_URL", "http://127.0.0.1:8000")
USE_PLAYWRIGHT = os.getenv("USE_PLAYWRIGHT", "1") == "1"
HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "1") == "1"      # 0 = você VÊ o navegador do robô trabalhando
SLOW_MO_MS = int(os.getenv("PLAYWRIGHT_SLOW_MO_MS", "0"))    # ex.: 700 deixa cada ação mais lenta (bom p/ vídeo)
ENABLE_ASR = os.getenv("ENABLE_ASR", "0") == "1"
HTTP_TIMEOUT_S = float(os.getenv("HTTP_TIMEOUT_S", "5"))
RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", "3"))
RETRY_BASE_DELAY_S = float(os.getenv("RETRY_BASE_DELAY", "1.0"))

CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.55"))
DEDUP_RADIUS_M = float(os.getenv("DEDUP_RADIUS_M", "80"))
DEDUP_ESCALATE_AT = 3  # nº de relatos que sobe a prioridade da ocorrência

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

CATEGORIES = ["buraco", "iluminacao", "lixo", "ruido", "outros"]
# Órgãos fictícios: o protótipo usa dados sintéticos e não se integra a nenhuma prefeitura real.
ORGAOS = {
    "buraco": "Zeladoria Viária",
    "iluminacao": "Iluminação Pública",
    "lixo": "Limpeza Urbana",
    "ruido": "Fiscalização de Ruído",
    "outros": "Triagem Manual",
}
