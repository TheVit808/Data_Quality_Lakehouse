from pathlib import Path
import pandas as pd


def results_to_frame(results):
    df = pd.DataFrame([result.to_dict() for result in results])
    
    # Converte colunas problemáticas de tipos mistos/structs para string
    for col in ["observed_value", "threshold"]:
        if col in df.columns:
            df[col] = df[col].astype(str)
            
    return df


def persist_quality_runs(results, output_dir="data/gold"):
    df = results_to_frame(results)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    csv_path = output / "quality_runs.csv"
    parquet_path = output / "quality_runs.parquet"

    # append histórico, sem apagar execuções anteriores
    if parquet_path.exists():
        try:
            previous = pd.read_parquet(parquet_path)
            for col in ["observed_value", "threshold"]:
                if col in previous.columns:
                    previous[col] = previous[col].astype(str)
            df = pd.concat([previous, df], ignore_index=True)
        except Exception:
            # Caso o arquivo anterior esteja corrompido ou com schema incompatível
            pass

    df.to_csv(csv_path, index=False)
    df.to_parquet(parquet_path, index=False)
    return parquet_path


def persist_scores(scores, output_dir="reports"):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    path = output / "quality_scores.parquet"
    scores.to_parquet(path, index=False)
    scores.to_csv(output / "quality_scores.csv", index=False)
    return path