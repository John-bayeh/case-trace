"""uv run python -m app.hospital.cli {validate,import} CASE-001."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from pydantic import TypeAdapter
from sqlalchemy import select

from app.core.config import load_settings
from app.core.database import Database
from app.hospital.assets import LocalAssetStorage
from app.hospital.diagnostics import Diagnostic
from app.hospital.discovery import discover_case
from app.hospital.ingestion import ImportConflict, ingest
from app.hospital.schemas import Identifier
from app.hospital.validation import CaseValidationError, validate_case
from app.models.hospital import CaseDataset


async def run(action: str, case_id: str) -> dict[str, object]:
    TypeAdapter(Identifier).validate_python(case_id)
    settings = load_settings()
    if action == "discover":
        imported = {}
        filename = settings.resolved_database_url.database
        if filename and filename != ":memory:" and Path(filename).is_file():
            database = Database(settings)
            try:
                async with database.session() as session:
                    rows = (await session.scalars(select(CaseDataset))).all()
                    imported = {(r.case_id, r.dataset_version): r.seed_hash for r in rows}
            finally:
                await database.dispose()
        return discover_case(
            settings.casetrace_root / "data" / "cases",
            case_id,
            LocalAssetStorage(settings.resolved_asset_path),
            imported,
        )
    path = settings.casetrace_root / "data" / "cases" / case_id / "case.json"
    validated = validate_case(path, LocalAssetStorage(settings.resolved_asset_path))
    if validated.clinical.case_id != case_id:
        report = validated.report
        if report is not None:
            report.diagnostics.append(
                Diagnostic(
                    case_id,
                    str(path),
                    "case",
                    None,
                    "case_id",
                    "CASE_DIRECTORY_MISMATCH",
                    "case_id does not match directory",
                )
            )
        raise CaseValidationError(f"{path}: case_id does not match directory", report)
    if action == "validate":
        return {
            **(validated.report.as_dict() if validated.report else {}),
            "case_id": case_id,
            "status": "valid",
            "assets": len(validated.assets),
        }
    database = Database(settings)
    try:
        await database.initialize()
        async with database.session() as session:
            return await ingest(session, validated)
    finally:
        await database.dispose()


def print_result(result: dict[str, object], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(result))
        return
    print(f"{result['case_id']}: {result['status']}")
    assets = result.get("assets_checked", result.get("assets", "not reported"))
    print(f"Records: {result.get('counts', {})}; assets: {assets}")
    diagnostics = result.get("diagnostics", [])
    assert isinstance(diagnostics, list)
    for item in diagnostics:
        print(
            f"{item['severity']} {item['code']} {item['file']} "
            f"{item['record_id'] or ''} {item['field'] or ''}: {item['description']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate/import canonical synthetic clinical records"
    )
    parser.add_argument("action", choices=["validate", "import", "discover"])
    parser.add_argument("case_id")
    parser.add_argument("--format", choices=["json", "text"], default="json")
    args = parser.parse_args()
    try:
        result = asyncio.run(run(args.action, args.case_id))
        print_result(result, args.format)
    except (CaseValidationError, ImportConflict, ValueError) as exc:
        if isinstance(exc, CaseValidationError) and exc.report:
            print_result(exc.report.as_dict(), args.format)
        else:
            print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
