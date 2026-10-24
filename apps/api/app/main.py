import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect

from app.api.routes.health import router
from app.api.routes.hospital import router as hospital_router
from app.api.routes.investigations import router as investigation_router
from app.clinical.assets import AssetReader
from app.clinical.ports import ClinicalSource
from app.composition import build_engine
from app.core.config import Settings, load_settings
from app.core.database import Database
from app.core.errors import install_error_handlers, internal_error_response
from app.core.logging import configure_logging
from app.hospital.asset_service import LocalAssetReader
from app.llm.openai import OpenAIProvider
from app.llm.provider import LLMProvider
from app.orchestration.store import InvestigationStore
from app.services.conversations import ConversationService
from app.services.investigations import InvestigationService


def create_app(
    settings: Settings | None = None,
    *,
    clinical: ClinicalSource | None = None,
    assets: AssetReader | None = None,
    provider: LLMProvider | None = None,
) -> FastAPI:
    config = settings or load_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        configure_logging(config.log_level)
        database = Database(config)
        application.state.database = database
        try:
            await database.initialize()
            store = InvestigationStore(database)
            asset_reader = (
                assets if assets is not None else LocalAssetReader(config.resolved_asset_path)
            )
            engine = build_engine(store, config, provider, clinical=clinical, assets=asset_reader)
            application.state.asset_reader = asset_reader
            application.state.investigation_service = InvestigationService(store, engine)
            application.state.investigation_store = store
            application.state.investigation_engine = engine
            application.state.conversation_service = ConversationService(
                store,
                application.state.investigation_service,
                engine.clinical,
                config,
                engine.provider if isinstance(engine.provider, OpenAIProvider) else None,
            )
            async with database.engine.connect() as connection:
                migrated = await connection.run_sync(
                    lambda conn: inspect(conn).has_table("investigations")
                )
            if migrated:
                await store.recover()
            logging.getLogger("casetrace").info("application.started")
            yield
        finally:
            if hasattr(application.state, "investigation_engine"):
                await application.state.investigation_engine.close()
            await database.dispose()
            logging.getLogger("casetrace").info("application.stopped")

    application = FastAPI(
        title="CASETRACE API",
        version="1.0.0",
        lifespan=lifespan,
    )
    application.state.settings = config
    install_error_handlers(application)
    application.include_router(router)
    application.include_router(hospital_router)
    application.include_router(investigation_router)

    @application.middleware("http")
    async def request_context(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request.state.request_id = f"req_{uuid4().hex}"
        start = perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            response = internal_error_response(request, exc)
        response.headers["X-Request-ID"] = request.state.request_id
        logging.getLogger("casetrace.http").info(
            "request.completed",
            extra={
                "request_id": request.state.request_id,
                "status": response.status_code,
                "duration_ms": round((perf_counter() - start) * 1000, 2),
            },
        )
        return response

    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_allowed_origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Idempotency-Key", "Last-Event-ID"],
        expose_headers=["X-Request-ID"],
    )
    return application


app = create_app()
