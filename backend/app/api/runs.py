"""Phase 9 (minimal): list and fetch persisted onboarding runs."""

from fastapi import APIRouter, HTTPException, Query, status

from app.config import get_settings
from app.schemas.onboarding_run import OnboardingRunRecord, OnboardingRunSummary
from app.services.runs_store import get_run, list_run_summaries

router = APIRouter(tags=["runs"])


@router.get("/runs", response_model=list[OnboardingRunSummary])
async def list_runs(limit: int = Query(default=50, ge=1, le=200)) -> list[OnboardingRunSummary]:
    settings = get_settings()
    return await list_run_summaries(settings=settings, limit=limit)


@router.get("/runs/{run_id}", response_model=OnboardingRunRecord)
async def get_run_detail(run_id: str) -> OnboardingRunRecord:
    settings = get_settings()
    record = await get_run(run_id, settings=settings)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )
    return record
