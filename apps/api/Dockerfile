FROM ghcr.io/astral-sh/uv:0.11.17 AS uv
FROM python:3.12-slim
COPY --from=uv /uv /usr/local/bin/uv
ENV CASETRACE_ROOT=/app UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app/apps/api
COPY apps/api/pyproject.toml apps/api/uv.lock apps/api/.python-version ./
RUN uv sync --locked --no-dev
COPY apps/api/app ./app
COPY apps/api/alembic ./alembic
COPY apps/api/alembic.ini ./alembic.ini
RUN mkdir -p /app/data/runtime /app/data/assets
EXPOSE 8000
CMD ["sh", "-c", "uv run --locked --no-dev alembic upgrade head && exec uv run --locked --no-dev uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log"]
