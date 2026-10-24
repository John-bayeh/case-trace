"""Registered-asset capability independent of sessions and local storage."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class AssetDescriptor:
    external_id: str
    case_id: str
    storage_key: str
    mime_type: str
    sha256: str
    byte_size: int


class AssetReader(Protocol):
    async def verified_path(self, asset: AssetDescriptor) -> Path: ...
