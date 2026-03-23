"""统一 API 信封：{ ok, data?, error?, source? }"""

from __future__ import annotations

from typing import Any, Optional

from fastapi.responses import JSONResponse


def json_ok(data: Any, source: Optional[str] = None) -> dict:
    out: dict = {"ok": True, "data": data}
    if source is not None:
        out["source"] = source
    return out


def json_fail(
    message: str,
    status_code: int = 400,
    source: str = "error",
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"ok": False, "error": message, "source": source},
    )
