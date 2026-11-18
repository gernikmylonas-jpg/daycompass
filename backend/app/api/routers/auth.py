from app.application.services.ratelimit import logins
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.infrastructure.security import hash_password, verify_password, create_access_token, get_current_user_id
from app.domain.models import User
from app.application.schemas import RegisterRequest, LoginRequest, AuthResponse, UserResponse, ProfileUpdate, PasswordChange
router = APIRouter(prefix="/api/auth", tags=["auth"])

MIN_PASSWORD = 8
MAX_NAME = 60


def _check_password(password: str) -> None:
    if len(password) < MIN_PASSWORD:
        raise HTTPException(status_code=422, detail=f"Password must be at least {MIN_PASSWORD} characters")

@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    _check_password(payload.password)

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(str(user.id))
    return AuthResponse(token=token, user=user)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    key = payload.email.strip().lower()
    logins.check(key)
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        logins.fail(key)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    logins.reset(key)

    token = create_access_token(str(user.id))
    return AuthResponse(token=token, user=user)

@router.get("/me", response_model=UserResponse)
def me(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/profile", response_model=UserResponse)
def update_profile(payload: ProfileUpdate, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=422, detail="Name is required")
        if len(name) > MAX_NAME:
            raise HTTPException(status_code=422, detail=f"Name is too long (max {MAX_NAME} characters)")
        user.name = name

    if payload.email is not None and payload.email.lower() != user.email.lower():
        # the email is the login identity, so changing it needs the current password
        if not payload.current_password or not verify_password(payload.current_password, user.password_hash):
            raise HTTPException(status_code=403, detail="Current password is incorrect")
        if db.query(User).filter(User.email == payload.email, User.id != user.id).first():
            raise HTTPException(status_code=409, detail="Email already registered")
        user.email = payload.email

    db.commit()
    db.refresh(user)
    return user


@router.put("/password")
def change_password(payload: PasswordChange, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=403, detail="Current password is incorrect")
    _check_password(payload.new_password)
    if payload.new_password == payload.current_password:
        raise HTTPException(status_code=422, detail="The new password must be different")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"detail": "Password changed"}
