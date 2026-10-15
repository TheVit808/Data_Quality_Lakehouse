import argparse
import sys

from .persistence import persist_quality_runs, persist_scores
from .reporting import write_reports
from .runner import run_all
from .scoring import global_score, score_results


def main():
    parser = argparse.ArgumentParser(description="Executa checks de qualidade")
    parser.add_argument("--layer", default="bronze", choices=["bronze", "gold"])
    parser.add_argument("--fail-on-critical", action="store_true")
    args = parser.parse_args()

    results = run_all(layer=args.layer)
    scores = score_results(results)
    persist_quality_runs(results)
    persist_scores(scores)
    write_reports(results, scores, results[0].run_id if results else "empty")

    critical_failures = [
        r for r in results
        if r.status == "FAIL" and r.severity == "critical"
    ]

    print(f"Checks executados: {len(results)}")
    print(f"Score global: {global_score(results):.2f}")
    print(f"Falhas críticas: {len(critical_failures)}")
    print(scores.to_string(index=False))

    if args.fail_on_critical and critical_failures:
        print("Falha crítica detectada; encerrando com código 1.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())