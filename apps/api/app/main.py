"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events."""
    # Startup
    settings = get_settings()
    await init_db()
    print(f"🚀 CASETRACE API starting - Environment: {settings.ENVIRONMENT}")
    
    yield
    
    # Shutdown
    print("👋 CASETRACE API shutting down")


app = FastAPI(
    title="CASETRACE API",
    description="AI Clinical Investigation System",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "name": "CASETRACE API",
        "version": "0.1.0",
        "status": "operational",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


# TODO: Import and include routers
# from app.api.routes import patients, investigations, hospital
# app.include_router(patients.router, prefix="/api/patients", tags=["patients"])
# app.include_router(investigations.router, prefix="/api/investigations", tags=["investigations"])
# app.include_router(hospital.router, prefix="/api/hospital", tags=["hospital"])
