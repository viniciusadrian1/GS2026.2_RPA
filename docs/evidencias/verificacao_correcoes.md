# Verificação das correções — 19/11/2026

Validação em Windows, Python 3.13, sem chave de LLM e com ASR desativado.

## Testes automatizados

`python -m pytest -q`: **20 passed**.

Os cinco casos novos em `tests/test_delivery_fixes.py` verificam:

- persistência e idempotência do portal entre processos Python independentes;
- recuperação de comprovante após falha da base de orientações, sem a entrada original, tanto para relato automático quanto para revisão humana;
- encaminhamento de categoria `outros` mesmo com confiança alta;
- 16 de 40 exemplos finais encaminhados por confiança ou categoria.

## Execução completa repetida

Executado `python main.py --demo` duas vezes, na mesma cópia inicialmente limpa.
O portal foi encerrado e iniciado novamente entre as execuções.

| Resultado | Primeira execução | Segunda execução |
|---|---:|---:|
| Arquivos lidos | 15 | 15 |
| Ocorrências novas | 6 | 0 |
| Registros enviados ao portal | 6 | 0 |
| Relatos agrupados | 2 | 0 |
| Já processados | 1 | 12 |
| Rejeitados | 3 | 3 |
| Encaminhados para revisão nesta execução | 3 | 0 |
| Comprovantes gerados | 11 | 0 |

Após a segunda execução, uma leitura independente confirmou **6 chamados no portal**, **6 ocorrências locais com os mesmos tickets** e **11 comprovantes**. Não houve duplicação.

O teste ponta a ponta usou o fallback HTTP porque Playwright não estava instalado neste ambiente. As evidências anteriores de execução pelo navegador permanecem separadas.

## Métricas recalculadas

`python scripts/evaluate.py` confirmou treino com **500 exemplos**, acurácia de **0,950** no teste final e revisão por confiança/categoria de **40%**, com **60% elegíveis à automação** e acurácia de **1,000** nesse subconjunto. A medição textual não inclui localização nem falhas de anexos.
