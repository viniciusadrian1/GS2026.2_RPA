# Resultados de validação — classificador de relatos

Treino: `treino.csv` (400 relatos sintéticos). Todos os dados são sintéticos.

## Teste gerado (mesmo gerador, outra semente) (n=100)

- Acurácia: **1.000**
- F1 macro: **1.000**

```
              precision    recall  f1-score   support

      buraco       1.00      1.00      1.00        20
  iluminacao       1.00      1.00      1.00        20
        lixo       1.00      1.00      1.00        20
       ruido       1.00      1.00      1.00        20
      outros       1.00      1.00      1.00        20

    accuracy                           1.00       100
   macro avg       1.00      1.00      1.00       100
weighted avg       1.00      1.00      1.00       100
```

Matriz de confusão:

```
                 pred:buraco  pred:iluminacao  pred:lixo  pred:ruido  pred:outros
real:buraco               20                0          0           0            0
real:iluminacao            0               20          0           0            0
real:lixo                  0                0         20           0            0
real:ruido                 0                0          0          20            0
real:outros                0                0          0           0           20
```

Erros (0):


Limiar de confiança -> % enviado à revisão humana | acurácia do que o robô resolve sozinho

| limiar | revisão humana | acurácia automática |
|---|---|---|
| 0.00 | 0% | 1.000 |
| 0.40 | 0% | 1.000 |
| 0.55 | 0% | 1.000 |
| 0.70 | 1% | 1.000 |

## Teste manual / DESENVOLVIMENTO (escrito à mão; usado para ajustar o gerador) (n=40)

- Acurácia: **1.000**
- F1 macro: **1.000**

```
              precision    recall  f1-score   support

      buraco       1.00      1.00      1.00         8
  iluminacao       1.00      1.00      1.00         8
        lixo       1.00      1.00      1.00         8
       ruido       1.00      1.00      1.00         8
      outros       1.00      1.00      1.00         8

    accuracy                           1.00        40
   macro avg       1.00      1.00      1.00        40
weighted avg       1.00      1.00      1.00        40
```

Matriz de confusão:

```
                 pred:buraco  pred:iluminacao  pred:lixo  pred:ruido  pred:outros
real:buraco                8                0          0           0            0
real:iluminacao            0                8          0           0            0
real:lixo                  0                0          8           0            0
real:ruido                 0                0          0           8            0
real:outros                0                0          0           0            8
```

Erros (0):


Limiar de confiança -> % enviado à revisão humana | acurácia do que o robô resolve sozinho

| limiar | revisão humana | acurácia automática |
|---|---|---|
| 0.00 | 0% | 1.000 |
| 0.40 | 2% | 1.000 |
| 0.55 | 5% | 1.000 |
| 0.70 | 22% | 1.000 |

## Teste FINAL (escrito à mão, não usado no ajuste) (n=40)

- Acurácia: **0.950**
- F1 macro: **0.950**

```
              precision    recall  f1-score   support

      buraco       1.00      0.88      0.93         8
  iluminacao       0.89      1.00      0.94         8
        lixo       0.89      1.00      0.94         8
       ruido       1.00      0.88      0.93         8
      outros       1.00      1.00      1.00         8

    accuracy                           0.95        40
   macro avg       0.96      0.95      0.95        40
weighted avg       0.96      0.95      0.95        40
```

Matriz de confusão:

```
                 pred:buraco  pred:iluminacao  pred:lixo  pred:ruido  pred:outros
real:buraco                7                0          1           0            0
real:iluminacao            0                8          0           0            0
real:lixo                  0                0          8           0            0
real:ruido                 0                1          0           7            0
real:outros                0                0          0           0            8
```

Erros (2):

- real=`buraco` predito=`lixo` (conf 0.42): Depois da obra da companhia de gás ficou uma vala sem tampar na calçada
- real=`ruido` predito=`iluminacao` (conf 0.47): Cachorros latindo sem parar o dia inteiro e o dono não resolve

Limiar de confiança -> % enviado à revisão humana | acurácia do que o robô resolve sozinho

| limiar | revisão humana | acurácia automática |
|---|---|---|
| 0.00 | 0% | 0.950 |
| 0.40 | 0% | 0.950 |
| 0.55 | 25% | 1.000 |
| 0.70 | 42% | 1.000 |

## Evolução

| versão | gerado | manual (dev) | final |
|---|---|---|---|
| v1: TF-IDF palavras, vocabulário estreito | 1.000 | 0.550 | 0.700 |
| v2: + n-gramas de caracteres e vocabulário variado | 1.000 | 1.000 | 0.950 |

## Limites

- O teste gerado usa os mesmos gabaritos do treino: o número tende a ser otimista.
- O manual (dev) informou o vocabulário do gerador v2: seu número também é otimista. Só o FINAL é imparcial.
- Os testes manuais (40 frases cada) são pequenos: cada erro pesa 2,5 pontos percentuais; não há intervalo de confiança.
- Nenhum dado real de moradores foi usado; o desempenho em texto real pode ser pior.
