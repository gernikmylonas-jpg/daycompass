from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id
from app.application.schemas import ReportResponse
from app.application.services.insights import build_report

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("/report", response_model=ReportResponse)
def report(
    period: str = Query("week", pattern="^(week|month)$"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return build_report(db, user_id, period)
