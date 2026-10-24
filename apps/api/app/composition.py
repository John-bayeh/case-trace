"""Local infrastructure is constructed here, never inside the workflow."""

from app.clinical.assets import AssetReader
from app.clinical.ports import ClinicalSource
from app.core.config import Settings
from app.hospital.adapter import SimulatedHospitalAdapter
from app.hospital.asset_service import LocalAssetReader
from app.llm.openai import OpenAIProvider
from app.llm.provider import GeminiProvider, LLMProvider
from app.orchestration.engine import InvestigationEngine
from app.orchestration.store import InvestigationStore


def build_engine(
    store: InvestigationStore,
    settings: Settings,
    provider: LLMProvider | None = None,
    *,
    clinical: ClinicalSource | None = None,
    assets: AssetReader | None = None,
) -> InvestigationEngine:
    source = (
        clinical
        if clinical is not None
        else SimulatedHospitalAdapter(
            store.database,
            assets if assets is not None else LocalAssetReader(settings.resolved_asset_path),
        )
    )
    model = (
        provider
        if provider is not None
        else (
            OpenAIProvider(settings)
            if settings.llm_provider == "openai"
            else GeminiProvider(settings)
            if settings.llm_provider == "gemini"
            else None
        )
    )
    return InvestigationEngine(store, settings, source, model)
