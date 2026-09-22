from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, health, investigations
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="RootCause API",
    version="1.0.0",
    description="Evidence-bound AI software debugging and root-cause assistant",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(investigations.router)
app.include_router(health.router)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "success" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {"code": "HTTP_ERROR", "message": str(exc.detail), "details": None},
        },
    )


@app.get("/")
def root():
    return {
        "success": True,
        "data": {
            "name": "RootCause",
            "docs": "/docs",
            "llm_provider": settings.llm_provider,
        },
    }
