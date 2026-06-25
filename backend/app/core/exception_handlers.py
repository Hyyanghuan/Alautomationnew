"""统一 API 异常响应"""
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _format_validation_errors(exc: RequestValidationError) -> list[dict]:
    items = []
    for err in exc.errors():
        loc = [str(x) for x in err.get("loc", []) if x not in ("body", "query", "path")]
        field = ".".join(loc) if loc else "request"
        items.append({
            "field": field,
            "message": err.get("msg", "校验失败"),
            "type": err.get("type", ""),
        })
    return items


async def request_validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "detail": "请求参数校验失败",
            "errors": _format_validation_errors(exc),
        },
    )


async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, str):
        body = {"success": False, "detail": detail}
    elif isinstance(detail, dict):
        body = {"success": False, **detail}
    else:
        body = {"success": False, "detail": str(detail)}
    return JSONResponse(status_code=exc.status_code, content=body, headers=getattr(exc, "headers", None))
