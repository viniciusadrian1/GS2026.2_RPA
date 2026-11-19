"""Teste do áudio. Rode na raiz do projeto, com o .venv ativo."""
import sqlite3
from pathlib import Path

from config import settings
from src.attachments import transcribe_audio

arquivo = Path("data/inbox/anexos/audio_conversa.mp3")
print("ENABLE_ASR =", settings.ENABLE_ASR)
print("Transcrição:", transcribe_audio(arquivo))

if settings.DB_PATH.exists():
    con = sqlite3.connect(settings.DB_PATH)
    for r in con.execute("SELECT protocolo, categoria, ROUND(confianca,2), status, motivo_revisao, "
                         "texto_mascarado FROM relatos WHERE relato_id='r012'"):
        print("No banco:", r)