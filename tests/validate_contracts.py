from pathlib import Path
import yaml

REQUIRED_TOP_LEVEL = {"contract", "schema", "quality", "compatibility"}
REQUIRED_CONTRACT_FIELDS = {
    "name", "version", "owner", "update", "governance", "storage"
}


def test_validate_contract(path: Path):
    content = yaml.safe_load(path.read_text(encoding="utf-8"))

    missing = REQUIRED_TOP_LEVEL - set(content)
    assert not missing, f"{path}: seções ausentes: {sorted(missing)}"

    contract = content["contract"]
    missing = REQUIRED_CONTRACT_FIELDS - set(contract)
    assert not missing, f"{path}: campos ausentes: {sorted(missing)}"

    columns = content["schema"].get("columns", [])
    names = [column["name"] for column in columns]
    assert len(names) == len(set(names)), f"{path}: coluna duplicada"

    primary_key = content["schema"].get("primary_key", [])
    assert primary_key, f"{path}: primary_key ausente"
    assert set(primary_key).issubset(names), f"{path}: primary_key desconhecida"


def test_all_contracts():
    paths = sorted(Path("contracts").glob("*.yml"))
    assert len(paths) >= 5, "Esperados pelo menos cinco contratos YAML"
    for path in paths:
        test_validate_contract(path)