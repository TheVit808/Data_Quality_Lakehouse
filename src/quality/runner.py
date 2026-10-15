from __future__ import annotations

from pathlib import Path
import uuid
import pandas as pd

from .checks import (
    check_domain,
    check_foreign_key,
    check_freshness,
    check_not_null,
    check_non_null_rate,
    check_positive,
    check_row_count,
    check_schema,
    check_unique,
)

RUN_ID = f"qr_{uuid.uuid4().hex[:12]}"
REFERENCE_TIME = "2025-12-31 23:59:59"


EXPECTED_SCHEMAS = {
    "customers": {
        "customer_id": "int64",
        "customer_segment": "object",
        "state": "object",
        "city": "object",
        "registration_date": "datetime64[ns]",
        "marketing_opt_in": "bool",
        "customer_status": "object",
    },
    "products": {
        "product_id": "int64",
        "sku": "object",
        "department": "object",
        "category": "object",
        "unit_price": "float64",
        "cost_price": "float64",
        "supplier_id": "int64",
        "product_status": "object",
    },
}


def run_customers(df):
    results = [
        check_schema(df, "customers", EXPECTED_SCHEMAS["customers"]),
        check_not_null(df, "customer_id", "customers"),
        check_unique(df, "customer_id", "customers"),
        check_domain(df, "customer_status", {"active", "inactive"}, "customers"),
        check_domain(df, "customer_segment", {"mass", "premium", "corporate"}, "customers"),
        check_non_null_rate(df, "state", "customers", minimum=0.99),
        check_row_count(df, "customers", minimum=4500, maximum=5500),
    ]
    return results


def run_products(df):
    results = [
        check_schema(df, "products", EXPECTED_SCHEMAS["products"]),
        check_not_null(df, "product_id", "products"),
        check_unique(df, "product_id", "products"),
        check_unique(df, "sku", "products"),
        check_positive(df, "unit_price", "products"),
        check_positive(df, "cost_price", "products"),
        check_domain(df, "product_status", {"active", "discontinued"}, "products"),
        check_row_count(df, "products", minimum=250, maximum=350),
    ]
    return results


def run_orders(df, customers, products):
    results = [
        check_not_null(df, "order_id", "orders"),
        check_unique(df, "order_id", "orders"),
        check_not_null(df, "customer_id", "orders"),
        check_foreign_key(df, "customer_id", customers, "customer_id", "orders"),
        check_foreign_key(df, "product_id", products, "product_id", "orders"),
        check_domain(df, "order_status", {"completed", "cancelled", "returned", "pending"}, "orders"),
        check_domain(df, "channel", {"app", "web", "store", "marketplace", "unknown"}, "orders"),
        check_positive(df, "quantity", "orders"),
        check_non_null_rate(df, "channel", "orders", minimum=0.998),
        check_row_count(df, "orders", minimum=28000, maximum=32000),
    ]
    return results


def run_payments(df, orders):
    results = [
        check_not_null(df, "payment_id", "payments"),
        check_unique(df, "payment_id", "payments"),
        check_foreign_key(df, "order_id", orders, "order_id", "payments"),
        check_domain(df, "payment_method", {"pix", "credit_card", "boleto", "wallet"}, "payments"),
        check_domain(df, "payment_status", {"approved", "refunded", "failed", "pending"}, "payments"),
        check_positive(df[df["payment_status"] == "approved"], "amount_paid", "payments"),
        check_row_count(df, "payments", minimum=28000, maximum=32000),
    ]
    return results


def run_events(df, customers, orders):
    results = [
        check_not_null(df, "event_id", "events"),
        check_unique(df, "event_id", "events"),
        check_foreign_key(df, "customer_id", customers, "customer_id", "events"),
        check_domain(df, "event_type", {"page_view", "search", "add_to_cart", "checkout_started", "purchase", "support_contact"}, "events"),
        check_domain(df, "device_type", {"mobile", "desktop", "tablet"}, "events"),
        check_freshness(df, "event_timestamp", "events", REFERENCE_TIME),
        check_positive(df, "session_duration_seconds", "events"),
        check_row_count(df, "events", minimum=55000, maximum=65000),
    ]
    # order_id é opcional: só valida referências quando preenchido.
    linked = df[df["order_id"].notna()]
    if len(linked):
        results.append(check_foreign_key(linked, "order_id", orders, "order_id", "events"))
    return results


def load_dataset(layer: str, dataset: str) -> pd.DataFrame:
    path = Path("data") / layer / f"{dataset}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
    return pd.read_parquet(path)


def run_all(layer="bronze"):
    customers = load_dataset(layer, "customers")
    products = load_dataset(layer, "products")
    orders = load_dataset(layer, "orders")
    payments = load_dataset(layer, "payments")
    events = load_dataset(layer, "events")

    results = []
    results += run_customers(customers)
    results += run_products(products)
    results += run_orders(orders, customers, products)
    results += run_payments(payments, orders)
    results += run_events(events, customers, orders)

    for result in results:
        result.run_id = RUN_ID
    return results