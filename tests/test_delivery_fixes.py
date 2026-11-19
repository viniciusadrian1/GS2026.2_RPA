import json
import os
import subprocess
import sys

import numpy as np
import pytest

from config import settings
from scripts.evaluate import automatic_mask
from src import assistant
from src.pipeline import Pipeline
from src.protocol import Store


def test_portal_persists_across_processes(tmp_path):
    code = """
import sys, json
from pathlib import Path
from config import settings
settings.OUTPUT_DIR = Path(sys.argv[1])
from mock_portal.app import _create, list_tickets
payload = dict(protocolo='OC-TEST', categoria='buraco', prioridade='media', endereco='Rua A', descricao='Buraco')
ticket = _create(payload)
print(json.dumps({'ticket':ticket, 'all':list_tickets()}))
"""
    env = dict(os.environ, PYTHON_DOTENV_DISABLED="1", GROQ_API_KEY="")
    def run():
        return json.loads(subprocess.check_output([sys.executable, "-c", code, str(tmp_path)],
                                                 env=env, text=True))
    first, second = run(), run()
    assert first == second
    assert len(second['all']) == 1
    assert (tmp_path / 'portal.db').exists()


@pytest.mark.parametrize('review', [False, True])
def test_receipt_recovers_without_original_input(tmp_path, monkeypatch, review):
    monkeypatch.setattr(settings, 'OUTPUT_DIR', tmp_path / 'out')
    monkeypatch.setattr(settings, 'GROQ_API_KEY', '')
    inbox = tmp_path / 'inbox'
    inbox.mkdir()
    file = inbox / 'a.json'
    file.write_text(json.dumps(dict(id='a', texto='Buraco enorme na Rua A', lat=-23.5, lon=-46.6)))
    class FixedClassifier:
        def predict(self, text): return ('outros', .9, 'teste') if review else ('buraco', .9, 'teste')
    store = Store(tmp_path / 'store.db')
    try:
        with monkeypatch.context() as failure:
            def unavailable(text): raise FileNotFoundError('base ausente')
            failure.setattr(assistant, 'answer', unavailable)
            first, _ = Pipeline(store, FixedClassifier()).run(inbox)
        assert first['comprovante_pendente'] == 1
        assert first['revisao_humana' if review else 'ocorrencia_nova'] == 1
        assert 'erro_inesperado' not in first
        file.unlink()
        second, _ = Pipeline(store, FixedClassifier()).run(inbox)
        assert second['comprovante_gerado'] == 1
        receipts = list((settings.OUTPUT_DIR / 'comprovantes').glob('*.txt'))
        assert len(receipts) == 1 and 'PROTOCOLO:' in receipts[0].read_text(encoding='utf8')
        third, _ = Pipeline(store, FixedClassifier()).run(inbox)
        assert 'comprovante_gerado' not in third
        assert len(store.all_reports()) == 1
    finally:
        store.close()


def test_review_metric_includes_out_of_scope():
    mask = automatic_mask(['buraco', 'outros', 'lixo'], np.array([.9, .99, .4]), .55)
    assert mask.tolist() == [True, False, False]


def test_final_set_review_count():
    import pandas as pd
    from src.classifier import train
    from src.nlp import normalize
    model = train(save_to=None)
    data = pd.read_csv(settings.DATA_DIR / 'synthetic' / 'teste_final.csv')
    probabilities = model.predict_proba(data.texto.map(normalize))
    mask = automatic_mask(model.classes_[probabilities.argmax(axis=1)], probabilities.max(axis=1), .55)
    assert len(data) == 40 and int((~mask).sum()) == 16
