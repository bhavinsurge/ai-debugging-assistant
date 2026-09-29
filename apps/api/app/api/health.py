from fastapi import APIRouter

from app.core.config import get_settings
from app.db.session import get_conn

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
def health():
    settings = get_settings()
    db_ok = False
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
            db_ok = True
    except Exception:
        db_ok = False
    return {
        "success": True,
        "data": {
            "status": "ok" if db_ok else "degraded",
            "database": db_ok,
            "llm_provider": settings.llm_provider,
            "embedding_dim": settings.embedding_dim,
        },
    }
