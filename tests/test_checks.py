import pandas as pd

from src.quality.checks import (
    check_domain,
    check_not_null,
    check_unique,
    check_positive,
)


def test_not_null_passes_when_column_is_complete():
    df = pd.DataFrame({"id": [1, 2, 3]})
    result = check_not_null(df, "id", "test")
    assert result.status == "PASS"
    assert result.failed_rows == 0


def test_not_null_fails_when_column_has_null():
    df = pd.DataFrame({"id": [1, None, 3]})
    result = check_not_null(df, "id", "test")
    assert result.status == "FAIL"
    assert result.failed_rows == 1


def test_unique_fails_on_duplicate():
    df = pd.DataFrame({"id": [1, 1, 2]})
    result = check_unique(df, "id", "test")
    assert result.status == "FAIL"
    assert result.failed_rows == 2


def test_domain_fails_on_unexpected_value():
    df = pd.DataFrame({"status": ["active", "invalid"]})
    result = check_domain(df, "status", {"active", "inactive"}, "test")
    assert result.status == "FAIL"


def test_positive_rejects_zero_and_negative():
    df = pd.DataFrame({"quantity": [2, 0, -1]})
    result = check_positive(df, "quantity", "test")
    assert result.status == "FAIL"
    assert result.failed_rows == 2