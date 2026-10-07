from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def read_source(dataset: str) -> pd.DataFrame:
    return pd.read_parquet(ROOT / "data" / "bronze" / dataset / "input.parquet")


def write_parquet(df: pd.DataFrame, layer: str, dataset: str) -> None:
    output = ROOT / "data" / layer / dataset
    output.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output / "part-000.parquet", index=False)


def build_bronze(dataset: str) -> None:
    # Bronze preserva o conteúdo recebido e adiciona metadados técnicos.
    pass


def build_silver(dataset: str) -> None:
    # Silver normaliza tipos, domínios e rejeições.
    pass


def build_gold() -> None:
    # Gold materializa dimensões e fatos do modelo estrela.
    pass


if __name__ == "__main__":
    build_gold()