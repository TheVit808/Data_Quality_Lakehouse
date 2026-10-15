from __future__ import annotations

import time
from typing import Any, Iterable
import pandas as pd

from .models import CheckResult


def _execute(dataset, rule, severity, threshold, fn):
    started = time.perf_counter()
    try:
        passed, observed, failed_rows, detail = fn()
    except Exception as exc:
        passed = False
        observed = "exception"
        failed_rows = 0
        detail = f"{type(exc).__name__}: {exc}"
    duration_ms = round((time.perf_counter() - started) * 1000, 3)
    return CheckResult(
        dataset=dataset,
        rule=rule,
        status="PASS" if passed else "FAIL",
        severity=severity,
        observed_value=observed,
        threshold=threshold,
        failed_rows=int(failed_rows),
        detail=detail,
        duration_ms=duration_ms,
    )


def check_schema(df: pd.DataFrame, dataset: str, expected: dict[str, str], severity="critical"):
    def evaluate():
        actual = {name: str(dtype) for name, dtype in df.dtypes.items()}
        missing = sorted(set(expected) - set(actual))
        unexpected = sorted(set(actual) - set(expected))
        wrong_types = sorted(
            name for name in expected.keys() & actual.keys()
            if expected[name] != actual[name]
        )
        passed = not missing and not unexpected and not wrong_types
        detail = f"missing={missing}; unexpected={unexpected}; wrong_types={wrong_types}"
        return passed, detail, len(missing) + len(unexpected) + len(wrong_types), detail

    return _execute(dataset, "schema_columns_and_types", severity, expected, evaluate)


def check_not_null(df: pd.DataFrame, column: str, dataset: str, severity="critical"):
    rule = f"{column}_not_null"

    def evaluate():
        failed_rows = int(df[column].isna().sum())
        observed = round(float(df[column].notna().mean()), 6) if len(df) else 0.0
        return failed_rows == 0, observed, failed_rows, f"null_rows={failed_rows}"

    return _execute(dataset, rule, severity, 1.0, evaluate)


def check_unique(df: pd.DataFrame, column: str, dataset: str, severity="critical"):
    rule = f"{column}_unique"

    def evaluate():
        duplicates = int(df[column].duplicated(keep=False).sum())
        observed = int(df[column].nunique(dropna=False))
        return duplicates == 0, observed, duplicates, f"duplicate_rows={duplicates}"

    return _execute(dataset, rule, severity, "unique", evaluate)


def check_domain(df: pd.DataFrame, column: str, allowed: Iterable[Any], dataset: str, severity="error"):
    rule = f"{column}_domain"
    allowed = set(allowed)

    def evaluate():
        invalid = ~df[column].isin(allowed)
        failed_rows = int(invalid.sum())
        observed = round(float((~invalid).mean()), 6) if len(df) else 0.0
        values = df.loc[invalid, column].drop_duplicates().head(10).tolist()
        return failed_rows == 0, observed, failed_rows, f"invalid_values={values}"

    return _execute(dataset, rule, severity, sorted(allowed), evaluate)


def check_non_null_rate(df, column, dataset, minimum=0.99, severity="warning"):
    rule = f"{column}_completeness"

    def evaluate():
        observed = round(float(df[column].notna().mean()), 6) if len(df) else 0.0
        failed_rows = int(df[column].isna().sum())
        return observed >= minimum, observed, failed_rows, f"null_rows={failed_rows}"

    return _execute(dataset, rule, severity, minimum, evaluate)


def check_foreign_key(df, column, parent_df, parent_column, dataset, severity="critical"):
    rule = f"{column}_referential_integrity"

    def evaluate():
        invalid = ~df[column].isin(parent_df[parent_column])
        failed_rows = int(invalid.sum())
        observed = round(float((~invalid).mean()), 6) if len(df) else 0.0
        return failed_rows == 0, observed, failed_rows, f"orphan_rows={failed_rows}"

    return _execute(dataset, rule, severity, 1.0, evaluate)


def check_positive(df, column, dataset, severity="error"):
    rule = f"{column}_positive"

    def evaluate():
        invalid = df[column].isna() | (df[column] <= 0)
        failed_rows = int(invalid.sum())
        observed = round(float((~invalid).mean()), 6) if len(df) else 0.0
        return failed_rows == 0, observed, failed_rows, f"non_positive_rows={failed_rows}"

    return _execute(dataset, rule, severity, 1.0, evaluate)


def check_freshness(df, column, dataset, reference_time, severity="critical"):
    rule = f"{column}_freshness"

    def evaluate():
        values = pd.to_datetime(df[column], errors="coerce")
        invalid = values.isna() | (values > pd.Timestamp(reference_time))
        failed_rows = int(invalid.sum())
        observed = round(float((~invalid).mean()), 6) if len(df) else 0.0
        return failed_rows == 0, observed, failed_rows, f"future_or_invalid_rows={failed_rows}"

    return _execute(dataset, rule, severity, 1.0, evaluate)


def check_row_count(df, dataset, minimum, maximum=None, severity="error"):
    rule = "row_count_expected"

    def evaluate():
        count = len(df)
        passed = count >= minimum and (maximum is None or count <= maximum)
        threshold = f"min={minimum}; max={maximum}"
        return passed, count, 0 if passed else 1, threshold

    return _execute(dataset, rule, severity, f"min={minimum}; max={maximum}", evaluate)