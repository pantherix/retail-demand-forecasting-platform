from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from backend.auth.security import decode_token
from backend.database.models import User
from backend.database.repositories import UserRepository
from backend.database.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    user = UserRepository(db).get_by_username(username)
    if user is None or user.is_active is not True:
        raise credentials_exc
    return user


def require_role(*roles: str):
    """Factory that returns a dependency requiring one of the given roles."""

    def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' is not authorized for this action.",
            )
        return current_user

    return _check


# Convenience shortcuts
require_admin = require_role("admin")
require_director = require_role("admin", "director")
require_manager = require_role("admin", "director", "manager")
require_planner = require_role("admin", "director", "manager", "planner", "analyst")


def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to get the current user and verify they have the 'admin' role.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action. Admin role required.",
        )
    return current_user
