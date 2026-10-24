import uvicorn

from app.core.config import load_settings

if __name__ == "__main__":
    settings = load_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.app_env == "development",
        access_log=False,
    )
