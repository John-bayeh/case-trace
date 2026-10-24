"""Short conversation reads/writes using the shared investigation writer lock."""

from sqlalchemy import func, select

from app.models.investigation import ChatMessage as MessageRow
from app.orchestration.persistence import InvestigationPersistence
from app.schemas.chat import ChatHistory, ChatMessage


class ConversationRepository:
    def __init__(self, persistence: InvestigationPersistence):
        self.persistence = persistence

    async def history(self, public_id: str, after: int = 0, limit: int = 100) -> ChatHistory:
        async with self.persistence.database.session() as session:
            run = await self.persistence.find(session, public_id)
            total = (
                await session.scalar(
                    select(func.count())
                    .select_from(MessageRow)
                    .where(MessageRow.investigation_id == run.id)
                )
                or 0
            )
            rows = await session.scalars(
                select(MessageRow)
                .where(MessageRow.investigation_id == run.id, MessageRow.sequence > after)
                .order_by(MessageRow.sequence)
                .limit(limit)
            )
            items = [ChatMessage.model_validate(row.body) for row in rows]
            return ChatHistory(
                conversation_id=f"CHAT-{public_id}",
                investigation_id=public_id,
                items=items,
                total=total,
                has_more=after + len(items) < total,
            )

    async def save_pair(self, public_id: str, messages: list[ChatMessage]) -> None:
        # Conversation writes do not reopen terminal investigations or alter event cursors.
        async with self.persistence.lock, self.persistence.database.session() as session:
            async with session.begin():
                run = await self.persistence.find(session, public_id)
                sequence = (
                    await session.scalar(
                        select(func.max(MessageRow.sequence)).where(
                            MessageRow.investigation_id == run.id
                        )
                    )
                    or 0
                )
                for offset, message in enumerate(messages, 1):
                    session.add(
                        MessageRow(
                            investigation_id=run.id,
                            sequence=sequence + offset,
                            body=message.model_dump(mode="json"),
                        )
                    )
