"""Budget, savings and trips. Private to the user; amounts are stored as whole cents (no floating-point money)."""
import re
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.models import BudgetLimit, MoneyEntry, MoneyProfile, SavingsDeposit, SavingsGoal, Trip
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id

router = APIRouter(prefix="/api/money", tags=["money"])

EXPENSE_CATEGORIES = ["food", "home", "transport", "health", "fun", "shopping", "bills", "travel", "other"]
INCOME_CATEGORIES = ["salary", "gift", "side", "other_income"]
TRIP_CATEGORIES = ["lodging", "food", "transport", "activities", "shopping", "other"]
MAX_CENTS = 100_000_000_00  # 100 million
MAX_NAME, MAX_NOTE = 60, 120
MAX_TRIPS, MAX_GOALS, MAX_ENTRIES_DAY = 50, 30, 200
EARLIEST = date(1900, 1, 1)


def cents(amount: float) -> int:
    return int(round(amount * 100))


def _check_amount(amount: float) -> int:
    c = cents(amount)
    if not 1 <= c <= MAX_CENTS:
        raise HTTPException(status_code=422, detail="Amount is not valid")
    return c


def _day(d: Optional[date]) -> date:
    d = d or date.today()
    if (d - date.today()).days > 1:
        raise HTTPException(status_code=422, detail="Date cannot be in the future")
    if d < EARLIEST:
        raise HTTPException(status_code=422, detail="Date cannot be before 1900")
    return d


def _profile(db: Session, user_id: str) -> MoneyProfile:
    p = db.query(MoneyProfile).filter(MoneyProfile.user_id == user_id).first()
    if p is None:
        p = MoneyProfile(user_id=user_id, currency="EUR")
        db.add(p)
        db.flush()
    return p


class ProfileIn(BaseModel):
    currency: str
    monthly_budget: Optional[float] = None


@router.get("/profile")
def get_profile(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    p = _profile(db, user_id)
    db.commit()
    return {"currency": p.currency, "monthly_budget_cents": p.monthly_budget_cents,
            "categories": {"expense": EXPENSE_CATEGORIES, "income": INCOME_CATEGORIES, "trip": TRIP_CATEGORIES}}


@router.put("/profile")
def put_profile(payload: ProfileIn, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    if not re.fullmatch(r"[A-Z]{3}", payload.currency.upper()):
        raise HTTPException(status_code=422, detail="Invalid currency")
    p = _profile(db, user_id)
    p.currency = payload.currency.upper()
    p.monthly_budget_cents = _check_amount(payload.monthly_budget) if payload.monthly_budget else None
    db.commit()
    return {"currency": p.currency, "monthly_budget_cents": p.monthly_budget_cents}


# ── entries (everyday income/expenses and trip expenses) ─────────────────────
class EntryIn(BaseModel):
    kind: str = "expense"
    amount: float
    category: str
    entry_date: Optional[date] = None
    note: Optional[str] = None
    trip_id: Optional[UUID] = None


def _own_trip(db: Session, trip_id, user_id) -> Trip:
    t = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Trip not found")
    return t


@router.post("/entries")
def add_entry(payload: EntryIn, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    if payload.kind not in ("expense", "income"):
        raise HTTPException(status_code=422, detail="Invalid kind")
    allowed = TRIP_CATEGORIES if payload.trip_id else (EXPENSE_CATEGORIES if payload.kind == "expense" else INCOME_CATEGORIES)
    if payload.category not in allowed:
        raise HTTPException(status_code=422, detail="Invalid category")
    if payload.trip_id:
        _own_trip(db, payload.trip_id, user_id)
        if payload.kind != "expense":
            raise HTTPException(status_code=422, detail="Invalid kind")
    note = (payload.note or "").strip() or None
    if note and len(note) > MAX_NOTE:
        raise HTTPException(status_code=422, detail=f"Note is too long (max {MAX_NOTE} characters)")
    day = _day(payload.entry_date)
    if db.query(func.count(MoneyEntry.id)).filter(MoneyEntry.user_id == user_id, MoneyEntry.entry_date == day).scalar() >= MAX_ENTRIES_DAY:
        raise HTTPException(status_code=422, detail="Too many entries for one day")
    e = MoneyEntry(user_id=user_id, kind=payload.kind, amount_cents=_check_amount(payload.amount), category=payload.category,
                   entry_date=day, note=note, trip_id=payload.trip_id)
    db.add(e)
    db.commit()
    return {"id": e.id}


@router.delete("/entries/{entry_id}")
def delete_entry(entry_id: UUID, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    e = db.query(MoneyEntry).filter(MoneyEntry.id == entry_id, MoneyEntry.user_id == user_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(e)
    db.commit()
    return {"detail": "Entry deleted"}


class LimitIn(BaseModel):
    category: str
    monthly: Optional[float] = None  # None removes the limit


@router.put("/limits")
def set_limit(payload: LimitIn, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    if payload.category not in EXPENSE_CATEGORIES:
        raise HTTPException(status_code=422, detail="Invalid category")
    row = db.query(BudgetLimit).filter(BudgetLimit.user_id == user_id, BudgetLimit.category == payload.category).first()
    if payload.monthly is None or payload.monthly == 0:
        if row:
            db.delete(row)
    else:
        c = _check_amount(payload.monthly)
        if row is None:
            db.add(BudgetLimit(user_id=user_id, category=payload.category, monthly_cents=c))
        else:
            row.monthly_cents = c
    db.commit()
    return {"detail": "Saved"}


@router.get("/month")
def month(month: str = Query(default_factory=lambda: date.today().strftime("%Y-%m"), pattern=r"^\d{4}-\d{2}$"),
          user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    year, mon = int(month[:4]), int(month[5:])
    if not (1900 <= year <= 2100 and 1 <= mon <= 12):
        raise HTTPException(status_code=422, detail="Invalid month")
    first = date(year, mon, 1)
    last = (date(year + (mon == 12), mon % 12 + 1, 1)) - timedelta(days=1)
    p = _profile(db, user_id)
    rows = (db.query(MoneyEntry).filter(MoneyEntry.user_id == user_id, MoneyEntry.trip_id.is_(None), MoneyEntry.entry_date.between(first, last))
            .order_by(MoneyEntry.entry_date.desc(), MoneyEntry.created_at.desc()).all())
    income = sum(r.amount_cents for r in rows if r.kind == "income")
    spent = sum(r.amount_cents for r in rows if r.kind == "expense")
    by_cat: dict[str, int] = defaultdict(int)
    for r in rows:
        if r.kind == "expense":
            by_cat[r.category] += r.amount_cents
    limits = {l.category: l.monthly_cents for l in db.query(BudgetLimit).filter(BudgetLimit.user_id == user_id)}
    today = date.today()
    days_left = max((last - today).days + 1, 0) if first <= today <= last else 0
    budget = p.monthly_budget_cents
    db.commit()
    return {
        "currency": p.currency, "month": month, "income_cents": income, "spent_cents": spent, "balance_cents": income - spent,
        "budget_cents": budget, "left_cents": (budget - spent) if budget else None, "days_left": days_left,
        "per_day_left_cents": ((budget - spent) // days_left) if budget and days_left and budget > spent else None,
        "categories": [{"category": c, "spent_cents": by_cat.get(c, 0), "limit_cents": limits.get(c)} for c in EXPENSE_CATEGORIES if by_cat.get(c) or c in limits],
        "entries": [{"id": r.id, "date": r.entry_date, "kind": r.kind, "amount_cents": r.amount_cents, "category": r.category, "note": r.note} for r in rows[:200]],
    }


# ── savings goals ────────────────────────────────────────────────────────────
class GoalIn(BaseModel):
    name: str
    target: float
    deadline: Optional[date] = None
    kind: str = "general"


class DepositIn(BaseModel):
    amount: float  # negative = take money out
    entry_date: Optional[date] = None
    note: Optional[str] = None


def _goal_out(db: Session, g: SavingsGoal) -> dict:
    deps = db.query(SavingsDeposit).filter(SavingsDeposit.goal_id == g.id).order_by(SavingsDeposit.entry_date.desc(), SavingsDeposit.created_at.desc()).all()
    saved = sum(d.amount_cents for d in deps)
    today = date.today()
    remaining = max(g.target_cents - saved, 0)
    out = {"id": g.id, "name": g.name, "kind": g.kind, "target_cents": g.target_cents, "saved_cents": saved,
           "percent": min(100, round(saved * 100 / g.target_cents)) if g.target_cents else 0, "remaining_cents": remaining,
           "deadline": g.deadline, "done": saved >= g.target_cents, "monthly_needed_cents": None, "projected": None,
           "deposits": [{"id": d.id, "date": d.entry_date, "amount_cents": d.amount_cents, "note": d.note} for d in deps[:30]]}
    if remaining and g.deadline and g.deadline > today:
        months = max((g.deadline - today).days / 30.44, 0.1)
        out["monthly_needed_cents"] = int(round(remaining / months))
    # at the pace of the last 90 days, when would it be reached?
    recent = sum(d.amount_cents for d in deps if d.entry_date >= today - timedelta(days=90))
    if remaining and recent > 0:
        days = int(remaining / (recent / 90))
        if days <= 365 * 30:  # a date decades away says nothing useful
            out["projected"] = today + timedelta(days=days)
    return out


@router.get("/savings")
def savings(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    goals = db.query(SavingsGoal).filter(SavingsGoal.user_id == user_id).order_by(SavingsGoal.created_at).all()
    p = _profile(db, user_id)
    db.commit()
    return {"currency": p.currency, "goals": [_goal_out(db, g) for g in goals]}


@router.post("/savings")
def add_goal(payload: GoalIn, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name is required")
    if len(name) > MAX_NAME:
        raise HTTPException(status_code=422, detail=f"Title is too long (max {MAX_NAME} characters)")
    if payload.kind not in ("general", "trip"):
        raise HTTPException(status_code=422, detail="Invalid kind")
    if db.query(SavingsGoal).filter(SavingsGoal.user_id == user_id).count() >= MAX_GOALS:
        raise HTTPException(status_code=422, detail="Too many savings goals")
    g = SavingsGoal(user_id=user_id, name=name, target_cents=_check_amount(payload.target), deadline=payload.deadline, kind=payload.kind)
    db.add(g)
    db.commit()
    return _goal_out(db, g)


def _own_goal(db: Session, goal_id, user_id) -> SavingsGoal:
    g = db.query(SavingsGoal).filter(SavingsGoal.id == goal_id, SavingsGoal.user_id == user_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Goal not found")
    return g


@router.post("/savings/{goal_id}/deposit")
def deposit(goal_id: UUID, payload: DepositIn, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    g = _own_goal(db, goal_id, user_id)
    c = cents(payload.amount)
    if c == 0 or abs(c) > MAX_CENTS:
        raise HTTPException(status_code=422, detail="Amount is not valid")
    saved = db.query(func.coalesce(func.sum(SavingsDeposit.amount_cents), 0)).filter(SavingsDeposit.goal_id == g.id).scalar()
    if saved + c < 0:
        raise HTTPException(status_code=422, detail="You cannot take out more than you saved")
    note = (payload.note or "").strip() or None
    db.add(SavingsDeposit(goal_id=g.id, user_id=user_id, amount_cents=c, entry_date=_day(payload.entry_date), note=note[:MAX_NOTE] if note else None))
    db.commit()
    return _goal_out(db, g)


@router.put("/savings/{goal_id}")
def edit_goal(goal_id: UUID, payload: GoalIn, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Change what you are saving for: the name, the target amount, the deadline (or remove it) and the type."""
    g = _own_goal(db, goal_id, user_id)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name is required")
    if len(name) > MAX_NAME:
        raise HTTPException(status_code=422, detail=f"Title is too long (max {MAX_NAME} characters)")
    if payload.kind not in ("general", "trip"):
        raise HTTPException(status_code=422, detail="Invalid kind")
    g.name, g.kind, g.target_cents, g.deadline = name, payload.kind, _check_amount(payload.target), payload.deadline
    db.commit()
    return _goal_out(db, g)


@router.delete("/savings/{goal_id}")
def delete_goal(goal_id: UUID, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    g = _own_goal(db, goal_id, user_id)
    db.query(SavingsDeposit).filter(SavingsDeposit.goal_id == g.id).delete(synchronize_session=False)
    db.delete(g)
    db.commit()
    return {"detail": "Goal deleted"}


# ── trips ────────────────────────────────────────────────────────────────────
class TripIn(BaseModel):
    name: str
    start_date: date
    end_date: date
    budget: float
    currency: Optional[str] = None


def _trip_out(db: Session, t: Trip, with_entries: bool = False) -> dict:
    rows = db.query(MoneyEntry).filter(MoneyEntry.trip_id == t.id).order_by(MoneyEntry.entry_date.desc(), MoneyEntry.created_at.desc()).all()
    spent = sum(r.amount_cents for r in rows)
    today = date.today()
    total_days = (t.end_date - t.start_date).days + 1
    elapsed = min(max((today - t.start_date).days + 1, 0), total_days)
    days_left = max((t.end_date - today).days + 1, 0) if today <= t.end_date else 0
    if today < t.start_date:
        days_left = total_days
    by_cat: dict[str, int] = defaultdict(int)
    for r in rows:
        by_cat[r.category] += r.amount_cents
    left = t.budget_cents - spent
    out = {
        "id": t.id, "name": t.name, "start_date": t.start_date, "end_date": t.end_date, "currency": t.currency, "budget_cents": t.budget_cents,
        "spent_cents": spent, "left_cents": left, "percent": min(100, round(spent * 100 / t.budget_cents)) if t.budget_cents else 0,
        "total_days": total_days, "days_left": days_left, "daily_allowance_cents": int(t.budget_cents // total_days),
        "avg_per_day_cents": int(spent // elapsed) if elapsed else None,
        "left_per_day_cents": int(left // days_left) if days_left and left > 0 else None,
        "by_category": [{"category": c, "spent_cents": v} for c, v in sorted(by_cat.items(), key=lambda x: -x[1])],
    }
    if with_entries:
        out["entries"] = [{"id": r.id, "date": r.entry_date, "amount_cents": r.amount_cents, "category": r.category, "note": r.note} for r in rows[:200]]
    return out


@router.get("/trips")
def trips(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    ts = db.query(Trip).filter(Trip.user_id == user_id).order_by(Trip.start_date.desc()).all()
    return [_trip_out(db, t, with_entries=True) for t in ts]


@router.post("/trips")
def add_trip(payload: TripIn, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name is required")
    if len(name) > MAX_NAME:
        raise HTTPException(status_code=422, detail=f"Title is too long (max {MAX_NAME} characters)")
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=422, detail="End date must not be before start date")
    if (payload.end_date - payload.start_date).days + 1 > 366:
        raise HTTPException(status_code=422, detail="Range is limited to 366 days")
    if db.query(Trip).filter(Trip.user_id == user_id).count() >= MAX_TRIPS:
        raise HTTPException(status_code=422, detail="Too many trips")
    cur = (payload.currency or _profile(db, user_id).currency).upper()
    if not re.fullmatch(r"[A-Z]{3}", cur):
        raise HTTPException(status_code=422, detail="Invalid currency")
    t = Trip(user_id=user_id, name=name, start_date=payload.start_date, end_date=payload.end_date, budget_cents=_check_amount(payload.budget), currency=cur)
    db.add(t)
    db.commit()
    return _trip_out(db, t, with_entries=True)


@router.put("/trips/{trip_id}")
def edit_trip(trip_id: UUID, payload: TripIn, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    t = _own_trip(db, trip_id, user_id)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name is required")
    if len(name) > MAX_NAME:
        raise HTTPException(status_code=422, detail=f"Title is too long (max {MAX_NAME} characters)")
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=422, detail="End date must not be before start date")
    if (payload.end_date - payload.start_date).days + 1 > 366:
        raise HTTPException(status_code=422, detail="Range is limited to 366 days")
    t.name, t.start_date, t.end_date, t.budget_cents = name, payload.start_date, payload.end_date, _check_amount(payload.budget)
    db.commit()
    return _trip_out(db, t, with_entries=True)


@router.delete("/trips/{trip_id}")
def delete_trip(trip_id: UUID, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    t = _own_trip(db, trip_id, user_id)
    db.query(MoneyEntry).filter(MoneyEntry.trip_id == t.id).delete(synchronize_session=False)
    db.delete(t)
    db.commit()
    return {"detail": "Trip deleted"}
