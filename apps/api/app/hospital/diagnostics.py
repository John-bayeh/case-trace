"""Clinical-only maintenance diagnostics; never include rejected source values."""

from dataclasses import asdict, dataclass, field
from typing import Literal


@dataclass(frozen=True)
class Diagnostic:
    case_id: str | None
    file: str
    record_type: str | None
    record_id: str | None
    field: str | None
    code: str
    description: str
    severity: Literal["error", "warning", "info"] = "error"


@dataclass
class ValidationReport:
    case_id: str | None = None
    counts: dict[str, int] = field(default_factory=dict)
    assets_checked: int = 0
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not any(item.severity == "error" for item in self.diagnostics)

    def as_dict(self) -> dict[str, object]:
        return {**asdict(self), "status": "valid" if self.valid else "invalid"}
