from fastapi import APIRouter, Response

from app.api.deps import CurrentUser, api_error
from app.core.config import get_settings
from app.core.security import create_access_token, verify_password
from app.db.session import get_conn
from app.models.schemas import LoginRequest, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


@router.post("/login")
def login(body: LoginRequest, response: Response):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, email, full_name, role, password_hash FROM users WHERE email = %s",
            (body.email.lower(),),
        ).fetchone()
    if not row or not verify_password(body.password, row["password_hash"]):
        raise api_error(401, "INVALID_CREDENTIALS", "Invalid email or password")

    token = create_access_token(user_id=row["id"], email=row["email"], role=row["role"])
    response.set_cookie(
        key="rootcause_access",
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=settings.access_token_minutes * 60,
        path="/",
    )
    user = UserOut(id=row["id"], email=row["email"], full_name=row["full_name"], role=row["role"])
    return {"success": True, "data": {"user": user.model_dump(mode="json"), "access_token": token}}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("rootcause_access", path="/")
    return {"success": True, "data": {"logged_out": True}}


@router.get("/me")
def me(user: CurrentUser):
    return {
        "success": True,
        "data": UserOut(
            id=user["id"], email=user["email"], full_name=user["full_name"], role=user["role"]
        ).model_dump(mode="json"),
    }
