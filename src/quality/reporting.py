from pathlib import Path
import pandas as pd


def build_markdown(results, scores, run_id):
    result_df = pd.DataFrame([r.to_dict() for r in results])
    failures = result_df[result_df["status"] == "FAIL"].copy()

    lines = [
        f"# Relatório de qualidade — `{run_id}`",
        "",
        f"**Checks executados:** {len(result_df)}  ",
        f"**Falhas:** {len(failures)}  ",
        f"**Falhas críticas:** {int(((result_df.status == 'FAIL') & (result_df.severity == 'critical')).sum())}",
        "",
        "## Score por dataset",
        "",
        scores.to_markdown(index=False) if not scores.empty else "Sem scores.",
        "",
        "## Falhas encontradas",
        "",
    ]

    if failures.empty:
        lines.append("Nenhuma falha encontrada.")
    else:
        lines.append(failures[["dataset", "rule", "severity", "observed_value", "threshold", "failed_rows", "detail"]].to_markdown(index=False))

    lines += [
        "",
        "## Interpretação",
        "",
        "- Falhas `critical` devem bloquear o consumo ou o merge quando integradas à CI.",
        "- Falhas `error` devem gerar plano de correção.",
        "- Falhas `warning` devem ser acompanhadas por tendência.",
    ]
    return "\n".join(lines)


def build_html(results, scores, run_id):
    result_df = pd.DataFrame([r.to_dict() for r in results])
    failures = result_df[result_df["status"] == "FAIL"]
    global_score = float(scores["score"].mean()) if not scores.empty else 0.0

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Relatório de qualidade {run_id}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2937; }}
h1 {{ color: #0f3d5e; }}
.cards {{ display: flex; gap: 16px; margin: 20px 0; }}
.card {{ border: 1px solid #d1d5db; border-radius: 8px; padding: 16px; min-width: 150px; }}
.card strong {{ display: block; font-size: 28px; }}
table {{ border-collapse: collapse; width: 100%; margin-bottom: 24px; }}
th, td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; }}
th {{ background: #e5eef5; }}
.fail {{ background: #fee2e2; }}
</style>
</head>
<body>
<h1>Relatório de qualidade — {run_id}</h1>
<div class="cards">
<div class="card">Score médio<strong>{global_score:.2f}</strong></div>
<div class="card">Checks<strong>{len(result_df)}</strong></div>
<div class="card">Falhas<strong>{len(failures)}</strong></div>
</div>
<h2>Score por dataset</h2>
{scores.to_html(index=False, classes='scores')}
<h2>Falhas</h2>
{failures.to_html(index=False, classes='fail') if not failures.empty else '<p>Nenhuma falha encontrada.</p>'}
</body>
</html>"""


def write_reports(results, scores, run_id, output_dir="reports"):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    markdown = build_markdown(results, scores, run_id)
    html = build_html(results, scores, run_id)
    (output / "quality_report.md").write_text(markdown, encoding="utf-8")
    (output / "quality_report.html").write_text(html, encoding="utf-8")