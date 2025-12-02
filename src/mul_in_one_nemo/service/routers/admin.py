"""Administrative routes for managing platform users."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mul_in_one_nemo.auth import UserRead, current_superuser
from mul_in_one_nemo.auth.db import get_async_session
from mul_in_one_nemo.db.models import User

router = APIRouter(prefix="/admin", tags=["admin"])


class UpdateAdminStatus(BaseModel):
    """Payload for elevating or revoking administrator privileges."""

    is_admin: bool


@router.get("/users", response_model=List[UserRead])
async def list_users(
    _: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session),
) -> List[UserRead]:
    """Return all platform users ordered by creation time."""
    stmt = select(User).order_by(User.created_at.asc())
    rows = (await session.execute(stmt)).scalars().all()
    return [UserRead.model_validate(user) for user in rows]


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_admin: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session),
) -> Response:
    """Delete a user account when requested by an administrator."""
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="无法删除当前管理员账号")

    target = await session.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    await session.delete(target)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/users/{user_id}/admin", response_model=UserRead)
async def toggle_admin_privileges(
    user_id: int,
    payload: UpdateAdminStatus,
    current_admin: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session),
) -> UserRead:
    """Grant or revoke administrator privileges for another user."""
    if user_id == current_admin.id and not payload.is_admin:
        raise HTTPException(status_code=400, detail="无法取消当前管理员的权限")

    target = await session.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    target.is_superuser = payload.is_admin
    target.role = "admin" if payload.is_admin else "member"
    session.add(target)
    await session.commit()
    await session.refresh(target)
    return UserRead.model_validate(target)
