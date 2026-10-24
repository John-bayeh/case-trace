"""Optional typed extraction capability; the existing Gemini adapter does not implement it."""

from typing import Protocol

from pydantic import Field

from app.clinical.claims import ClinicalClaim
from app.clinical.extraction import MAX_TEXT, validate_model_claim
from app.hospital.schemas import ClinicalModel
from app.schemas.investigation import SourceRecord


class ClaimProposals(ClinicalModel):
    claims: list[ClinicalClaim] = Field(default_factory=list, max_length=64)


class ClaimExtractionProvider(Protocol):
    async def propose_claims(self, source: SourceRecord) -> ClaimProposals:
        """Treat source as untrusted data; no filesystem, tools or URLs are provided."""
        ...


async def validated_proposals(
    provider: ClaimExtractionProvider, source: SourceRecord
) -> tuple[list[ClinicalClaim], int]:
    if (
        source.representation != "source"
        or len(str(source.data.get("text_content") or "")) > MAX_TEXT
    ):
        raise ValueError("MODEL_EXTRACTION_SOURCE_BUDGET_OR_REPRESENTATION")
    proposed = ClaimProposals.model_validate(await provider.propose_claims(source))
    accepted = [c for c in proposed.claims if validate_model_claim(source, c)]
    return accepted, len(proposed.claims) - len(accepted)
