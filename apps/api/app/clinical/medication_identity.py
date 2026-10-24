"""Conservative identity from explicit product fields, without a drug dictionary."""

import re
from typing import Any

from app.hospital.schemas import ClinicalModel


class MedicationIdentity(ClinicalModel):
    ingredient: str
    strength: str | None = None
    formulation: str | None = None
    route: str | None = None


def medication_identity(data: dict[str, Any]) -> MedicationIdentity | None:
    name = str(data.get("medication_name") or "").casefold().strip()
    ingredient = str(data.get("generic_name") or "").casefold().strip()
    if not name:
        return None
    # Absent generic name: exact product-name matching only; never infer synonyms.
    ingredient = ingredient or name
    strength = re.search(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|units?)(?:\s*/\s*\d*\s*ml)?\b", name)
    form = re.search(
        r"\b(?:extended.release|modified.release|immediate.release|controlled.release|"
        r"er|xr|sr|mr|ir|tablet|capsule|suspension|solution|injection|cream|patch)\b",
        name,
    )
    return MedicationIdentity(
        ingredient=ingredient,
        strength=re.sub(r"\s+", "", strength[0]) if strength else None,
        formulation=form[0].replace("-", " ") if form else None,
        route=str(data["route"]).casefold() if data.get("route") else None,
    )
