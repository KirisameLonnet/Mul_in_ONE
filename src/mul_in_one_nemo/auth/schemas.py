"""Pydantic schemas for user authentication."""

from datetime import datetime

from fastapi_users import schemas


class UserRead(schemas.BaseUser[int]):
    """用户公开信息模型."""
    username: str
    display_name: str | None = None
    role: str = "member"
    created_at: datetime


class UserCreate(schemas.BaseUserCreate):
    """用户注册模型."""
    username: str
    display_name: str | None = None


class UserUpdate(schemas.BaseUserUpdate):
    """用户更新模型."""
    username: str | None = None
    display_name: str | None = None
