"""Grounded conversation over an existing patient-scoped investigation."""

from typing import Any, Protocol, TypeVar
from uuid import uuid4

from pydantic import BaseModel

from app.clinical.ports import ClinicalSource
from app.core.config import Settings
from app.core.provenance import now
from app.evidence.verification import EvidenceVerifier
from app.hospital.errors import HospitalError
from app.llm.prompts.conversation import CHAT_PROMPT
from app.llm.provider import ProviderError
from app.orchestration.conversations import ConversationRepository
from app.orchestration.store import InvestigationStore
from app.schemas.chat import (
    ChatAnswer,
    ChatCitation,
    ChatMessage,
    ChatRequest,
    ChatResponse,
)
from app.schemas.investigation import Candidate, CreateInvestigation, Finding, SourceRecord
from app.schemas.provenance import Anchor, SourceRef, SourceType
from app.services.investigations import InvestigationService

Output = TypeVar("Output", bound=BaseModel)


class ConversationProvider(Protocol):
    async def generate(
        self, task: str, evidence: dict[str, Any], schema: type[Output], instructions: str
    ) -> Output: ...


OBJECTIVES = {
    "all": "full_record_investigation",
    "timeline": "timeline_investigation",
    "medication": "medication_investigation",
    "followup": "followup_investigation",
    "hypothesis": "hypothesis_investigation",
}


class ConversationService:
    def __init__(
        self,
        store: InvestigationStore,
        investigations: InvestigationService,
        clinical: ClinicalSource,
        settings: Settings,
        provider: ConversationProvider | None = None,
    ):
        self.store, self.investigations = store, investigations
        self.clinical, self.settings, self.provider = clinical, settings, provider
        self.repository = ConversationRepository(store.persistence)

    async def context(
        self, public_id: str, body: ChatRequest
    ) -> tuple[dict[str, Any], list[ChatCitation], list[Finding], list[str]]:
        state = await self.store.snapshot(public_id)
        findings = await self.store.findings(public_id)
        words = set(body.message.lower().split())
        focused = {
            "timeline": {"timeline_contradiction", "documentation_delay"},
            "medication": {"medication_change"},
            "followup": {"missing_evidence"},
        }
        findings.sort(
            key=lambda f: (
                f.type not in focused.get(body.focus, set()),
                -len(words & set((f.title + " " + f.claim).lower().split())),
                f.id,
            )
        )
        citations: list[ChatCitation] = []
        selected: list[Finding] = []
        limits = ["Answers are limited to accessible synthetic records; no clinical decisions."]
        verifier = EvidenceVerifier(
            self.clinical, state["patient_id"], self.settings.investigation_reasoning
        )
        context: dict[str, Any] = {
            "question": body.message,
            "focus": body.focus,
            "findings": [],
            "records": [],
            "history": [],
        }
        remaining = self.settings.investigation_max_context_chars - 6000

        async def add(anchor: Anchor) -> str | None:
            if len(citations) >= 20:
                return None
            if any(c.anchor == anchor for c in citations):
                return next(c.id for c in citations if c.anchor == anchor)
            probe = Candidate(
                type="clinical_relationship",
                title="Citation validation",
                claim="Citation validation",
                claim_kind="hypothesis",
                rule="interpretation",
                anchors=[anchor],
            )
            verification, _ = await verifier.verify(probe)
            if verification.status == "rejected":
                limits.append("A stale or inaccessible evidence reference was omitted.")
                return None
            citation = ChatCitation(id=f"C{len(citations) + 1}", anchor=anchor)
            citations.append(citation)
            return citation.id

        for finding in findings[:8]:
            size = len(finding.model_dump_json())
            if size > remaining:
                limits.append("Some findings were omitted to respect the answer context budget.")
                continue
            ids = [value for anchor in finding.anchors[:4] if (value := await add(anchor))]
            if ids:
                selected.append(finding)
                context["findings"].append(
                    {
                        "id": finding.id,
                        "status": finding.status,
                        "claim": finding.claim,
                        "verification": finding.verification.model_dump(),
                        "citation_ids": ids,
                        "limitations": finding.limitations,
                    }
                )
                remaining -= size

        # Search is a bounded lead; only independently resolved originals enter model context.
        query = " ".join(body.message.split())[:200]
        hits, total = await self.clinical.search_documents(
            state["patient_id"], query, {"limit": 4, "offset": 0}
        )
        originals: list[SourceRecord] = []
        for hit in hits[:4]:
            try:
                originals.append(
                    await self.clinical.resolve(
                        state["patient_id"], SourceRef(type="document", id=hit.id)
                    )
                )
            except HospitalError:
                limits.append("An original document was inaccessible.")
        categories: list[SourceType] = {
            "timeline": ["clinical_event"],
            "medication": ["medication", "observation"],
            "followup": ["referral", "diagnostic_report"],
            "hypothesis": ["diagnosis"],
            "all": [],
        }[body.focus]  # type: ignore[assignment]
        for category in categories:
            rows, count = await self.clinical.records(
                category, state["patient_id"], {"limit": 4, "offset": 0}
            )
            originals.extend(rows[:4])
            if count > 4:
                limits.append(f"Only a bounded selection of {category} records was reviewed.")
        if total > 4:
            limits.append("Additional matching documents were outside the chat retrieval budget.")
        for record in originals:
            size = len(record.model_dump_json())
            if size > remaining or len(citations) >= 20:
                limits.append("Additional records were outside the chat context budget.")
                continue
            field = next(
                (
                    f
                    for f in ("text_content", "description", "status", "test_name")
                    if record.data.get(f) is not None
                ),
                None,
            )
            if field is None:
                continue
            anchor = Anchor(
                source=record.source,
                source_version=record.source_version,
                source_hash=record.source_hash,
                encounter_id=record.data.get("encounter_id"),
                field=field,
                expected=record.data[field],
            )
            citation_id = await add(anchor)
            if citation_id:
                context["records"].append(
                    {"citation_id": citation_id, "source": record.model_dump(mode="json")}
                )
                remaining -= size
        context["citations"] = [c.model_dump(mode="json") for c in citations]
        # Persisted state contributes compact context, rather than a second generated conclusion.
        context["timeline"] = state["timeline"][:10]
        context["hypotheses"] = state["hypotheses"][:3]
        context["limitations"] = state["limitations"][:10] + list(dict.fromkeys(limits))
        history = await self.repository.history(public_id, limit=1)
        recent = await self.repository.history(public_id, after=max(0, history.total - 6), limit=6)
        context["history"] = [{"role": m.role, "content": m.content[:1000]} for m in recent.items]
        return context, citations, selected, list(dict.fromkeys(limits))

    async def send(self, public_id: str, body: ChatRequest) -> ChatResponse:
        state = await self.store.snapshot(public_id)
        conversation_id = f"CHAT-{public_id}"
        user = ChatMessage(
            id=f"MSG-{uuid4().hex}",
            conversation_id=conversation_id,
            role="user",
            content=body.message,
            created_at=now(),
        )
        assistant = ChatMessage(
            id=f"MSG-{uuid4().hex}",
            conversation_id=conversation_id,
            role="assistant",
            content="",
            created_at=now(),
        )
        if body.mode == "investigate":
            focus: str = body.focus
            if focus == "all":
                text = body.message.lower()
                focus = next(
                    (
                        f
                        for f, keywords in {
                            "medication": ("medication", "drug", "treatment"),
                            "timeline": ("timeline", "chronology"),
                            "followup": ("follow-up", "followup", "referral"),
                            "hypothesis": ("hypothesis", "diagnosis"),
                        }.items()
                        if any(word in text for word in keywords)
                    ),
                    "all",
                )
            request = CreateInvestigation.model_validate(
                {"patient_id": state["patient_id"], "objective": OBJECTIVES[focus]}
            )
            # Creation uses the existing scheduler; the finalized parent is never reopened.
            created = await self.investigations.create(request, user.id)
            assistant.new_investigation_id = created.investigation_id
            assistant.content = f"A new {focus} investigation was accepted for this patient."
            assistant.execution_mode = "scheduled"
        else:
            context, citations, selected, limits = await self.context(public_id, body)
            answer: ChatAnswer | None = None
            if self.provider:
                try:
                    answer = await self.provider.generate(
                        "conversation", context, ChatAnswer, CHAT_PROMPT
                    )
                except ProviderError as exc:
                    limits.append(f"Live answer unavailable ({exc}); source-backed fallback shown.")
            else:
                limits.append("No live conversational model configured; stored evidence shown.")
            allowed_citations = {c.id for c in citations}
            allowed_findings = {f.id for f in selected}
            if answer and (
                not set(answer.citation_ids) <= allowed_citations
                or not set(answer.finding_ids) <= allowed_findings
                or not answer.citation_ids
            ):
                answer = None
                limits.append("The model answer failed citation validation and was discarded.")
            if answer:
                assistant.content = answer.answer
                assistant.citations = [c for c in citations if c.id in answer.citation_ids]
                assistant.finding_ids = answer.finding_ids
                limits.extend(answer.limitations)
                assistant.execution_mode = "openai"
            else:
                assistant.content = (
                    "The available evidence does not establish an answer to this question."
                )
                if selected:
                    assistant.content += " Stored findings for review: " + " ".join(
                        f"[{f.status}] {f.claim}" for f in selected[:3]
                    )
                    assistant.citations = citations
                    assistant.finding_ids = [f.id for f in selected[:3]]
            assistant.limitations = list(dict.fromkeys(limits))
        assistant.created_at = now()
        await self.repository.save_pair(public_id, [user, assistant])
        return ChatResponse(
            conversation_id=conversation_id,
            investigation_id=public_id,
            user_message=user,
            assistant_message=assistant,
        )
