from collections import defaultdict
import pandas as pd

DEFAULT_WEIGHTS = {
    "critical": 5.0,
    "error": 3.0,
    "warning": 1.0,
}


def score_results(results, weights=None):
    weights = weights or DEFAULT_WEIGHTS
    rows = [result.to_dict() for result in results]
    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(columns=["dataset", "score", "checks", "passed", "failed", "critical_failures"])

    df["weight"] = df["severity"].map(weights).fillna(1.0)
    df["passed_numeric"] = (df["status"] == "PASS").astype(int)
    df["weighted_points"] = df["passed_numeric"] * df["weight"]

    summary = (
        df.groupby("dataset", as_index=False)
        .agg(
            total_weight=("weight", "sum"),
            earned_weight=("weighted_points", "sum"),
            checks=("status", "size"),
            passed=("passed_numeric", "sum"),
            failed=("status", lambda values: int((values == "FAIL").sum())),
            critical_failures=("severity", lambda values: int(((values == "critical") & (df.loc[values.index, "status"] == "FAIL")).sum())),
        )
    )
    summary["score"] = (100 * summary["earned_weight"] / summary["total_weight"]).round(2)
    return summary[["dataset", "score", "checks", "passed", "failed", "critical_failures"]]


def global_score(results, weights=None):
    weights = weights or DEFAULT_WEIGHTS
    if not results:
        return 0.0
    total = sum(weights.get(result.severity, 1.0) for result in results)
    earned = sum(weights.get(result.severity, 1.0) for result in results if result.status == "PASS")
    return round(100 * earned / total, 2) if total else 0.0