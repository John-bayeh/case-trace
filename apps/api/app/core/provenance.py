"""Canonical source DTO fingerprints, distinct from text and asset byte digests."""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any


def now() -> datetime:
    return datetime.now(UTC)


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
