# Funda Analyzer — Roadmap

Estado do projeto e próximos passos. Atualizado conforme avançamos.

## ✅ Pronto (funcionando com dados de exemplo)

- **Fundação de dados** — `src/models.py`, `src/config.py`, `config/search.yaml`
- **Coleta MULTI-FONTE** — `src/providers/collect_all()` roda várias fontes de uma vez,
  marca a origem e UNIFICA DUPLICATAS entre portais (ex: funda+pararius), completando
  campos faltantes. Fontes não implementadas são puladas com aviso.
- **Avaliação WOZ** — `src/enrichment/woz.py` (avaliação fiscal, modo estimativa)
- **Vendas reais Kadaster** — `src/enrichment/kadaster.py` (modo estimativa) — LIGADO ao
  score (peso 0.25, sinal forte de preço abaixo do mercado)
- **Reforma (heurística)** — `src/enrichment/renovation.py`
- **Motor de score** — `src/scoring/engine.py` (WOZ, vendas reais, €/m², tempo, label)
- **Dashboard HTML** — `src/report/dashboard.py` (Plotly + tabela ordenável, colunas de
  fonte, WOZ, venda de referência e reforma)
- **Orquestrador** — `main.py` (coleta multi-fonte -> WOZ -> Kadaster -> reforma -> score)

## 🔜 Em andamento

- **Reforma — heurística (Opção C)**: PRONTA e ligada. `src/enrichment/renovation.py`
  (palavras-chave da descrição + ano + label energético).
- **Reforma — visão da Claude (Opção A)**: módulo `src/enrichment/vision.py` criado,
  mas DESABILITADO por enquanto (não está ligado ao pipeline). Para ativar no futuro:
  `pip install anthropic`, definir ANTHROPIC_API_KEY, e chamar `enrich_vision` no main.py.

## 📋 Próximos (roadmap)

### Coletores adicionais (mesma arquitetura plugável)
- **Pararius** (`src/providers/pararius.py`) — 2º maior portal, tem imóveis à venda
  que às vezes não estão no Funda. Esqueleto criado.
- ~~Jaap.nl~~ — descartado: parou de listar imóveis à venda.
- Huispedia / Homeup — opcionais, conforme o sistema crescer.

### Fontes de dados para valuation (aprofundam o score)
- **Kadaster** (`src/enrichment/kadaster.py`) — PREÇOS REAIS DE VENDA de imóveis
  parecidos (o dado mais valioso pra saber se um pedido está caro/barato).
  Esqueleto criado.
- **CBS** — tendência de preço por bairro/código postal e tempo médio de venda.
- **EP-Online** — label energético oficial (mais confiável que o do anúncio).
- **Leefbaarometer** — índice de qualidade de vida por área (valorização futura).

### Fase "real" (trocar os modos de exemplo pelos reais)
- Scraping real do Funda com Playwright (ajustar seletores; lidar com DataDome).
- WOZ real via PDOK + wozwaardeloket (hoje é estimativa).

### Interface
- Filtros no próprio dashboard (cidade, faixa de preço, score mínimo) — client-side.
- Painel de controle interativo (Streamlit) — escolher filtros e re-rodar a coleta.

### Persistência
- ✅ **Banco SQLite** (`src/storage/db.py`) — LIGADO. Cada execução grava um snapshot
  em `data/funda.db` (histórico completo p/ detectar quedas de preço) e exporta
  `output/latest.csv`. Ver com DB Browser for SQLite ou a extensão SQLite Viewer no VS Code.
- Próximo: alertas de queda de preço comparando snapshots.
