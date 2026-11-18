"""Public holidays of any country, computed from the `holidays` package (no network needed)."""
from functools import lru_cache
import holidays
from fastapi import APIRouter, Depends, HTTPException
from app.infrastructure.security import get_current_user_id

router = APIRouter(prefix="/api/calendars", tags=["calendars"])

MIN_YEAR, MAX_YEAR = 1900, 2100


@lru_cache(maxsize=1)
def _countries() -> list[str]:
    return sorted(code for code in holidays.list_supported_countries() if len(code) == 2 and code.isalpha())


@router.get("/countries", response_model=list[str])
def countries(_: str = Depends(get_current_user_id)):
    return _countries()


@lru_cache(maxsize=512)
def _holidays(country: str, year: int, language: str | None) -> tuple[tuple[str, str], ...]:
    h = holidays.country_holidays(country, years=year, language=language)
    return tuple((d.isoformat(), name) for d, name in sorted(h.items()))


@router.get("/holidays")
def public_holidays(country: str, year: int, lang: str | None = None, _: str = Depends(get_current_user_id)):
    country = country.upper()
    if country not in _countries():
        raise HTTPException(status_code=422, detail="Unknown country")
    if not MIN_YEAR <= year <= MAX_YEAR:
        raise HTTPException(status_code=422, detail=f"Year must be between {MIN_YEAR} and {MAX_YEAR}")
    supported = holidays.country_holidays(country).supported_languages
    language = lang if lang in supported else None  # None = the country's own default language
    return [{"date": d, "name": n} for d, n in _holidays(country, year, language)]
