from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import Cookie, Depends, Header, HTTPException

from app.core.security import decode_access_token
from app.db.session import get_conn


def api_error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"success": False, "error": {"code": code, "message": message, "details": None}},
    )


def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    rootcause_access: Annotated[str | None, Cookie()] = None,
) -> dict[str, Any]:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    elif rootcause_access:
        token = rootcause_access
    if not token:
        raise api_error(401, "UNAUTHORIZED", "Authentication required")
    try:
        payload = decode_access_token(token)
    except ValueError:
        raise api_error(401, "UNAUTHORIZED", "Invalid or expired token") from None

    user_id = payload.get("sub")
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, email, full_name, role FROM users WHERE id = %s",
            (user_id,),
        ).fetchone()
    if not row:
        raise api_error(401, "UNAUTHORIZED", "User not found")
    return dict(row)


CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]
