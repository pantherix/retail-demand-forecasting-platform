from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from database.session import get_db
from database.repositories import UserRepository, AuditRepository
from auth.security import hash_password, verify_password, create_access_token
from auth.dependencies import get_current_user
from database.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Schemas ───────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email:     str = Field(..., description="Valid email address")
    username:  str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=2)
    password:  str = Field(..., min_length=6)
    role:      str = Field(default="analyst")  # admin | manager | analyst


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    username:     str
    role:         str
    full_name:    str


class UserResponse(BaseModel):
    id:        int
    email:     str
    username:  str
    full_name: str
    role:      str
    is_active: bool


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.post("/register", response_model=UserResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    if repo.get_by_email(payload.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if repo.get_by_username(payload.username):
        raise HTTPException(status_code=400, detail="Username already taken")

    user = repo.create(
        email=payload.email,
        username=payload.username,
        full_name=payload.full_name,
        hashed_pw=hash_password(payload.password),
        role=payload.role,
    )
    AuditRepository(db).log(user.username, "register", "user", f"New user registered: {user.email}")
    return user


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    repo = UserRepository(db)
    user = repo.get_by_username(form.username)
    if not user or not verify_password(form.password, user.hashed_pw):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    token = create_access_token({"sub": user.username, "role": user.role})
    AuditRepository(db).log(user.username, "login", "auth", "User logged in")
    return TokenResponse(
        access_token=token,
        username=user.username,
        role=user.role,
        full_name=user.full_name,
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/users")
def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    users = UserRepository(db).get_all()
    return [{"id": u.id, "username": u.username, "email": u.email,
             "role": u.role, "is_active": u.is_active} for u in users]


@router.get("/health")
def health():
    return {"module": "auth", "status": "healthy"}
