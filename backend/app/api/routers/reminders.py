from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id
from app.domain.models import ReminderSetting
from app.application.schemas import ReminderSettings
from app.application.services.reminders import LANGUAGES, DEFAULT_LANGUAGE

router = APIRouter(prefix="/api/reminders", tags=["reminders"])


@router.get("", response_model=ReminderSettings)
def get_settings(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    setting = db.query(ReminderSetting).filter(ReminderSetting.user_id == user_id).first()
    if setting is None:
        return ReminderSettings(enabled=False, language=DEFAULT_LANGUAGE)
    return ReminderSettings(enabled=setting.enabled, language=setting.language)


@router.put("", response_model=ReminderSettings)
def update_settings(
    payload: ReminderSettings,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if payload.language not in LANGUAGES:
        raise HTTPException(status_code=422, detail="Invalid language")

    setting = db.query(ReminderSetting).filter(ReminderSetting.user_id == user_id).first()
    if setting is None:
        setting = ReminderSetting(user_id=user_id)
        db.add(setting)
    setting.enabled = payload.enabled
    setting.language = payload.language
    db.commit()
    return ReminderSettings(enabled=setting.enabled, language=setting.language)
