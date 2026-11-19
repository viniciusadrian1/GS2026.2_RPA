# Quadro de temas

| # | Tema | Onde entra no fluxo | O que resolve | Por que esta escolha |
|---|---|---|---|---|
| 1 | **Machine Learning supervisionado** (TF-IDF + Regressão Logística) | `src/classifier.py`: classifica cada relato em buraco / iluminação / lixo / ruído / outros e devolve a confiança | Triagem automática e **mensurável** (acerto/erro em amostra rotulada) | Leve, explicável, roda sem GPU. A confiança alimenta a decisão de revisão humana |
| 2 | **RPA com automação web** (Playwright) | `src/rpa_portal.py`: abre o portal do gestor, preenche o formulário e lê o nº do chamado, como um funcionário faria | Elimina a digitação manual de cada ocorrência no sistema do órgão | Mostra o robô "de verdade"; portal simulado local evita depender de site real |
| 3 | **Regras inteligentes e human-in-the-loop** | `src/priority.py`, `src/dedup.py`, limiar em `pipeline.py` | Prioridade explicável, agrupamento de relatos do mesmo problema, e envio à **revisão humana** do que o robô não resolve | Decisão com regra clara e auditável; o robô sabe quando não decidir |
| 4 | **NLP** (mascaramento de dados pessoais, normalização, extração de endereço, recuperação de informação) | `src/nlp.py`, `src/assistant.py` | Remove CPF/telefone/e-mail antes de qualquer etapa; extrai o local do texto livre; assistente responde com base numa base de serviços | LGPD por padrão; assistente funciona sem LLM (LLM é opcional, com fallback) |
| 5 | **Orquestração e resiliência de pipeline** (log, retry com backoff, idempotência, disjuntor, relatório) | `src/pipeline.py`, `src/utils/resilience.py`, `src/protocol.py`, `src/report.py` | Execução contínua sem intervenção, sem duplicar protocolos, sem cair por um arquivo ruim | Critério de 20% da nota; permite reexecutar o lote com segurança |

**Combinação:** o ML dá a categoria e a confiança → as regras decidem prioridade e revisão humana → o RPA executa a ação no portal → o NLP protege os dados e orienta o cidadão. Cada etapa depende da anterior; remover qualquer tema quebra o fluxo.
