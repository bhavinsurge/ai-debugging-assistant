from uuid import UUID

from fastapi import APIRouter

from app.api.deps import CurrentUser, api_error
from app.core.config import get_settings
from app.models.schemas import InvestigationCreate
from app.services import investigation as inv_service

router = APIRouter(prefix="/api/investigations", tags=["investigations"])


@router.get("")
def list_investigations(user: CurrentUser):
    items = inv_service.list_investigations()
    return {"success": True, "data": [i.model_dump(mode="json") for i in items]}


@router.post("")
def create_investigation(body: InvestigationCreate, user: CurrentUser):
    row = inv_service.create_investigation_row(
        user_id=user["id"],
        title=body.title,
        symptom=body.symptom,
        service=body.service,
        environment=body.environment,
        time_window_minutes=body.time_window_minutes,
    )
    # Run synchronously for reliability in local/demo; background optional for UX
    report = inv_service.run_investigation(
        investigation_id=row["id"],
        title=body.title,
        symptom=body.symptom,
        service=body.service,
        environment=body.environment,
        llm_provider=get_settings().llm_provider,
    )
    return {"success": True, "data": report.model_dump(mode="json")}


@router.get("/{investigation_id}")
def get_investigation(investigation_id: UUID, user: CurrentUser):
    report = inv_service.get_investigation(investigation_id)
    if not report:
        raise api_error(404, "NOT_FOUND", "Investigation not found")
    return {"success": True, "data": report.model_dump(mode="json")}


@router.post("/{investigation_id}/rerun")
def rerun_investigation(investigation_id: UUID, user: CurrentUser):
    existing = inv_service.get_investigation(investigation_id)
    if not existing:
        raise api_error(404, "NOT_FOUND", "Investigation not found")
    report = inv_service.run_investigation(
        investigation_id=investigation_id,
        title=existing.title,
        symptom=existing.symptom,
        service=existing.service,
        environment=existing.environment,
        llm_provider=get_settings().llm_provider,
    )
    return {"success": True, "data": report.model_dump(mode="json")}
