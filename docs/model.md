| Item | Decisão da Trilha A |
| --- | --- |
| Dimensões | `customers`, `products` |
| Fatos | `orders`, `payments`, `events` |
| Formato | Parquet |
| Contratos | YAML versionado |
| Bronze | Preserva a origem |
| Silver | Padroniza e valida |
| Gold | Modelo estrela para consumo |

customers 1 ─── N orders N ─── 1 products
orders    1 ─── 1 payments
customers 1 ─── N events
orders    1 ─── N events (order_id opcional)