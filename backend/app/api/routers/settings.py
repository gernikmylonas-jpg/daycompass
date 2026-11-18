from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id
from app.domain.models import UserSettings
from app.application.schemas import SettingsPayload, SettingsResponse
from app.application.services.reminders import LANGUAGES

router = APIRouter(prefix="/api/settings", tags=["settings"])

THEMES = {"classic", "modern", "retro", "nautical", "explorer", "neon", "minimal"}
MODES = {"light", "dark", "system"}
MOOD_STYLES = {"emoji", "colors", "words"}
DEFAULTS = SettingsPayload(theme="classic", mode="system", needle_cursor=True, language=None, mood_style="emoji", depth_3d=False, brightness=100)


@router.get("", response_model=SettingsResponse)
def get_settings(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    row = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    if row is None:
        return SettingsResponse(**DEFAULTS.model_dump(), saved=False)
    return SettingsResponse(
        theme=row.theme, mode=row.mode, needle_cursor=row.needle_cursor, language=row.language,
        mood_style=row.mood_style, depth_3d=row.depth_3d, lid_open=row.lid_open, calendar_prefs=row.calendar_prefs, brightness=row.brightness, saved=True,
    )


@router.put("", response_model=SettingsResponse)
def put_settings(
    payload: SettingsPayload,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if payload.theme not in THEMES:
        raise HTTPException(status_code=422, detail="Invalid theme")
    if payload.mode not in MODES:
        raise HTTPException(status_code=422, detail="Invalid mode")
    if payload.language is not None and payload.language not in LANGUAGES:
        raise HTTPException(status_code=422, detail="Invalid language")
    if payload.mood_style not in MOOD_STYLES:
        raise HTTPException(status_code=422, detail="Invalid mood style")
    if payload.calendar_prefs is not None and len(payload.calendar_prefs) > 2000:
        raise HTTPException(status_code=422, detail="Invalid calendar preferences")
    if not 50 <= payload.brightness <= 150:
        raise HTTPException(status_code=422, detail="Invalid brightness")

    row = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    if row is None:
        row = UserSettings(user_id=user_id)
        db.add(row)
    row.theme = payload.theme
    row.mode = payload.mode
    row.needle_cursor = payload.needle_cursor
    row.language = payload.language
    row.mood_style = payload.mood_style
    row.depth_3d = payload.depth_3d
    row.lid_open = payload.lid_open
    row.calendar_prefs = payload.calendar_prefs
    row.brightness = payload.brightness
    row.updated_at = datetime.utcnow()
    db.commit()
    return SettingsResponse(**payload.model_dump(), saved=True)
