"""Authentication system for Mul-in-One using FastAPI-Users."""

from .manager import get_user_manager
from .schemas import UserCreate, UserRead, UserUpdate
from .users import auth_backend, current_active_user, current_superuser, fastapi_users

__all__ = [
    "fastapi_users",
    "auth_backend",
    "current_active_user",
    "current_superuser",
    "get_user_manager",
    "UserRead",
    "UserCreate",
    "UserUpdate",
]
