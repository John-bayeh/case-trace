from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    version: Literal["1.0.0"] = "1.0.0"
    database: Literal["connected"] = "connected"
