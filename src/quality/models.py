from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass
class CheckResult:
    dataset: str
    rule: str
    status: str
    severity: str
    observed_value: Any
    threshold: Any
    failed_rows: int = 0
    detail: str = ""
    duration_ms: float = 0.0
    executed_at: str = ""
    run_id: str = ""

    def __post_init__(self):
        if not self.executed_at:
            self.executed_at = datetime.now(timezone.utc).isoformat()
        if self.status not in {"PASS", "FAIL"}:
            raise ValueError("status deve ser PASS ou FAIL")
        if self.severity not in {"critical", "error", "warning"}:
            raise ValueError("severity inválida")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)