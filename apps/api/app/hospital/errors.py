"""Stable hospital/application error contract."""


class HospitalError(Exception):
    def __init__(self, code: str = "RESOURCE_NOT_FOUND", status: int = 404):
        self.code = code
        self.status = status
