"""Investigation-scoped conversation and validated evidence citations."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.hospital.schemas import ClinicalModel
from app.schemas.provenance import Anchor

Focus = Literal["timeline", "medication", "followup", "hypothesis", "all"]


class ChatRequest(ClinicalModel):
    message: str = Field(min_length=1, max_length=2000, pattern=r"\S")
    mode: Literal["ask", "investigate"] = "ask"
    focus: Focus = "all"


class ChatAnswer(ClinicalModel):
    answer: str = Field(min_length=1, max_length=6000)
    citation_ids: list[str] = Field(max_length=20)
    finding_ids: list[str] = Field(max_length=20)
    limitations: list[str] = Field(max_length=10)


class ChatCitation(ClinicalModel):
    id: str
    anchor: Anchor


class ChatMessage(ClinicalModel):
    id: str
    conversation_id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    citations: list[ChatCitation] = Field(default_factory=list)
    finding_ids: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    new_investigation_id: str | None = None
    execution_mode: str = "deterministic_rules"


class ChatHistory(ClinicalModel):
    conversation_id: str
    investigation_id: str
    items: list[ChatMessage]
    total: int
    has_more: bool = False


class ChatResponse(ClinicalModel):
    conversation_id: str
    investigation_id: str
    user_message: ChatMessage
    assistant_message: ChatMessage
