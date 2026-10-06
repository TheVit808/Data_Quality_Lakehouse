# Dataset sintético — Data Quality e Catálogo de Metadados para Lakehouse

## 1. Resumo executivo

Este pacote materializa o escopo do PDF **02-data-quality-lakehouse.pdf** em uma base sintética de e-commerce omnichannel, adequada para demonstrar contratos de dados, camadas bronze/silver/gold conceituais, validação de schema, completude, unicidade, domínios, integridade referencial, atualidade, volume esperado e observabilidade.

- **Período de negócio:** 01/01/2025 a 31/12/2025
- **Semente de reprodução:** `20251006`
- **Camada bronze:** 90.302 registros distribuídos em 5 datasets; contém **295 defeitos/outliers controlados**.
- **Camada gold:** 89.845 registros, com deduplicação, correções de domínio e remoção de chaves órfãs.
- **Formato:** cada tabela foi exportada em `.csv` e `.parquet`.
- **Checks automatizados:** 16 regras persistidas em `quality_runs`; 6 falhas na bronze, sendo 5 críticas e 1 de completude, para exercitar CI/CD.
- **Fingerprint da gold/orders:** `2d05efa658cd074985a2fbce501ccbaaab0634c99f0c34ff9ed751a63bccac51`

A geração é determinística e pode ser refeita com `python3 generate_dataset.py`.

## 2. Modelo proposto

O modelo é um **star schema** centrado no pedido:

```text
          dim_customers
          (customer_id PK)
                 |
                 | customer_id
 dim_products -- fact_orders -- fact_payments
(product_id PK) (order_id PK)  (payment_id PK)
                       |
                       | customer_id / order_id nullable
                   fact_events
                   (event_id PK)
```

- `customers` e `products` são dimensões.
- `orders`, `payments` e `events` são fatos/eventos.
- `payments.order_id` é uma relação 1:1 esperada no cenário sintético; a bronze injeta órfãos para testar integridade.
- `events.order_id` é opcional: eventos de navegação podem não estar associados a uma compra.
- Cada contrato JSON em `contracts/` documenta chave, colunas, owner, frequência, SLA, classificação e sensibilidade.

## 3. Dicionário de dados

### `customers` — dimensão de clientes

| Coluna | Tipo | Chave | Descrição / regra |
|---|---|---|---|
| `customer_id` | int64 | PK | Identificador único e não nulo. |
| `customer_segment` | string | — | Segmento `mass`, `premium` ou `corporate`. |
| `state` | string | — | UF brasileira; bronze possui nulos injetados. |
| `city` | string | — | Cidade sintética normalizada por UF. |
| `registration_date` | datetime64 | — | Data de cadastro. |
| `marketing_opt_in` | bool | — | Consentimento de marketing. |
| `customer_status` | string | — | `active` ou `inactive`. |

### `products` — dimensão de produtos

| Coluna | Tipo | Chave | Descrição / regra |
|---|---|---|---|
| `product_id` | int64 | PK | Identificador único. |
| `sku` | string | candidata | SKU único no catálogo. |
| `department` | string | — | Departamento comercial. |
| `category` | string | — | Categoria sintética dentro do departamento. |
| `unit_price` | float64 | — | Preço de venda positivo; bronze contém poucos nulos. |
| `cost_price` | float64 | — | Custo menor que o preço na geração normal. |
| `supplier_id` | int64 | — | Identificador do fornecedor. |
| `product_status` | string | — | `active` ou `discontinued`. |

### `orders` — fato de pedidos

| Coluna | Tipo | Chave | Descrição / regra |
|---|---|---|---|
| `order_id` | int64 | PK | Pedido único na gold; duplicado propositalmente na bronze. |
| `order_date` | datetime64 | — | Data do pedido no período de referência. |
| `customer_id` | int64 | FK | Referência a `customers.customer_id`. |
| `product_id` | int64 | FK | Referência a `products.product_id`. |
| `channel` | string | — | `app`, `web`, `store`, `marketplace`; bronze tem nulos. |
| `quantity` | int64 | — | Quantidade positiva; outliers de 25–79 unidades são injetados. |
| `unit_price_at_order` | float64 | — | Snapshot do preço no momento da venda. |
| `discount_rate` | float64 | — | Percentual de desconto entre 0 e 1. |
| `shipping_amount` | float64 | — | Frete; loja física possui frete zero. |
| `order_amount` | float64 | — | `quantity * unit_price * (1-discount) + shipping`. |
| `order_status` | string | — | `completed`, `cancelled`, `returned`, `pending`; bronze possui domínio inválido. |
| `delivery_days` | float64 | — | Dias de entrega; nulo para pedidos não concluídos. |

### `payments` — fato de pagamentos

| Coluna | Tipo | Chave | Descrição / regra |
|---|---|---|---|
| `payment_id` | int64 | PK | Identificador único do pagamento. |
| `order_id` | int64 | FK | Referência a `orders.order_id`; bronze possui órfãos. |
| `payment_date` | datetime64 | — | Data do pagamento, até dois dias após o pedido. |
| `payment_method` | string | — | `pix`, `credit_card`, `boleto`, `wallet`; bronze possui domínio inválido. |
| `payment_status` | string | — | `approved`, `refunded`, `failed`, `pending`. |
| `amount_paid` | float64 | — | Valor pago; zero quando falho/pendente. |
| `installments` | int64 | — | Parcelas; maior que 1 apenas para cartão. |

### `events` — eventos comportamentais

| Coluna | Tipo | Chave | Descrição / regra |
|---|---|---|---|
| `event_id` | int64 | PK | Identificador único do evento. |
| `event_timestamp` | datetime64 | — | Timestamp do evento; bronze possui um futuro. |
| `customer_id` | int64 | FK | Referência a cliente. |
| `order_id` | float64 | FK nullable | Pedido associado a checkout/compra; nulo em navegação. |
| `event_type` | string | — | `page_view`, `search`, `add_to_cart`, `checkout_started`, `purchase`, `support_contact`. |
| `device_type` | string | — | `mobile`, `desktop` ou `tablet`. |
| `session_duration_seconds` | int64 | — | Duração positiva da sessão, com cauda gamma. |

## 4. Lógica de geração

- **Sazonalidade:** pesos mensais crescentes ao longo do ano e pico em novembro/dezembro; Q4 concentra 36,65% dos pedidos.
- **Tendência temporal:** leve crescimento do volume no decorrer do ano.
- **Distribuições:** quantidade de itens discreta; ticket e preços com distribuição lognormal; duração de sessão com distribuição gamma; estados, segmentos e canais com pesos de negócio.
- **Correlações:** clientes premium recebem descontos maiores; app favorece Pix e wallet; loja não cobra frete; pedidos cancelados tendem a ter pagamento reembolsado/falho; entrega só é preenchida para pedidos concluídos.
- **Anomalias:** nulos inesperados, duplicidade de pedidos, status/método fora do domínio, chaves estrangeiras órfãs, timestamp futuro e tickets extremos. O inventário está em `data/bronze/defect_log.csv` e `.parquet`.

## 5. Validação estatística e de qualidade

| Evidência | Resultado observado |
|---|---:|
| Pedidos bronze | 30.002 |
| Pedidos gold | 29.985 |
| Clientes / produtos | 5.000 / 300 |
| Pagamentos / eventos | 30.000 / 60.000 |
| Mediana do ticket gold | R$ 168,42 |
| P95 / P99 do ticket gold | R$ 808,09 / R$ 1.522,19 |
| Média / P99 da quantidade | 2,07 / 6 |
| Taxa de pedidos concluídos | 76,03% |
| Taxa de pagamentos aprovados | 81,37% |
| Participação de eventos de compra | 8,07% |
| Q4 sobre pedidos | 36,65% |
| Pedidos gold com cliente válido | 29.985 / 29.985 |
| Pedidos gold com produto válido | 29.985 / 29.985 |
| Pagamentos gold com pedido válido | 29.970 / 29.970 |
| Regras automatizadas | 16 |
| Falhas bronze | 6 (5 críticas, 1 de completude; intencionais) |

As falhas críticas incluem `orders.pk_unique`, integridade referencial de pedidos/pagamentos, domínio de status e `events.timestamp_freshness` (um evento em `2026-04-01`); a falha não crítica é a completude de `orders.channel`. Isso demonstra o requisito do projeto de retornar código não zero quando checks críticos falharem. Após o processo de saneamento, a gold remove/corrige as falhas de negócio principais. Nulos restantes na gold são semânticos, principalmente `events.order_id` para navegação e `orders.delivery_days` para pedidos não concluídos.

## 6. Organização dos entregáveis

- `data/bronze/`: dados brutos com defeitos injetados, inventário de defeitos e `quality_runs`.
- `data/gold/`: dados tipados e saneados para análise.
- `contracts/`: contratos JSON por dataset.
- `reports/summary.json`: métricas reprodutíveis e fingerprint.
- `generate_dataset.py`: script completo, determinístico e executável.

## 7. Como usar

```bash
python3 generate_dataset.py
python3 -c "import pandas as pd; print(pd.read_parquet('data/gold/orders.parquet').head())"
```

Os Parquets são adequados para DuckDB, Polars, Spark/Databricks e consultas analíticas; os CSVs facilitam inspeção e integração com ferramentas de portfólio.
