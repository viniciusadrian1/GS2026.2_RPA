"""Testes automatizados (pytest). Rodar: python -m pytest -q"""
import json
import time

import pandas as pd
import pytest
from sklearn.metrics import accuracy_score

from config import settings
from src import assistant, attachments, nlp, priority
from src.classifier import Classifier, keyword_fallback, train
from src.dedup import haversine_m, same_place
from src.ingest import InvalidReport, load_file, parse_report
from src.pipeline import Pipeline
from src.protocol import Store, make_protocol
from src.utils.resilience import TransientError, safe_step


@pytest.fixture(autouse=True)
def fast_env(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "RETRY_BASE_DELAY_S", 0.0)
    monkeypatch.setattr(settings, "OUTPUT_DIR", tmp_path / "out")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")


# ---------------- entrada / validação ----------------
def test_ingest_valid_and_invalid(tmp_path):
    ok = parse_report({"id": "a", "texto": "Buraco grande na Rua A", "lat": -23.5, "lon": -46.6})
    assert ok.lat == -23.5
    for bad in [{"texto": "sem id aqui ok"}, {"id": "x"}, {"id": "x", "texto": "texto longo o bastante", "lat": 999, "lon": 0},
                {"id": "x", "texto": "texto longo o bastante", "lat": 1}, {"id": "x", "texto": 123}]:
        with pytest.raises(InvalidReport):
            parse_report(bad)
    p = tmp_path / "corrompido.json"
    p.write_text('{"id": "x", "texto": "abc', encoding="utf-8")
    with pytest.raises(InvalidReport):
        load_file(p)
    with pytest.raises(InvalidReport):
        load_file(tmp_path / "nao_existe.json")


def test_audio_only_is_accepted():
    r = parse_report({"id": "a", "lat": 1, "lon": 1, "anexos": [{"tipo": "audio", "arquivo": "x.wav"}]})
    assert r.text == "" and r.attachments[0].kind == "audio"


# ---------------- NLP / LGPD ----------------
def test_mask_pii():
    t = nlp.mask_pii("CPF 123.456.789-09, tel (11) 98888-7777, joana@exemplo.com")
    assert "123.456" not in t and "98888" not in t and "@" not in t
    assert "[CPF]" in t and "[EMAIL]" in t and "[TELEFONE]" in t


def test_extract_address_and_normalize():
    assert nlp.extract_address("Buraco na Rua das Acácias, Jardim Aurora.") == "Rua das Acácias"
    assert nlp.extract_address("sem endereço nenhum") is None
    assert nlp.normalize("Lâmpada QUEIMADA!!") == "lampada queimada"


# ---------------- regras ----------------
def test_priority_rules():
    assert priority.prioritize("iluminacao", "poste apagado com fio exposto perto da escola")[0] == "urgente"
    assert priority.prioritize("lixo", "lixo na calçada")[0] == "baixa"
    assert priority.escalate("urgente") == "urgente"


def test_dedup_geo_and_address():
    assert haversine_m(-23.5505, -46.6333, -23.5507, -46.6333) < 30
    assert same_place(-23.5505, -46.6333, None, -23.5507, -46.6333, None, 80)
    assert not same_place(-23.5505, -46.6333, None, -23.56, -46.64, None, 80)
    assert same_place(None, None, "Rua das Acácias", None, None, "rua das acacias", 80)


# ---------------- persistência / idempotência ----------------
def test_protocol_is_idempotent_and_groups(tmp_path):
    assert make_protocol("r1", "buraco") == make_protocol("r1", "buraco")
    assert make_protocol("r1", "buraco") != make_protocol("r2", "buraco")
    st = Store(tmp_path / "t.db")
    row = dict(protocolo="BED-AAAA", relato_id="r1", ocorrencia_id=None, categoria="buraco", confianca=.9, origem="ml",
               prioridade="media", status="em_andamento", motivo_revisao=None, endereco="Rua A", lat=1.0, lon=1.0,
               texto_mascarado="x", criado_em="2026-01-01")
    assert st.insert_report(row) is True
    assert st.insert_report(row) is False  # não duplica
    oid = st.create_occurrence("BED-AAAA", "buraco", "media", 1.0, 1.0, "Rua A", "2026-01-01")
    assert st.find_occurrence("buraco", 1.00001, 1.0, None)["id"] == oid
    st.add_to_occurrence(oid)
    assert st.add_to_occurrence(oid)["prioridade"] == "alta"  # 3º relato escala


# ---------------- resiliência ----------------
def test_safe_step_retry_then_success_and_fallback():
    calls = {"n": 0}

    @safe_step("t", retries=3, base_delay=0)
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise TransientError("fora do ar")
        return "ok"

    assert flaky() == "ok" and calls["n"] == 3

    calls["n"] = 0

    @safe_step("t", retries=3, base_delay=0, fallback=lambda: "seguro")
    def bug():
        calls["n"] += 1
        raise ValueError("dado inválido")

    assert bug() == "seguro" and calls["n"] == 1  # erro não transitório não é repetido

    @safe_step("t", retries=2, base_delay=0, fallback=lambda: "seguro")
    def always_down():
        raise TransientError("x")

    assert always_down() == "seguro"


# ---------------- ML ----------------
def test_classifier_final_set_and_fallback():
    model = train(save_to=None)
    d = pd.read_csv(settings.DATA_DIR / "synthetic" / "teste_final.csv", encoding="utf-8")
    pred = model.predict(d["texto"].map(nlp.normalize))
    assert accuracy_score(d["categoria"], pred) >= 0.85
    assert keyword_fallback("poste apagado")[0] == "iluminacao"
    c = Classifier(model=model)
    c.model = None  # simula modelo indisponível
    assert c.predict("buraco na rua")[2] == "regras"


# ---------------- assistente ----------------
def test_assistant_retrieval_and_llm_fallback(monkeypatch):
    assert assistant.answer("o poste da minha rua está apagado")["fonte"] == "iluminacao"
    assert assistant.answer("xyzzy qwerty")["fonte"] is None

    class FakeResp:
        status_code = 200
        def raise_for_status(self): pass
        def json(self): return {"choices": [{"message": {"content": ""}}]}  # resposta vazia

    monkeypatch.setattr(settings, "GROQ_API_KEY", "chave-falsa")
    monkeypatch.setattr(assistant.requests, "post", lambda *a, **k: FakeResp())
    res = assistant.answer("buraco na rua")
    assert res["llm"] is False and "Zeladoria" in res["resposta"]  # caminho seguro


# ---------------- anexos ----------------
def test_exif_removed(tmp_path):
    from PIL import Image
    src = tmp_path / "f.jpg"
    exif = Image.Exif()
    exif[0x010F] = "Camera"
    Image.new("RGB", (8, 8)).save(src, exif=exif)
    assert dict(Image.open(src).getexif())
    out = attachments.sanitize_image(src, tmp_path / "limpo")
    assert dict(Image.open(out).getexif()) == {}


# ---------------- ponta a ponta ----------------
class FakeRobot:
    mode = "fake"
    def __init__(self, down=False): self.n, self.down = 0, down
    def register(self, payload):
        if self.down:
            raise TransientError("portal fora do ar")
        self.n += 1
        return f"TK-{self.n:05d}"


def _run(tmp_path, robot):
    store = Store(tmp_path / "e2e.db")
    summary, events = Pipeline(store, Classifier(), robot).run(settings.INBOX_DIR)
    return store, summary


def test_end_to_end_and_idempotent_rerun(tmp_path):
    store, s = _run(tmp_path, FakeRobot())
    assert s["rejeitado"] == 3 and s["ja_processado"] == 1  # corrompido, sem texto, coordenada inválida; duplicata
    assert s["agrupado_em_existente"] == 2 and s["portal_registrado"] == s["ocorrencia_nova"]
    assert s["revisao_humana"] >= 2
    assert not any("123.456" in (r["texto_mascarado"] or "") for r in store.review_queue())  # PII mascarada
    # reexecução: nada novo é criado
    _, s2 = _run(tmp_path, FakeRobot())
    assert s2.get("ocorrencia_nova", 0) == 0 and s2["ja_processado"] == 12


def test_portal_down_keeps_pending_then_recovers(tmp_path):
    t0 = time.time()
    store, s = _run(tmp_path, FakeRobot(down=True))
    assert s["portal_pendente"] == s["ocorrencia_nova"] and s.get("portal_registrado", 0) == 0
    assert time.time() - t0 < 5  # disjuntor: não martela o portal fora do ar
    _, s2 = _run(tmp_path, FakeRobot())
    assert s2["portal_registrado"] == s["portal_pendente"]


# ---------------- painel do gestor ----------------
def test_dashboard_real_data_escaping_and_no_buttons(tmp_path):
    from src import dashboard
    store, s = _run(tmp_path, FakeRobot())
    store.insert_report(dict(protocolo="BED-XSS", relato_id="x", ocorrencia_id=None, categoria="outros", confianca=0.1,
                             origem="ml", prioridade="baixa", status="em_revisao", motivo_revisao="fora_do_escopo",
                             endereco=None, lat=None, lon=None, texto_mascarado="<script>alert(1)</script>",
                             criado_em="2026-01-01"))
    html = dashboard.render(store, {"resumo": s, "eventos": []})
    assert "Painel do gestor" in html and "Urgente" in html and "TK-00001" in html
    assert "<script>alert(1)" not in html and "&lt;script&gt;" in html  # nada do usuário vira HTML
    assert "criança" in html and "Confirmar" not in html


def test_dashboard_empty_state(tmp_path):
    from src import dashboard
    assert "Nenhuma ocorrência ainda" in dashboard.render(Store(tmp_path / "vazio.db"), {})
    assert "Painel do gestor" in dashboard.render(None, {})
