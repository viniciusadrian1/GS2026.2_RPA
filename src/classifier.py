"""Classificação de categoria: TF-IDF + Regressão Logística (medível, leve, explicável).
Caminho seguro: se o modelo não carrega, regras por palavra-chave."""
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

from config import settings
from src.nlp import normalize
from src.utils.logger import get_logger

log = get_logger("classificador")

_KEYWORDS = {
    "buraco": ["buraco", "cratera", "asfalto", "pista afundou"],
    "iluminacao": ["poste", "lampada", "iluminacao", "escur", "luminaria", "sem luz"],
    "lixo": ["lixo", "entulho", "cacamba", "coleta", "descarte"],
    "ruido": ["barulho", "som alto", "musica", "caixa de som", "festa", "obra fazendo"],
}


def build_pipeline() -> Pipeline:
    return Pipeline([
        # palavras (1-2) + caracteres (3-5): pegam variações como "buraco" ~ "esburacada"
        ("tfidf", FeatureUnion([
            ("palavras", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
            ("chars", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)),
        ])),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced", C=5.0)),
    ])


def train(csv_path=settings.TRAIN_CSV, save_to=settings.MODEL_PATH) -> Pipeline:
    df = pd.read_csv(csv_path, encoding="utf-8")
    model = build_pipeline().fit(df["texto"].map(normalize), df["categoria"])
    if save_to:
        save_to.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, save_to)
    log.info("Modelo treinado com %d amostras", len(df))
    return model


def load_or_train() -> Pipeline:
    try:
        return joblib.load(settings.MODEL_PATH)
    except Exception as exc:  # noqa: BLE001
        log.warning("Modelo indisponível (%r); treinando a partir do CSV sintético", exc)
        return train()


def keyword_fallback(text_norm: str):
    """Regras simples. Confiança propositalmente baixa -> tende a ir para revisão humana."""
    for cat, words in _KEYWORDS.items():
        if any(w in text_norm for w in words):
            return cat, 0.5
    return "outros", 0.0


class Classifier:
    def __init__(self, model=None):
        try:
            self.model = model or load_or_train()
        except Exception as exc:  # noqa: BLE001
            log.error("Sem modelo ML (%r): usando só regras", exc)
            self.model = None

    def predict(self, text_norm: str):
        """Retorna (categoria, confiança, origem)."""
        if self.model is None:
            return (*keyword_fallback(text_norm), "regras")
        try:
            proba = self.model.predict_proba([text_norm])[0]
            i = int(proba.argmax())
            return str(self.model.classes_[i]), float(proba[i]), "ml"
        except Exception as exc:  # noqa: BLE001
            log.error("Falha na predição ML (%r): fallback por regras", exc)
            return (*keyword_fallback(text_norm), "regras")
