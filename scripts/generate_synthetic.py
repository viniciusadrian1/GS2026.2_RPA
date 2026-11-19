"""Gera dados SINTÉTICOS (nenhum dado pessoal real): treino, teste gerado e a caixa de entrada de exemplo.
O teste manual (teste_manual.csv) foi escrito à mão, com vocabulário diferente dos gabaritos."""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd  # noqa: E402

from config import settings  # noqa: E402

RUAS = ["Rua das Acácias", "Avenida dos Ipês", "Rua Dom Pedro Segundo", "Travessa do Sol", "Praça da Fonte",
        "Rua Santa Clara", "Avenida Beira Rio", "Rua Cruzeiro do Sul", "Rua dos Jasmins", "Alameda das Palmeiras"]
BAIRROS = ["Jardim Aurora", "Vila Esperança", "Parque Verde", "Vila Nova Aliança", "Bairro Alto Sereno"]

CORES = {
    "buraco": ["tem um buraco enorme na", "buraco gigante no meio da", "a rua está cheia de buracos na",
               "cratera aberta no asfalto da", "o asfalto afundou na", "buraco na pista da"],
    "iluminacao": ["poste apagado na", "a iluminação não funciona na", "lâmpada queimada no poste da",
                   "o poste está sem luz na", "rua totalmente escura na", "luminária piscando sem parar na"],
    "lixo": ["lixo acumulado na", "entulho jogado na calçada da", "sacos de lixo espalhados na",
             "caçamba transbordando na", "a coleta não passa há dias na", "descarte irregular de sofá e colchão na"],
    "ruido": ["som alto de bar na", "barulho de festa até de madrugada na", "vizinho com caixa de som altíssima na",
              "carro de som passando toda hora na", "obra fazendo barulho fora do horário na",
              "bar com música ao vivo muito alta na"],
}
EXTRAS = {
    "buraco": ["já danificou o pneu de vários carros", "uma moto quase caiu ontem", "fica pior quando chove",
               "está assim há semanas", "os ônibus desviam e causam trânsito", "é perigoso para pedestres", ""],
    "iluminacao": ["já faz mais de uma semana", "fica inseguro à noite", "os moradores têm medo de passar",
                   "parece problema na fiação", "ninguém veio consertar", ""],
    "lixo": ["cheiro forte e muitos ratos", "atrai insetos e baratas", "bloqueia a passagem de pedestres",
             "já está há mais de uma semana", "o mau cheiro incomoda a vizinhança", ""],
    "ruido": ["não consigo dormir", "criança pequena acorda toda noite", "acontece todo fim de semana",
              "já pedi para baixar e não adiantou", "passa das duas da manhã", ""],
}
OUTROS = ["quero saber como tirar a segunda via do IPTU", "o ônibus da linha 45 atrasa muito",
          "gostaria de elogiar o atendimento da UBS", "tem vazamento de água dentro do meu apartamento",
          "meu vizinho estacionou na minha garagem", "minha internet está muito lenta",
          "preciso de informação sobre vaga em creche", "problema com a conta de luz da minha casa",
          "fila enorme no banco da", "como faço para tirar um alvará", "onde pago a taxa de licença"]


# Frases livres, sem rua formal (como o morador realmente escreve). Vocabulário inspirado no conjunto de
# DESENVOLVIMENTO (teste_manual.csv); o teste_final.csv foi escrito antes e não foi usado aqui.
LOCAIS = ["na minha rua", "no meu bairro", "em frente ao mercado", "perto da escola", "na esquina de casa",
          "na praça", "na avenida principal", "em frente ao meu prédio", "no fim da quadra", "na entrada da vila"]
LIVRES = {
    "buraco": ["abriu um rombo no chão {l}", "o pavimento está destruído {l}", "o asfalto cedeu {l}",
               "a rua está toda esburacada {l}", "cratera no asfalto {l}", "o tapa-buraco abriu de novo {l}",
               "buraco fundo {l} e os carros desviam", "o chão afundou {l}"],
    "iluminacao": ["está tudo no breu {l}", "a lâmpada queimou {l}", "o poste não acende {l}",
                   "a luminária está apagada {l}", "poste com fiação pendurada {l}",
                   "falta iluminação {l} e dá medo de passar", "a luz do poste pisca {l}", "a escuridão {l} já causou assalto"],
    "lixo": ["lixo espalhado {l}", "a coleta não passa {l} há dias", "restos de obra e entulho jogados {l}",
             "colchão e geladeira velha abandonados {l}", "sujeira acumulada {l}",
             "a lixeira está quebrada e transbordando {l}", "resto de poda de árvore largado {l}", "container cheio e fedendo {l}"],
    "ruido": ["pancadão até o sol nascer {l}", "oficina martelando de manhã cedo {l}", "som automotivo em volume absurdo {l}",
              "amplificador altíssimo {l} de madrugada", "festa com caixa de som {l} toda semana",
              "moto com escapamento aberto acelerando {l}", "betoneira ligada antes das sete {l}", "o barulho {l} não deixa dormir"],
}
OUTROS += ["preciso de segunda via de documento", "o ônibus atrasa demais", "reclamação do atendimento no posto de saúde",
           "minha conta veio com valor errado", "dúvida sobre imposto parcelado", "o wifi gratuito não funciona",
           "como me inscrevo em curso gratuito", "quero informações sobre benefício social", "fila enorme no banco"]


def noisy(t, rnd):
    if rnd.random() < 0.3:
        t = t.lower()
    if rnd.random() < 0.15 and len(t) > 8:  # troca de letras vizinhas (erro de digitação)
        i = rnd.randrange(2, len(t) - 2)
        t = t[:i] + t[i + 1] + t[i] + t[i + 2:]
    if rnd.random() < 0.2:
        t = t.replace("ç", "c").replace("ã", "a").replace("é", "e")
    return t


def make(n_per_class, seed):
    rnd, rows, seen = random.Random(seed), [], set()
    for cat in ["buraco", "iluminacao", "lixo", "ruido", "outros"]:
        while sum(1 for r in rows if r[1] == cat) < n_per_class:
            rua, bairro = rnd.choice(RUAS), rnd.choice(BAIRROS)
            if cat == "outros":
                t = f"{rnd.choice(OUTROS)}, {bairro}." if rnd.random() < .5 else f"{rnd.choice(OUTROS)}."
            elif rnd.random() < 0.5:
                t = rnd.choice(LIVRES[cat]).format(l=rnd.choice(LOCAIS)).capitalize() + "."
                if rnd.random() < 0.4:
                    t += " " + rnd.choice(EXTRAS[cat]).capitalize()
                t = t.strip()
            else:
                t = f"{rnd.choice(CORES[cat]).capitalize()} {rua}, {bairro}. {rnd.choice(EXTRAS[cat])}".strip()
                if rnd.random() < 0.15:  # ruído de domínio: menção a outra categoria (rótulo = queixa principal)
                    other = rnd.choice([c for c in CORES if c != cat])
                    t += f" Ao lado também tem {rnd.choice(['lixo', 'um poste', 'barulho', 'um buraco'])}."
            t = noisy(t, rnd)
            if t not in seen:
                seen.add(t)
                rows.append((t, cat))
    rnd.shuffle(rows)
    return pd.DataFrame(rows, columns=["texto", "categoria"])


def make_inbox():
    inbox = settings.INBOX_DIR
    (inbox / "anexos").mkdir(parents=True, exist_ok=True)
    for f in inbox.glob("*.json"):
        f.unlink()
    A = (-23.55050, -46.63330)  # coordenadas fictícias
    base = [
        ("r001", "Tem um buraco enorme na Rua das Acácias, Jardim Aurora. Já danificou o pneu de dois carros.", A, None),
        ("r002", "O asfalto afundou na Rua das Acácias e os carros estão desviando para a contramão.", (A[0] + 0.0002, A[1]), None),
        ("r003", "Poste apagado na Avenida dos Ipês, tem fio exposto e as crianças da escola passam ali.", (-23.5600, -46.6400), None),
        ("r004", "Entulho jogado na calçada da Travessa do Sol há mais de uma semana, com muito rato.", (-23.5700, -46.6200), None),
        ("r005", "Barulho de festa até de madrugada na Rua Santa Clara, não consigo dormir.", (-23.5400, -46.6500), None),
        ("r006", "Quero saber como tirar a segunda via do IPTU. Telefone (11) 98888-7777, CPF 123.456.789-09.", (-23.5500, -46.6300), None),
        ("r007", "Tem um problema aqui perto de casa que precisa ser resolvido logo.", (-23.5450, -46.6350), None),
        ("r011", "Buraco fundo na Alameda das Palmeiras, já danificou carros. Contato: Joana 11 97777-6666 joana@exemplo.com.", (-23.5800, -46.6100), None),
        ("r015", "Buraco gigante no meio da Rua das Acácias, os ônibus estão desviando.", (A[0], A[1] + 0.0003), None),
    ]
    for rid, texto, (lat, lon), _ in base:
        (inbox / f"{rid}.json").write_text(json.dumps(
            {"id": rid, "texto": texto, "lat": lat, "lon": lon, "data": "2026-11-10T09:00:00",
             "morador_ref": f"morador-{rid}"}, ensure_ascii=False, indent=1), encoding="utf-8")
    # duplicata exata de r001 (mesmo id e texto) -> idempotência
    (inbox / "r013_duplicado_de_r001.json").write_text(json.dumps(
        {"id": "r001", "texto": base[0][1], "lat": A[0], "lon": A[1], "data": "2026-11-10T09:00:00"},
        ensure_ascii=False), encoding="utf-8")
    # falhas previstas
    (inbox / "r008_corrompido.json").write_text('{"id": "r008", "texto": "buraco na rua', encoding="utf-8")
    (inbox / "r009_sem_texto.json").write_text(json.dumps({"id": "r009", "lat": -23.5, "lon": -46.6}), encoding="utf-8")
    (inbox / "r010_coordenada_invalida.json").write_text(json.dumps(
        {"id": "r010", "texto": "Poste apagado na Rua dos Jasmins há dias.", "lat": 999, "lon": -46.6}), encoding="utf-8")
    # só áudio (ASR desligado -> revisão humana)
    (inbox / "anexos" / "relato_012.wav").write_bytes(b"RIFF....WAVEfmt ")
    (inbox / "r012_somente_audio.json").write_text(json.dumps(
        {"id": "r012", "lat": -23.5, "lon": -46.6, "anexos": [{"tipo": "audio", "arquivo": "anexos/relato_012.wav"}]}),
        encoding="utf-8")
    # foto com EXIF/GPS falso (para provar a remoção)
    from PIL import Image
    img = Image.new("RGB", (64, 64), (120, 120, 120))
    exif = Image.Exif()
    exif[0x010F] = "CameraFalsa"
    exif.get_ifd(0x8825)[1] = "S"
    img.save(inbox / "anexos" / "foto_014.jpg", exif=exif)
    (inbox / "r014_com_foto.json").write_text(json.dumps(
        {"id": "r014", "texto": "Cratera na Avenida Beira Rio, uma moto quase caiu ontem.", "lat": -23.5900, "lon": -46.6000,
         "anexos": [{"tipo": "foto", "arquivo": "anexos/foto_014.jpg"}]}, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    make(100, seed=42).to_csv(settings.TRAIN_CSV, index=False, encoding="utf-8")
    make(20, seed=7).to_csv(settings.DATA_DIR / "synthetic" / "teste_gerado.csv", index=False, encoding="utf-8")
    make_inbox()
    print("Dados sintéticos gerados em", settings.DATA_DIR)
