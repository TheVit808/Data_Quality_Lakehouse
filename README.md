# Data Quality Lakehouse

Dataset sintético de e-commerce omnichannel para demonstrar **contratos de dados**, camadas de lakehouse e observabilidade de qualidade. A geração é determinística e injeta defeitos controlados na camada Bronze para exercitar validações e saneamento na Gold.

## Visão técnica

- **Dimensões:** `customers`, `products`
- **Fatos:** `orders`, `payments`, `events`
- **Período:** 2025-01-01 a 2025-12-31
- **Formato:** CSV e Parquet
- **Semente:** `20251006`
- **Contratos:** YAML versionado em `contracts/`, com schema, chaves, regras de qualidade, SLA e governança
- **Dados:** `data/bronze/` preserva anomalias; `data/gold/` contém dados tipados e saneados

O modelo segue um star schema centrado em pedidos: `orders` referencia `customers` e `products`; `payments` referencia `orders`; `events` referencia `customers` e opcionalmente `orders`. A documentação detalhada está em [`docs/model.md`](docs/model.md) e [`reports/executive_summary.md`](reports/executive_summary.md).

## Qualidade e observabilidade

A geração registra `quality_runs` e `defect_log` em CSV/Parquet. As regras cobrem schema, completude, unicidade, domínios, positividade, integridade referencial e atualidade. A Bronze contém falhas intencionais, incluindo duplicidade de pedidos, chaves órfãs, valores fora de domínio, nulos inesperados, outliers e timestamp futuro; portanto, falhas críticas na validação da Bronze são esperadas.

## Execução

Requisitos: Python 3.11+ e os pacotes `numpy`, `pandas`, `pyarrow`, `pyyaml` e `pytest`.

```bash
python3 -m pip install numpy pandas pyarrow pyyaml pytest
python3 generate_dataset.py
pytest -q tests/validate_contracts.py
```

A execução de `generate_dataset.py` recria os dados, contratos e relatórios. Os principais resultados são:

- `data/bronze/` e `data/gold/`: datasets gerados;
- `contracts/*.json` e `contracts/*.yml`: contratos das cinco entidades;
- `reports/summary.json`: contagens, métricas, checks e fingerprint;
- `reports/executive_summary.md`: análise estatística e dicionário de dados.

Os Parquets podem ser consultados com DuckDB, Polars, Spark/Databricks ou pandas.

> **Nota:** a suíte atual ainda inclui `contracts/catalog.yml` na validação de contratos, embora esse arquivo seja um catálogo de metadados e não siga o mesmo schema dos contratos de dataset. Por isso, a validação completa falha até que o teste passe a filtrar o catálogo ou que ele seja validado separadamente.

## Estado do pipeline

A geração atual é o fluxo executável de referência. `src/pipeline/build_layers.py` documenta a futura implementação modular das etapas Bronze/Silver/Gold, mas ainda contém stubs (`pass`) e não deve ser usado como orquestrador de produção.

## Organização

```text
contracts/             Contratos YAML/JSON e catálogo de metadados
data/bronze/           Dados de entrada com defeitos controlados
data/gold/             Dados saneados para consumo analítico
docs/                  Decisões do modelo de dados
reports/               Métricas, fingerprint e resumo executivo
src/pipeline/          Esqueleto do pipeline modular
tests/                  Validação estrutural dos contratos
```
