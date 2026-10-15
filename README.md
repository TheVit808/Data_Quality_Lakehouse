# Data Quality Lakehouse

Dataset sintético de e-commerce omnichannel para demonstrar **contratos de dados**, camadas de lakehouse, validações automatizadas e observabilidade de qualidade. A geração é determinística e injeta defeitos controlados na camada Bronze para exercitar saneamento, scoring e relatórios na Gold.

## Visão técnica

- **Dimensões:** `customers`, `products`
- **Fatos:** `orders`, `payments`, `events`
- **Período de negócio:** 2025-01-01 a 2025-12-31
- **Semente:** `20251006`
- **Formato:** CSV e Parquet
- **Contratos:** YAML versionado em `contracts/`, com schema, chaves, regras, SLA e governança
- **Camadas:** Bronze preserva a origem; Silver é o estágio conceitual de padronização; Gold contém dados saneados para consumo analítico

O modelo é um star schema centrado em pedidos: `orders` referencia `customers` e `products`; `payments` referencia `orders`; `events` referencia `customers` e opcionalmente `orders`. A documentação do modelo está em [`docs/model.md`](docs/model.md) e o dicionário detalhado em [`reports/executive_summary.md`](reports/executive_summary.md).

## Dados e contratos

A geração produz cinco datasets com contratos JSON/YAML:

- `customers` e `products`: dimensões;
- `orders`, `payments` e `events`: fatos/eventos;
- `quality_runs`: resultados dos checks persistidos por execução;
- `defect_log`: inventário dos defeitos injetados na Bronze.

A execução de `generate_dataset.py` é determinística e recria os arquivos em `data/bronze/`, `data/gold/`, `contracts/` e `reports/`. O snapshot de referência contém 90.302 registros na Bronze, 89.845 na Gold e 295 defeitos/outliers controlados. Os Parquets podem ser consultados com pandas, DuckDB, Polars ou Spark/Databricks.

## Qualidade e observabilidade

A camada `src/quality/` implementa checks reutilizáveis sobre a Bronze ou Gold:

- schema e tipos;
- nulos e completude;
- unicidade;
- domínios aceitos;
- valores positivos;
- integridade referencial;
- atualidade/freshness;
- volume esperado.

Os resultados são representados por `CheckResult`, recebem severidade (`critical`, `error` ou `warning`) e são pontuados com pesos padrão de 5, 3 e 1, respectivamente. A execução persiste histórico em `data/gold/quality_runs.parquet` e `quality_runs.csv`, scores em `reports/quality_scores.*` e relatórios em Markdown/HTML.

O relatório atual (`reports/quality_report.md`) registra **41 checks**, **2 falhas**, ambas críticas:

| Dataset | Score | Checks | Falhas | Falhas críticas |
|---|---:|---:|---:|---:|
| `customers` | 80,00 | 7 | 1 | 1 |
| `events` | 100,00 | 9 | 0 | 0 |
| `orders` | 100,00 | 10 | 0 | 0 |
| `payments` | 100,00 | 7 | 0 | 0 |
| `products` | 84,38 | 8 | 1 | 1 |

As falhas são `schema_columns_and_types` em `customers` e `products`: os campos textuais chegam como `object`, enquanto o contrato esperado pelo runner está tipado como string equivalente. Em uma integração CI/CD, a CLI pode retornar código não zero quando `--fail-on-critical` for usado.

## Execução

Requisitos: Python 3.11+ e `numpy`, `pandas`, `pyarrow`, `pyyaml` e `pytest`.

```bash
python3 -m pip install numpy pandas pyarrow pyyaml pytest
python3 generate_dataset.py
```

Para validar os contratos e os checks unitários:

```bash
pytest -q tests/validate_contracts.py
pytest -q tests/test_checks.py
```

Para executar a camada de qualidade:

```bash
python3 -m src.quality.cli --layer bronze
python3 -m src.quality.cli --layer gold
python3 -m src.quality.cli --layer bronze --fail-on-critical
```

A CLI imprime a quantidade de checks, score global, falhas críticas e score por dataset. Cada execução gera/atualiza `reports/quality_report.md`, `reports/quality_report.html` e `reports/quality_scores.*`.

## Consulta com DuckDB

O arquivo `query.sql` cria uma view sobre `data/gold/quality_runs.parquet` e consulta checks, falhas e taxa de aprovação por execução:

```bash
duckdb quality.duckdb < query.sql
```

Também está disponível o relatório HTML [`reports/quality_report.html`](reports/quality_report.html) para inspeção visual.

## Estado do pipeline

`generate_dataset.py` é o fluxo executável de referência para geração e saneamento determinísticos. `src/pipeline/build_layers.py` continua sendo um blueprint modular das etapas Bronze/Silver/Gold, com stubs ainda não adequados para orquestração de produção. A camada `src/quality/` já fornece execução, scoring, persistência e reporting independentes.

> **Nota sobre contratos:** `contracts/catalog.yml` é um catálogo de metadados e não possui o mesmo schema dos contratos de dataset. O teste legado `tests/validate_contracts.py` ainda o inclui no glob de contratos; por isso, essa suíte precisa filtrar o catálogo ou validá-lo separadamente.

## Organização

```text
contracts/             Contratos YAML/JSON e catálogo de metadados
data/bronze/           Dados de entrada com defeitos controlados
data/gold/             Dados saneados e quality_runs persistidos
docs/                  Decisões do modelo de dados
reports/               Resumos, scores, tendências e relatórios HTML/Markdown
src/pipeline/          Blueprint do pipeline Bronze/Silver/Gold
src/quality/           Checks, runner, scoring, persistência e reporting
tests/                 Testes unitários e validação estrutural de contratos
query.sql              Consultas DuckDB sobre quality_runs
quality.duckdb         Banco DuckDB para exploração local
```
