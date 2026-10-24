"""Interrupted execution reconciliation; no invented successes."""

from typing import Any, cast

from sqlalchemy import select, update

from app.core.provenance import now
from app.models import investigation as db
from app.orchestration.commands import InvestigationCommands
from app.orchestration.persistence import InvestigationPersistence


class InvestigationRecovery:
    def __init__(self, persistence: InvestigationPersistence):
        self.persistence = persistence

    async def recover(self) -> None:
        async with self.persistence.database.session() as session:
            pending = list(
                await session.scalars(
                    select(db.Investigation.external_id).where(
                        db.Investigation.status.in_(["queued", "running"]),
                    )
                )
            )
        for public_id in pending:
            await InvestigationCommands(self.persistence).transition(
                public_id, "failed", "PROCESS_INTERRUPTED; retry with a new run"
            )
        # Close interrupted audit entries without inventing successful results.
        async with (
            self.persistence.lock,
            self.persistence.database.session() as session,
            session.begin(),
        ):
            for model in [db.AgentExecution, db.ToolCall, db.InvestigationStage]:
                await session.execute(
                    update(model)
                    .where(cast(Any, model).status == "running")
                    .values(
                        status="failed",
                        **(
                            {"completed_at": now(), "error_code": "PROCESS_INTERRUPTED"}
                            if model is db.ToolCall
                            else {"ended_at": now()}
                        ),
                    )
                )
