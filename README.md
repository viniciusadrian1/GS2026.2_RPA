# Bairro em Dia — robô de triagem de relatos do bairro (CitizenTech · GS 2026.2 · RPA + IA)

**Integrantes**

| Nome | RM |
|---|---|
| Marcelo Roberto Maso Junior | 562163 |
| Gabriel Tonelli Avelino dos Santos | 564705 |
| Vinícius Adrian Siqueira de Oliveira | 564962 |

## Problema e público
Moradores relatam buracos, iluminação com defeito, lixo acumulado e barulho, mas os relatos chegam soltos, sem categoria, sem prioridade e muitas vezes repetidos, e alguém precisa digitá-los à mão no sistema do órgão responsável. O **Bairro em Dia** é um robô que lê os relatos (texto, foto ou áudio), classifica, prioriza, agrupa os repetidos, gera **protocolo** para o morador acompanhar, **registra a ocorrência no portal do gestor** e encaminha para **revisão humana** o que não consegue resolver com segurança. Também há um **assistente** que orienta o cidadão sobre como buscar atendimento.

## Fluxo (uma execução contínua)
```
data/inbox/*.json  →  validação  →  mascara dados pessoais (LGPD)  →  [áudio→texto | foto sem EXIF]
  →  extrai endereço  →  ML classifica (categoria + confiança)  →  regras de prioridade
  →  confiança baixa / fora do escopo / sem local?  ── sim ─→  fila de REVISÃO HUMANA
  →  agrupa relatos do mesmo problema (≤ 80 m)  →  protocolo idempotente (SQLite)
  →  robô Playwright registra no portal do órgão  →  comprovante + relatório da execução + PAINEL DO GESTOR
```

## Como executar
Requisitos: Python 3.10+.
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate      Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium     # navegador do robô (opcional: sem ele o robô usa HTTP)
python scripts/generate_synthetic.py      # gera dados sintéticos + caixa de entrada de exemplo
python main.py --demo                     # sobe o portal simulado, processa tudo e gera relatórios
python main.py --manter-portal            # idem, e deixa o portal aberto para você ver no navegador
```
Outros comandos: `python main.py --consultar BED-XXXXXXXXXX` (morador acompanha) · `--perguntar "texto"` (assistente) · `--sem-portal` · `--treinar` · `--demo --loop 10` (repete a cada 10 min, sem intervenção) · `python scripts/evaluate.py` (validação) · `python scripts/capturar_prints.py` (prints do painel e do relatório em `docs/evidencias/prints/`) · `python -m pytest -q` (20 testes).

**Saídas** (pasta `output/`): `painel_gestor.html` (painel visual do gestor), `relatorio_execucao.html/.json`, `fila_revisao_humana.csv`, `painel_gestor.xlsx`, `comprovantes/`, `execucao.log`.

## Chaves de API (todas opcionais)
Nenhuma chave é necessária para rodar. Para o assistente reescrever respostas com LLM (Groq, plano gratuito): copie `.env.example` para `.env` e preencha `GROQ_API_KEY`. O `.env` está no `.gitignore`. Sem chave, ou se a chamada falhar ou voltar vazia, o assistente responde com a base de serviços (`data/knowledge/servicos.json`).
Para transcrição de áudio local (gratuita), `pip install faster-whisper` e `ENABLE_ASR=1`; se falhar, o relato vai para revisão humana.

## Guia de testes (Groq, áudio e portal)
- **Painel do gestor (visual):** abra `output/painel_gestor.html` no navegador depois de qualquer execução (nenhum servidor necessário). Ao vivo: `python main.py --manter-portal` e acesse `http://127.0.0.1:8000/gestor` (atualiza sozinho a cada 10 s); `/painel` mostra os chamados criados no sistema do órgão e `/novo` o formulário que o robô preenche. Aperte ENTER no terminal para encerrar. Com só `--demo` o portal fecha quando o robô termina. Os chamados do portal ficam em `output/portal.db` e permanecem após reiniciar o programa. Para reiniciar a demonstração do zero, pare o portal e remova `output/` (isso apaga protocolos, chamados e relatórios). Após atualizar uma execução da versão antiga, que guardava chamados apenas em memória, reinicie a demonstração do zero uma vez. O painel é somente leitura.
- **Robô visível:** em `.env`, `PLAYWRIGHT_HEADLESS=0` e `PLAYWRIGHT_SLOW_MO_MS=700` (abre uma janela do Chromium preenchendo o formulário).
- **Groq:** `GROQ_API_KEY` no `.env` e `python main.py --perguntar "tem barulho de bar na minha rua"`; a última linha indica se foi o LLM ou a base.
- **Áudio:** `pip install faster-whisper`, `ENABLE_ASR=1`, troque `data/inbox/anexos/relato_012.wav` por uma gravação sua (a do repositório é um arquivo de mentira) e rode `python main.py --demo`.

## Temas da disciplina usados
ML supervisionado · RPA web (Playwright) · regras inteligentes + human-in-the-loop · NLP · orquestração/resiliência. Detalhes e justificativas em [`docs/quadro_temas.md`](docs/quadro_temas.md).

## Evidências de validação (dados sintéticos)
Classificador treinado em 500 relatos sintéticos. Detalhes, matrizes de confusão e todos os erros em [`docs/resultados_validacao.md`](docs/resultados_validacao.md).

| Conjunto | n | Acurácia | Observação |
|---|---|---|---|
| Gerado (mesmo gerador do treino) | 100 | 1,00 | **otimista**: mesmos gabaritos do treino |
| Manual, desenvolvimento | 40 | 1,00 (v1: 0,55) | usado para ajustar o gerador; **otimista** |
| **Manual, final (não usado no ajuste)** | **40** | **0,95** (38/40) (v1: 0,70) | amostra pequena, escrita pelo próprio grupo; não é validação externa independente |

No conjunto final, com limiar de confiança 0,55, **40% (16/40)** são encaminhados por baixa confiança **ou categoria `outros`**. Os **60% (24/40) elegíveis à automação** tiveram 100% de acerto. Essa medição considera somente texto e classificação: falta de localização e falhas de anexos também podem exigir revisão no fluxo completo. A baixa confiança isolada corresponde a 25% (10/40), mas não representa toda a revisão humana. Os 2 erros: "vala sem tampar" (buraco → lixo) e "cachorros latindo" (ruído → iluminação), ambos com confiança < 0,5.
**Limites:** dados sintéticos; 40 frases por conjunto (cada erro = 2,5 p.p., sem intervalo de confiança); desempenho em texto real de moradores deve ser pior.

### Falhas tratadas e demonstradas (`docs/evidencias/`)
| Falha | Comportamento | Onde ver |
|---|---|---|
| JSON corrompido / sem texto / coordenada inválida | `rejeitado` com motivo no log e no relatório; lote continua | `execucao*_relatorio.json` |
| Portal fora do ar | 3 tentativas com espera (backoff); **disjuntor** não martela o portal; ocorrências ficam `portal_pendente` | `execucao1_portal_fora_do_ar.txt` |
| Portal volta | reexecução envia só as pendentes; **nada é duplicado** (idempotência) | `execucao2_portal_no_ar.txt` |
| Portal reiniciado | chamados preservados em SQLite, sem duplicação | `tests/test_delivery_fixes.py` |
| Falha ao gerar comprovante | registra `comprovante_pendente` e recupera em outra execução, mesmo sem a entrada original | `tests/test_delivery_fixes.py` |
| Relato repetido (mesmo id e texto) | `ja_processado` | idem |
| Áudio sem transcrição / baixa confiança / fora do escopo | **fila de revisão humana** + comprovante ao morador | `fila_revisao_humana.csv` |
| Navegador indisponível | cai para HTTP | `src/rpa_portal.py` |
| LLM falha/vazio/sem chave | resposta determinística da base | `tests/test_bairro.py` |

## Estrutura
```
main.py            ponto de entrada          config/settings.py   configuração (.env)
src/               ingest · nlp · attachments · classifier · priority · dedup · protocol · rpa_portal
                   assistant · dashboard · report · pipeline · utils/(logger, resilience)
mock_portal/       portal do gestor simulado (FastAPI)
scripts/           generate_synthetic.py · evaluate.py · capturar_prints.py
data/              knowledge/ · synthetic/ · inbox/        tests/  20 testes        docs/  quadro, ética/ODS, resultados, evidências
```

## Proteção de dados, ética e ODS
Resumo: só dados sintéticos; CPF/e-mail/telefone mascarados antes de qualquer etapa; EXIF removido; revisão humana para o que o robô não resolve; ODS 11 e 16. Texto completo em [`docs/etica_dados_ods.md`](docs/etica_dados_ods.md).

## Limitações e próximos passos
Portal do gestor simulado (não integra com prefeitura real); órgãos e prazos são fictícios; fotos são apenas armazenadas sem análise visual; áudio depende de `faster-whisper`; o painel do gestor é somente leitura (aprovar/reclassificar itens da revisão humana ainda é manual, pelo CSV) e o morador consulta o protocolo por linha de comando. Próximos passos: validação com relatos reais anonimizados, classificação de imagem, interface web.
