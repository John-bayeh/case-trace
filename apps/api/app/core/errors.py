import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.hospital.errors import HospitalError
from app.hospital.schemas import HospitalErrorDetail, HospitalErrorResponse, Meta
from app.schemas.errors import ErrorDetail, ErrorResponse

logger = logging.getLogger("casetrace.errors")


def error_response(request: Request, status: int, code: str, message: str) -> JSONResponse:
    if request.url.path.startswith("/api/hospital/v1"):
        hospital_body = HospitalErrorResponse(
            error=HospitalErrorDetail(
                code="RESOURCE_NOT_FOUND" if code == "NOT_FOUND" else code, message=message
            ),
            meta=Meta(request_id=request.state.request_id),
        )
        return JSONResponse(status_code=status, content=hospital_body.model_dump())
    body = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            request_id=request.state.request_id,
        )
    )
    return JSONResponse(status_code=status, content=body.model_dump())


def internal_error_response(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "request.failed",
        extra={
            "request_id": request.state.request_id,
            "status": 500,
            "error_type": type(exc).__name__,
        },
    )
    return error_response(request, 500, "INTERNAL_ERROR", "An internal error occurred.")


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HospitalError)
    async def hospital_error(request: Request, exc: HospitalError) -> JSONResponse:
        return error_response(
            request,
            exc.status,
            exc.code,
            "The clinical resource or asset is unavailable."
            if exc.status == 404
            else "The clinical request could not be completed.",
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        response = error_response(
            request,
            exc.status_code,
            "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR",
            "The requested resource was not found."
            if exc.status_code == 404
            else "The request could not be completed.",
        )
        if exc.headers:
            response.headers.update(exc.headers)
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(request, 422, "VALIDATION_ERROR", "Request validation failed.")

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception) -> JSONResponse:
        response = internal_error_response(request, exc)
        response.headers["X-Request-ID"] = request.state.request_id
        return response
