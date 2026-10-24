"""Existing lifecycle policy and stable conflict error."""

from app.hospital.errors import HospitalError

TERMINAL = {"completed", "completed_with_limitations", "failed", "cancelled"}
TRANSITIONS = {
    "queued": {"running", "failed", "cancelled"},
    "running": TERMINAL,
}


class RunConflict(HospitalError):
    def __init__(self) -> None:
        super().__init__("INVESTIGATION_CONFLICT", 409)
