from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id
from app.application.schemas import ReportResponse
from datetime import date
from fastapi import HTTPException
from app.application.services.insights import build_report
from app.application.services.year_review import build_year

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("/report", response_model=ReportResponse)
def report(
    period: str = Query("week", pattern="^(week|month)$"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return build_report(db, user_id, period)


@router.get("/year")
def year_review(
    year: int = Query(default_factory=lambda: date.today().year),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if not 2000 <= year <= date.today().year:
        raise HTTPException(status_code=422, detail=f"Year must be between 2000 and {date.today().year}")
    return build_year(db, user_id, year)
