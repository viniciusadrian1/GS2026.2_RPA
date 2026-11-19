"""Persistência (SQLite) + protocolos idempotentes + ocorrências (relatos agrupados)."""
import hashlib
import sqlite3
from pathlib import Path
from typing import Optional

from config import settings
from src.dedup import same_place
from src.priority import escalate

_SCHEMA = """
CREATE TABLE IF NOT EXISTS ocorrencias (
  id TEXT PRIMARY KEY, categoria TEXT, prioridade TEXT, lat REAL, lon REAL, endereco TEXT,
  n_relatos INTEGER DEFAULT 1, ticket TEXT, status TEXT, criado_em TEXT);
CREATE TABLE IF NOT EXISTS relatos (
  protocolo TEXT PRIMARY KEY, relato_id TEXT, ocorrencia_id TEXT, categoria TEXT, confianca REAL,
  origem TEXT, prioridade TEXT, status TEXT, motivo_revisao TEXT, endereco TEXT, lat REAL, lon REAL,
  texto_mascarado TEXT, criado_em TEXT);
"""


def make_protocol(report_id: str, text_norm: str) -> str:
    """Determinístico: o mesmo relato reprocessado gera o mesmo protocolo (idempotência)."""
    h = hashlib.sha256(f"{report_id}|{text_norm}".encode("utf-8")).hexdigest()
    return "BED-" + h[:10].upper()


class Store:
    def __init__(self, path: Path = settings.DB_PATH):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def close(self):
        self.conn.close()

    # --- relatos -----------------------------------------------------------
    def get_report(self, protocolo: str) -> Optional[dict]:
        r = self.conn.execute("SELECT * FROM relatos WHERE protocolo=?", (protocolo,)).fetchone()
        return dict(r) if r else None

    def insert_report(self, row: dict) -> bool:
        """False se o protocolo já existia (relato já processado)."""
        cols = ",".join(row)
        qs = ",".join("?" * len(row))
        cur = self.conn.execute(f"INSERT OR IGNORE INTO relatos ({cols}) VALUES ({qs})", tuple(row.values()))
        self.conn.commit()
        return cur.rowcount == 1

    # --- ocorrências -------------------------------------------------------
    def find_occurrence(self, categoria, lat, lon, endereco) -> Optional[dict]:
        rows = self.conn.execute("SELECT * FROM ocorrencias WHERE categoria=?", (categoria,)).fetchall()
        for r in rows:
            if same_place(lat, lon, endereco, r["lat"], r["lon"], r["endereco"], settings.DEDUP_RADIUS_M):
                return dict(r)
        return None

    def create_occurrence(self, protocolo, categoria, prioridade, lat, lon, endereco, criado_em) -> str:
        oid = "OC-" + protocolo.split("-")[1][:8]
        self.conn.execute(
            "INSERT INTO ocorrencias (id,categoria,prioridade,lat,lon,endereco,n_relatos,ticket,status,criado_em)"
            " VALUES (?,?,?,?,?,?,1,NULL,'aguardando_portal',?)",
            (oid, categoria, prioridade, lat, lon, endereco, criado_em))
        self.conn.commit()
        return oid

    def add_to_occurrence(self, oid: str) -> dict:
        """Soma um relato; a partir de N relatos a prioridade sobe um nível (mais gente afetada)."""
        occ = dict(self.conn.execute("SELECT * FROM ocorrencias WHERE id=?", (oid,)).fetchone())
        n = occ["n_relatos"] + 1
        prio = escalate(occ["prioridade"]) if n == settings.DEDUP_ESCALATE_AT else occ["prioridade"]
        self.conn.execute("UPDATE ocorrencias SET n_relatos=?, prioridade=? WHERE id=?", (n, prio, oid))
        self.conn.commit()
        occ.update(n_relatos=n, prioridade=prio)
        return occ

    def set_ticket(self, oid: str, ticket: str):
        self.conn.execute("UPDATE ocorrencias SET ticket=?, status='registrada' WHERE id=?", (ticket, oid))
        self.conn.commit()

    def pending_portal(self) -> list:
        rows = self.conn.execute("SELECT * FROM ocorrencias WHERE ticket IS NULL").fetchall()
        return [dict(r) for r in rows]

    def representative_text(self, oid: str) -> str:
        r = self.conn.execute("SELECT texto_mascarado FROM relatos WHERE ocorrencia_id=? ORDER BY criado_em LIMIT 1",
                              (oid,)).fetchone()
        return r["texto_mascarado"] if r else ""

    # --- consultas -----------------------------------------------------------
    def consultar(self, protocolo: str) -> Optional[dict]:
        """Visão do morador: andamento do protocolo."""
        rep = self.get_report(protocolo)
        if not rep:
            return None
        if rep["ocorrencia_id"]:
            occ = self.conn.execute("SELECT * FROM ocorrencias WHERE id=?", (rep["ocorrencia_id"],)).fetchone()
            rep["ocorrencia"] = dict(occ) if occ else None
        return rep

    def all_occurrences(self) -> list:
        return [dict(r) for r in self.conn.execute("SELECT * FROM ocorrencias ORDER BY criado_em")]

    def all_reports(self) -> list:
        return [dict(r) for r in self.conn.execute("SELECT * FROM relatos ORDER BY criado_em")]

    def review_queue(self) -> list:
        return [dict(r) for r in self.conn.execute("SELECT * FROM relatos WHERE status='em_revisao' ORDER BY criado_em")]
