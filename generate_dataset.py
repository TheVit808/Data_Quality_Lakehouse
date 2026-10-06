from pathlib import Path
import json
import hashlib
import numpy as np
import pandas as pd

SEED = 20251006
rng = np.random.default_rng(SEED)
BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
BRONZE = DATA / "bronze"
GOLD = DATA / "gold"
REPORTS = BASE / "reports"
CONTRACTS = BASE / "contracts"
for p in [BRONZE, GOLD, REPORTS, CONTRACTS]:
    p.mkdir(parents=True, exist_ok=True)

# ----------------------------
# Dimensions
# ----------------------------
N_CUSTOMERS = 5000
N_PRODUCTS = 300
N_ORDERS = 30000
N_EVENTS = 60000
START = pd.Timestamp("2025-01-01")
END = pd.Timestamp("2025-12-31 23:59:59")

states = np.array(["SP", "RJ", "MG", "PR", "SC", "RS", "BA", "PE", "GO", "ES"])
state_weights = np.array([.30, .13, .12, .10, .08, .08, .07, .05, .04, .03])
segments = np.array(["mass", "premium", "corporate"])
segment_weights = np.array([.68, .25, .07])
channels = np.array(["app", "web", "store", "marketplace"])
channel_weights = np.array([.42, .28, .18, .12])

customer_id = np.arange(1, N_CUSTOMERS + 1)
customer_segment = rng.choice(segments, N_CUSTOMERS, p=segment_weights)
customer_state = rng.choice(states, N_CUSTOMERS, p=state_weights)
registration = START - pd.to_timedelta(rng.integers(0, 5 * 365, N_CUSTOMERS), unit="D")
dim_customers = pd.DataFrame({
    "customer_id": customer_id,
    "customer_segment": customer_segment,
    "state": customer_state,
    "city": np.array([f"cidade_{s.lower()}_{i%20+1:02d}" for i, s in enumerate(customer_state)]),
    "registration_date": pd.to_datetime(registration).date,
    "marketing_opt_in": rng.choice([True, False], N_CUSTOMERS, p=[.64, .36]),
    "customer_status": rng.choice(["active", "inactive"], N_CUSTOMERS, p=[.91, .09]),
})

departments = np.array(["eletronicos", "casa", "beleza", "esportes", "moda", "mercado"])
product_id = np.arange(1, N_PRODUCTS + 1)
department = rng.choice(departments, N_PRODUCTS, p=[.22, .19, .14, .13, .15, .17])
base_price = np.exp(rng.normal(np.log(95), .85, N_PRODUCTS)).clip(8, 2500)
dim_products = pd.DataFrame({
    "product_id": product_id,
    "sku": [f"SKU-{i:06d}" for i in product_id],
    "department": department,
    "category": [f"{d}_cat_{i%4+1}" for i, d in enumerate(department)],
    "unit_price": np.round(base_price, 2),
    "cost_price": np.round(base_price * rng.uniform(.42, .78, N_PRODUCTS), 2),
    "supplier_id": rng.integers(1001, 1061, N_PRODUCTS),
    "product_status": rng.choice(["active", "discontinued"], N_PRODUCTS, p=[.94, .06]),
})

# ----------------------------
# Facts with seasonality and business correlations
# ----------------------------
order_id = np.arange(1, N_ORDERS + 1)
# seasonality: stronger Nov/Dec, weekends slightly lower for store; business trend upward
all_days = pd.date_range(START, END, freq="D")
month_factor = np.array([.88, .86, .92, .95, .98, 1.00, 1.01, 1.00, 1.05, 1.12, 1.55, 1.75])
day_of_year = all_days.dayofyear.to_numpy()
trend = 0.88 + (day_of_year / 365) * .24
weights = month_factor[all_days.month.to_numpy() - 1] * trend
# resample dates to respect weights approximately
order_date = pd.Series(rng.choice(all_days, N_ORDERS, p=weights / weights.sum()))
order_date = pd.to_datetime(order_date).sort_values().reset_index(drop=True)
customer_choices = rng.choice(customer_id, N_ORDERS)
product_choices = rng.choice(product_id, N_ORDERS)
qty = rng.choice([1, 2, 3, 4, 5, 6], N_ORDERS, p=[.46, .27, .14, .07, .04, .02])
order_channel = rng.choice(channels, N_ORDERS, p=channel_weights)
status = rng.choice(["completed", "cancelled", "returned", "pending"], N_ORDERS, p=[.76, .08, .07, .09])
price = dim_products.set_index("product_id").loc[product_choices, "unit_price"].to_numpy()
segment_lookup = dim_customers.set_index("customer_id").loc[customer_choices, "customer_segment"].to_numpy()
discount = np.where(segment_lookup == "premium", rng.uniform(.05, .18, N_ORDERS), rng.uniform(0, .12, N_ORDERS))
discount = np.round(discount, 4)
shipping = np.where(order_channel == "store", 0, rng.uniform(4.9, 39.9, N_ORDERS))
gross = qty * price
net = np.round(gross * (1 - discount) + shipping, 2)
dim_orders = pd.DataFrame({
    "order_id": order_id,
    "order_date": order_date.dt.date,
    "customer_id": customer_choices,
    "product_id": product_choices,
    "channel": order_channel,
    "quantity": qty,
    "unit_price_at_order": np.round(price, 2),
    "discount_rate": discount,
    "shipping_amount": np.round(shipping, 2),
    "order_amount": net,
    "order_status": status,
    "delivery_days": np.where(status == "completed", rng.poisson(4, N_ORDERS).clip(1, 16), np.nan),
})

# Payments: mostly one per order, with payment method correlated to channel
payment_method = np.where(order_channel == "app", rng.choice(["pix", "credit_card", "wallet"], N_ORDERS, p=[.42, .40, .18]), rng.choice(["pix", "credit_card", "boleto", "wallet"], N_ORDERS, p=[.28, .48, .16, .08]))
pay_status = np.where(status == "cancelled", rng.choice(["refunded", "failed"], N_ORDERS, p=[.7, .3]), np.where(status == "pending", rng.choice(["pending", "approved"], N_ORDERS, p=[.65, .35]), rng.choice(["approved", "refunded", "failed"], N_ORDERS, p=[.94, .04, .02])))
fact_payments = pd.DataFrame({
    "payment_id": np.arange(1, N_ORDERS + 1),
    "order_id": order_id,
    "payment_date": pd.to_datetime(order_date) + pd.to_timedelta(rng.integers(0, 3, N_ORDERS), unit="D"),
    "payment_method": payment_method,
    "payment_status": pay_status,
    "amount_paid": np.round(np.where(pay_status == "approved", net, np.where(pay_status == "refunded", net, 0)), 2),
    "installments": np.where(payment_method == "credit_card", rng.choice([1, 2, 3, 6, 12], N_ORDERS, p=[.35, .22, .18, .15, .10]), 1),
})
fact_payments["payment_date"] = fact_payments["payment_date"].dt.date

# Events: behavior correlated with customer status and order activity
order_map = dim_orders[["order_id", "customer_id", "order_date"]].copy()
event_customer = rng.choice(customer_id, N_EVENTS)
event_types = rng.choice(["page_view", "search", "add_to_cart", "checkout_started", "purchase", "support_contact"], N_EVENTS, p=[.38, .22, .16, .10, .08, .06])
event_date = pd.to_datetime(rng.choice(all_days, N_EVENTS))
# map a plausible order to 75% of purchase/checkouts; null is valid for browse events
candidate_orders = rng.integers(1, N_ORDERS + 1, N_EVENTS)
event_order = np.where(np.isin(event_types, ["purchase", "checkout_started"]), candidate_orders, np.nan)
fact_events = pd.DataFrame({
    "event_id": np.arange(1, N_EVENTS + 1),
    "event_timestamp": event_date + pd.to_timedelta(rng.integers(0, 86400, N_EVENTS), unit="s"),
    "customer_id": event_customer,
    "order_id": event_order,
    "event_type": event_types,
    "device_type": rng.choice(["mobile", "desktop", "tablet"], N_EVENTS, p=[.62, .33, .05]),
    "session_duration_seconds": rng.gamma(2.2, 95, N_EVENTS).clip(5, 3600).round().astype(int),
})

# Normalize date/time representations
for df in [dim_customers, dim_products, dim_orders, fact_payments, fact_events]:
    for col in df.columns:
        if "date" in col or "timestamp" in col:
            df[col] = pd.to_datetime(df[col])

# ----------------------------
# Defect injection for bronze
# ----------------------------
defect_log = []
def inject(df, dataset, rule, rows, detail):
    for r in rows:
        defect_log.append({"dataset": dataset, "rule": rule, "row_number": int(r), "detail": detail})

bronze = {
    "customers": dim_customers.copy(),
    "products": dim_products.copy(),
    "orders": dim_orders.copy(),
    "payments": fact_payments.copy(),
    "events": fact_events.copy(),
}
# Nullability defects: non-key attributes
ix = rng.choice(N_CUSTOMERS, 50, replace=False); bronze["customers"].loc[ix, "state"] = None; inject(bronze["customers"], "customers", "completeness_state", ix, "state nulo inesperado")
ix = rng.choice(N_ORDERS, 90, replace=False); bronze["orders"].loc[ix, "channel"] = None; inject(bronze["orders"], "orders", "completeness_channel", ix, "channel nulo inesperado")
ix = rng.choice(N_PRODUCTS, 12, replace=False); bronze["products"].loc[ix, "unit_price"] = np.nan; inject(bronze["products"], "products", "completeness_unit_price", ix, "preço nulo inesperado")
# Domain defects
ix = rng.choice(N_ORDERS, 35, replace=False); bronze["orders"].loc[ix, "order_status"] = "in_review"; inject(bronze["orders"], "orders", "domain_order_status", ix, "status fora do domínio")
ix = rng.choice(N_ORDERS, 25, replace=False); bronze["orders"].loc[ix, "quantity"] = 0; inject(bronze["orders"], "orders", "positive_quantity", ix, "quantidade não positiva")
ix = rng.choice(N_PAYMENTS if False else N_ORDERS, 20, replace=False); bronze["payments"].loc[ix, "payment_method"] = "crypto"; inject(bronze["payments"], "payments", "domain_payment_method", ix, "método fora do domínio")
# Referential defects
ix = rng.choice(N_ORDERS, 15, replace=False); bronze["orders"].loc[ix, "customer_id"] = N_CUSTOMERS + np.arange(1, 16); inject(bronze["orders"], "orders", "referential_customer_id", ix, "cliente inexistente")
ix = rng.choice(N_ORDERS, 15, replace=False); bronze["payments"].loc[ix, "order_id"] = N_ORDERS + np.arange(1, 16); inject(bronze["payments"], "payments", "referential_order_id", ix, "pedido inexistente")
# Duplicate business keys
bronze["orders"] = pd.concat([bronze["orders"], bronze["orders"].iloc[[1234, 5678]].copy()], ignore_index=True)
inject(bronze["orders"], "orders", "uniqueness_order_id", [N_ORDERS, N_ORDERS + 1], "pedido duplicado")
# Freshness defect: future timestamp
bronze["events"].loc[0, "event_timestamp"] = pd.Timestamp("2026-04-01")
inject(bronze["events"], "events", "freshness_event_timestamp", [0], "timestamp futuro ao período de referência")
# Outliers: legitimate but rare business extremes
outlier_ix = rng.choice(N_ORDERS, 30, replace=False)
bronze["orders"].loc[outlier_ix, "quantity"] = rng.integers(25, 80, len(outlier_ix))
bronze["orders"].loc[outlier_ix, "order_amount"] *= rng.uniform(2.5, 6.0, len(outlier_ix))
inject(bronze["orders"], "orders", "outlier_order_amount", outlier_ix, "ticket e quantidade extremos")

# Gold is a clean, typed layer derived from bronze by deterministic corrections/filtering.
gold = {k: v.copy() for k, v in bronze.items()}
gold["customers"]["state"] = gold["customers"]["state"].fillna("NA")
gold["products"]["unit_price"] = gold["products"]["unit_price"].fillna(gold["products"]["unit_price"].median())
gold["orders"]["channel"] = gold["orders"]["channel"].fillna("unknown")
gold["orders"] = gold["orders"].drop_duplicates(subset=["order_id"], keep="first")
gold["orders"]["order_status"] = gold["orders"]["order_status"].where(gold["orders"]["order_status"].isin(["completed", "cancelled", "returned", "pending"]), "pending")
gold["orders"]["quantity"] = gold["orders"]["quantity"].clip(lower=1)
gold["orders"] = gold["orders"].loc[gold["orders"]["customer_id"].isin(gold["customers"]["customer_id"])]
gold["payments"]["payment_method"] = gold["payments"]["payment_method"].where(gold["payments"]["payment_method"].isin(["pix", "credit_card", "boleto", "wallet"]), "wallet")
gold["payments"] = gold["payments"].loc[gold["payments"]["order_id"].isin(gold["orders"]["order_id"])]
gold["events"]["event_timestamp"] = gold["events"]["event_timestamp"].where(gold["events"]["event_timestamp"] <= END, END)

# Write outputs and contracts
for layer, datasets in [(BRONZE, bronze), (GOLD, gold)]:
    for name, df in datasets.items():
        df.to_csv(layer / f"{name}.csv", index=False)
        df.to_parquet(layer / f"{name}.parquet", index=False, engine="pyarrow")

schemas = {
    "customers": {"primary_key": ["customer_id"], "columns": {c: str(t) for c, t in dim_customers.dtypes.items()}, "owner": "Data Platform", "frequency": "daily", "sla_minutes": 60, "classification": "internal", "sensitivity": "personal_low"},
    "products": {"primary_key": ["product_id"], "columns": {c: str(t) for c, t in dim_products.dtypes.items()}, "owner": "Data Platform", "frequency": "daily", "sla_minutes": 60, "classification": "internal", "sensitivity": "non_personal"},
    "orders": {"primary_key": ["order_id"], "foreign_keys": {"customer_id": "customers.customer_id", "product_id": "products.product_id"}, "columns": {c: str(t) for c, t in dim_orders.dtypes.items()}, "owner": "Commerce Analytics", "frequency": "hourly", "sla_minutes": 30, "classification": "confidential", "sensitivity": "personal_indirect"},
    "payments": {"primary_key": ["payment_id"], "foreign_keys": {"order_id": "orders.order_id"}, "columns": {c: str(t) for c, t in fact_payments.dtypes.items()}, "owner": "Payments", "frequency": "hourly", "sla_minutes": 15, "classification": "confidential", "sensitivity": "financial"},
    "events": {"primary_key": ["event_id"], "foreign_keys": {"customer_id": "customers.customer_id", "order_id": "orders.order_id (nullable)"}, "columns": {c: str(t) for c, t in fact_events.dtypes.items()}, "owner": "Digital Analytics", "frequency": "15min", "sla_minutes": 10, "classification": "internal", "sensitivity": "behavioral"},
}
for name, contract in schemas.items():
    (CONTRACTS / f"{name}.json").write_text(json.dumps(contract, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

# 12+ automated quality rules over bronze, persisted as quality_runs.
def check(dataset, rule, passed, observed, threshold, severity="warning", detail=""):
    quality_rows.append({"run_id": run_id, "run_timestamp": run_ts, "dataset": dataset, "rule": rule, "status": "PASS" if passed else "FAIL", "severity": severity, "observed_value": str(observed), "threshold": str(threshold), "detail": detail})

quality_rows = []
run_id = "qr_20251006_001"
run_ts = pd.Timestamp("2025-12-31 23:59:59")
allowed_status = {"completed", "cancelled", "returned", "pending"}
check("customers", "schema_columns", set(bronze["customers"].columns) == set(dim_customers.columns), len(bronze["customers"].columns), len(dim_customers.columns), "critical")
check("customers", "pk_not_null", bronze["customers"].customer_id.notna().all(), int(bronze["customers"].customer_id.isna().sum()), 0, "critical")
check("customers", "pk_unique", bronze["customers"].customer_id.is_unique, int(bronze["customers"].customer_id.duplicated().sum()), 0, "critical")
check("customers", "state_completeness", bronze["customers"].state.notna().mean() >= 0.99, bronze["customers"].state.notna().mean(), 0.99, "warning")
check("products", "unit_price_positive", (bronze["products"].unit_price.dropna() > 0).mean() == 1.0, (bronze["products"].unit_price.dropna() > 0).mean(), 1.0, "critical")
check("products", "sku_unique", bronze["products"].sku.is_unique, int(bronze["products"].sku.duplicated().sum()), 0, "critical")
check("orders", "pk_unique", bronze["orders"].order_id.is_unique, int(bronze["orders"].order_id.duplicated().sum()), 0, "critical")
check("orders", "customer_referential_integrity", bronze["orders"].customer_id.isin(bronze["customers"].customer_id).mean() == 1.0, bronze["orders"].customer_id.isin(bronze["customers"].customer_id).mean(), 1.0, "critical")
check("orders", "status_domain", bronze["orders"].order_status.isin(allowed_status).mean() >= 0.999, bronze["orders"].order_status.isin(allowed_status).mean(), 0.999, "critical")
check("orders", "quantity_positive", (bronze["orders"].quantity > 0).mean() >= 0.999, (bronze["orders"].quantity > 0).mean(), 0.999, "critical")
check("orders", "channel_completeness", bronze["orders"].channel.notna().mean() >= 0.998, bronze["orders"].channel.notna().mean(), 0.998)
check("payments", "order_referential_integrity", bronze["payments"].order_id.isin(bronze["orders"].order_id).mean() == 1.0, bronze["payments"].order_id.isin(bronze["orders"].order_id).mean(), 1.0, "critical")
check("payments", "payment_method_domain", bronze["payments"].payment_method.isin({"pix", "credit_card", "boleto", "wallet"}).mean() >= 0.999, bronze["payments"].payment_method.isin({"pix", "credit_card", "boleto", "wallet"}).mean(), 0.999, "critical")
check("events", "event_id_unique", bronze["events"].event_id.is_unique, 0, "=0", "critical")
check("events", "timestamp_freshness", (bronze["events"].event_timestamp <= END).mean() == 1.0, (bronze["events"].event_timestamp <= END).mean(), 1.0, "critical")
check("events", "customer_referential_integrity", bronze["events"].customer_id.isin(bronze["customers"].customer_id).mean() == 1.0, bronze["events"].customer_id.isin(bronze["customers"].customer_id).mean(), 1.0, "critical")
quality_runs = pd.DataFrame(quality_rows)
quality_runs.to_csv(BRONZE / "quality_runs.csv", index=False)
quality_runs.to_parquet(BRONZE / "quality_runs.parquet", index=False)
quality_runs.to_csv(GOLD / "quality_runs.csv", index=False)
quality_runs.to_parquet(GOLD / "quality_runs.parquet", index=False)
pd.DataFrame(defect_log).to_csv(BRONZE / "defect_log.csv", index=False)
pd.DataFrame(defect_log).to_parquet(BRONZE / "defect_log.parquet", index=False)

# Executive summary with reproducibility hash and statistics.
summary = {
    "seed": SEED,
    "period": {"start": str(START.date()), "end": str(END.date())},
    "row_counts_bronze": {k: int(len(v)) for k, v in bronze.items()},
    "row_counts_gold": {k: int(len(v)) for k, v in gold.items()},
    "defect_count": len(defect_log),
    "quality_checks": int(len(quality_runs)),
    "failed_checks": int((quality_runs.status == "FAIL").sum()),
    "critical_failures": int(((quality_runs.status == "FAIL") & (quality_runs.severity == "critical")).sum()),
    "key_metrics": {
        "gross_order_amount_bronze": float(bronze["orders"].order_amount.sum()),
        "median_order_amount": float(gold["orders"].order_amount.median()),
        "completed_order_rate": float((gold["orders"].order_status == "completed").mean()),
        "approved_payment_rate": float((gold["payments"].payment_status == "approved").mean()),
        "event_purchase_share": float((gold["events"].event_type == "purchase").mean()),
    },
    "quality_scores_by_dataset": quality_runs.groupby("dataset").apply(lambda x: round((x.status == "PASS").mean() * 100, 2), include_groups=False).to_dict(),
}
summary["dataset_fingerprint"] = hashlib.sha256(pd.util.hash_pandas_object(gold["orders"], index=True).values.tobytes()).hexdigest()
(REPORTS / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
