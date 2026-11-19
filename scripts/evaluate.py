"""Validação: treina em treino.csv e mede em (a) teste gerado e (b) teste manual escrito à mão.
Gera docs/resultados_validacao.md com acurácia, F1, matriz de confusão, erros e curva confiança x revisão."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd  # noqa: E402
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score  # noqa: E402

from config import settings  # noqa: E402
from src.classifier import train  # noqa: E402
from src.nlp import normalize  # noqa: E402

LABELS = settings.CATEGORIES


def automatic_mask(predictions, confidence, threshold):
    return (confidence >= threshold) & (pd.Series(predictions).to_numpy() != "outros")


def evaluate(model, csv, nome, out):
    df = pd.read_csv(csv, encoding="utf-8")
    X = df["texto"].map(normalize)
    proba = model.predict_proba(X)
    pred = [str(model.classes_[i]) for i in proba.argmax(axis=1)]
    conf = proba.max(axis=1)
    acc = accuracy_score(df["categoria"], pred)
    f1m = f1_score(df["categoria"], pred, average="macro", labels=LABELS)
    out.append(f"## {nome} (n={len(df)})\n\n- Acurácia: **{acc:.3f}**\n- F1 macro: **{f1m:.3f}**\n")
    out.append("```\n" + classification_report(df["categoria"], pred, labels=LABELS, zero_division=0) + "```\n")
    cm = pd.DataFrame(confusion_matrix(df["categoria"], pred, labels=LABELS),
                      index=[f"real:{l}" for l in LABELS], columns=[f"pred:{l}" for l in LABELS])
    out.append("Matriz de confusão:\n\n```\n" + cm.to_string() + "\n```\n")
    errs = df.assign(predito=pred, confianca=conf.round(2))[df["categoria"] != pd.Series(pred)]
    out.append(f"Erros ({len(errs)}):\n")
    for _, r in errs.iterrows():
        out.append(f"- real=`{r.categoria}` predito=`{r.predito}` (conf {r.confianca}): {r.texto}")
    out.append("")
    # trade-off do limiar: o que vai para revisão humana x acerto do que o robô decide sozinho
    out.append("Revisão por baixa confiança OU categoria `outros`; acurácia entre os elegíveis à automação. "
               "Esta avaliação textual não considera localização nem falhas de anexos, que também podem exigir revisão.\n")
    out.append("| limiar | revisão humana | acurácia automática |\n|---|---|---|")
    for th in (0.0, 0.4, 0.55, 0.7):
        auto = automatic_mask(pred, conf, th)
        acc_auto = accuracy_score(df["categoria"][auto], pd.Series(pred)[auto]) if auto.any() else float("nan")
        out.append(f"| {th:.2f} | {(~auto).mean():.0%} | {acc_auto:.3f} |")
    out.append("")
    return acc, f1m


if __name__ == "__main__":
    model = train()
    training_count = len(pd.read_csv(settings.TRAIN_CSV))
    out = ["# Resultados de validação — classificador de relatos\n",
           f"Treino: `treino.csv` ({training_count} relatos sintéticos). Todos os dados são sintéticos.\n"]
    a1, f1 = evaluate(model, settings.DATA_DIR / "synthetic" / "teste_gerado.csv", "Teste gerado (mesmo gerador, outra semente)", out)
    a2, f2 = evaluate(model, settings.DATA_DIR / "synthetic" / "teste_manual.csv",
                      "Teste manual / DESENVOLVIMENTO (escrito à mão; usado para ajustar o gerador)", out)
    a3, f3 = evaluate(model, settings.DATA_DIR / "synthetic" / "teste_final.csv",
                      "Teste FINAL (escrito à mão, não usado no ajuste)", out)
    out.append("## Evolução\n\n| versão | gerado | manual (dev) | final |\n|---|---|---|---|\n"
               "| v1: TF-IDF palavras, vocabulário estreito | 1.000 | 0.550 | 0.700 |\n"
               f"| v2: + n-gramas de caracteres e vocabulário variado | {a1:.3f} | {a2:.3f} | {a3:.3f} |\n")
    out.append("## Limites\n\n- O teste gerado usa os mesmos gabaritos do treino: o número tende a ser otimista.\n"
               "- O manual (dev) informou o vocabulário do gerador v2: seu número também é otimista. O FINAL foi escrito pelo grupo e não equivale a validação externa independente.\n"
               "- Os testes manuais (40 frases cada) são pequenos: cada erro pesa 2,5 pontos percentuais; não há intervalo de confiança.\n"
               "- Nenhum dado real de moradores foi usado; o desempenho em texto real pode ser pior.\n")
    Path("docs").mkdir(exist_ok=True)
    Path("docs/resultados_validacao.md").write_text("\n".join(out), encoding="utf-8")
    print(f"Gerado: acc={a1:.3f} f1={f1:.3f} | Manual(dev): acc={a2:.3f} f1={f2:.3f} | FINAL: acc={a3:.3f} f1={f3:.3f}")
    print("Detalhes em docs/resultados_validacao.md")
