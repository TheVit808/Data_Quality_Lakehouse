# Relatório de qualidade — `qr_06054b635e9f`

**Checks executados:** 41  
**Falhas:** 2  
**Falhas críticas:** 2

## Score por dataset

| dataset   |   score |   checks |   passed |   failed |   critical_failures |
|:----------|--------:|---------:|---------:|---------:|--------------------:|
| customers |   80    |        7 |        6 |        1 |                   1 |
| events    |  100    |        9 |        9 |        0 |                   0 |
| orders    |  100    |       10 |       10 |        0 |                   0 |
| payments  |  100    |        7 |        7 |        0 |                   0 |
| products  |   84.38 |        8 |        7 |        1 |                   1 |

## Falhas encontradas

| dataset   | rule                     | severity   | observed_value                                                                                  | threshold                                                                                                                                                                                    |   failed_rows | detail                                                                                          |
|:----------|:-------------------------|:-----------|:------------------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------:|:------------------------------------------------------------------------------------------------|
| customers | schema_columns_and_types | critical   | missing=[]; unexpected=[]; wrong_types=['city', 'customer_segment', 'customer_status', 'state'] | {'customer_id': 'int64', 'customer_segment': 'object', 'state': 'object', 'city': 'object', 'registration_date': 'datetime64[ns]', 'marketing_opt_in': 'bool', 'customer_status': 'object'}  |             4 | missing=[]; unexpected=[]; wrong_types=['city', 'customer_segment', 'customer_status', 'state'] |
| products  | schema_columns_and_types | critical   | missing=[]; unexpected=[]; wrong_types=['category', 'department', 'product_status', 'sku']      | {'product_id': 'int64', 'sku': 'object', 'department': 'object', 'category': 'object', 'unit_price': 'float64', 'cost_price': 'float64', 'supplier_id': 'int64', 'product_status': 'object'} |             4 | missing=[]; unexpected=[]; wrong_types=['category', 'department', 'product_status', 'sku']      |

## Interpretação

- Falhas `critical` devem bloquear o consumo ou o merge quando integradas à CI.
- Falhas `error` devem gerar plano de correção.
- Falhas `warning` devem ser acompanhadas por tendência.