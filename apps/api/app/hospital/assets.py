"""Constrained filesystem assets. No API accepts a storage path."""

import hashlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


class AssetError(ValueError):
    pass


@dataclass(frozen=True)
class AssetInfo:
    key: str
    sha256: str
    byte_size: int


class LocalAssetStorage:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def resolve(self, key: str, case_id: str) -> Path:
        parts = PurePosixPath(key).parts
        if (
            "\\" in key
            or ":" in key
            or "\x00" in key
            or PurePosixPath(key).is_absolute()
            or ".." in parts
        ):
            raise AssetError("unsafe asset storage key")
        if len(parts) < 3 or parts[:2] != ("cases", case_id):
            raise AssetError("asset must be within its case asset directory")
        if any(
            part.lower() in {"expected", "evaluation", "ground_truth", "ground-truth"}
            for part in parts
        ):
            raise AssetError("evaluation paths are not clinical assets")
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root / "cases" / case_id):
            raise AssetError("asset escapes constrained root")
        if not path.is_file():
            raise AssetError("registered asset file is missing")
        return path

    def inspect(self, key: str, case_id: str, mime_type: str) -> AssetInfo:
        path = self.resolve(key, case_id)
        with path.open("rb") as handle:
            head = handle.read(16)
            handle.seek(0)
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        signatures = {
            "application/pdf": b"%PDF-",
            "image/png": b"\x89PNG\r\n\x1a\n",
            "image/jpeg": b"\xff\xd8\xff",
        }
        if mime_type not in {*signatures, "text/plain", "text/html"}:
            raise AssetError("unsupported asset media type")
        if mime_type in signatures and not head.startswith(signatures[mime_type]):
            raise AssetError("asset bytes do not match declared media type")
        return AssetInfo(key, digest, path.stat().st_size)
