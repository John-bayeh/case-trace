"""DTO-only hospital capabilities; no ORM, sessions, or storage paths."""

from typing import Any, Protocol, runtime_checkable

from app.hospital.schemas import DocumentSearchHit
from app.schemas.investigation import SourceRecord, SourceRef, SourceType


@runtime_checkable
class SourceResolver(Protocol):
    async def resolve(self, patient_id: str, source: SourceRef) -> SourceRecord: ...


@runtime_checkable
class ClinicalReader(Protocol):
    async def records(
        self, source_type: SourceType, patient_id: str, filters: dict[str, Any]
    ) -> tuple[list[SourceRecord], int]: ...

    async def search_documents(
        self, patient_id: str, query: str, filters: dict[str, Any]
    ) -> tuple[list[DocumentSearchHit], int]: ...


class ClinicalSource(SourceResolver, ClinicalReader, Protocol):
    """Selected-patient retrieval, including individual provenance-bearing sources."""
