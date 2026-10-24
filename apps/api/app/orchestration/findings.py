"""Finding, verification and evidence link persistence."""

from sqlalchemy import select

from app.core.provenance import digest, now
from app.models import investigation as db
from app.orchestration.persistence import InvestigationPersistence
from app.schemas.investigation import Finding


class FindingRepository:
    def __init__(self, persistence: InvestigationPersistence):
        self.persistence = persistence

    async def save_finding(self, public_id: str, finding: Finding) -> None:
        async with self.persistence.mutation(
            public_id,
            f"finding.{finding.status}",
            {
                "finding_id": finding.id,
            },
        ) as (session, run):
            key = digest(
                {
                    "rule": finding.rule,
                    "anchors": [a.model_dump(mode="json") for a in finding.anchors],
                    **(
                        {"relationship": finding.relationship.model_dump(mode="json")}
                        if finding.relationship
                        else {}
                    ),
                }
            )
            existing = await session.scalar(
                select(db.Finding).where(
                    db.Finding.investigation_id == run.id,
                    db.Finding.logical_key == key,
                )
            )
            if existing:
                return
            row = db.Finding(
                investigation_id=run.id,
                logical_key=key,
                status=finding.status,
                body=finding.model_dump(mode="json"),
            )
            session.add(row)
            await session.flush()
            # Invalid anchors remain in rejected proposal audit only, never the evidence registry.
            if finding.verification.status == "rejected":
                return
            for anchor in finding.anchors:
                evidence = db.EvidenceRef(
                    investigation_id=run.id,
                    anchor=anchor.model_dump(mode="json"),
                    retrieved_at=now(),
                )
                session.add(evidence)
                await session.flush()
                session.add(
                    db.FindingEvidenceLink(
                        finding_id=row.id,
                        evidence_ref_id=evidence.id,
                        relationship=anchor.relationship,
                        validation_status=finding.verification.status,
                    )
                )
