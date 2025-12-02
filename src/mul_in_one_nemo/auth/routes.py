"""Authentication routes for FastAPI backend."""

import logging

from fastapi import APIRouter, HTTPException, Request, Depends, status
from fastapi.responses import Response
from fastapi_users.exceptions import UserAlreadyExists
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from mul_in_one_nemo.auth import (
    UserCreate,
    UserRead,
    UserUpdate,
    auth_backend,
    current_active_user,
    fastapi_users,
)
from mul_in_one_nemo.auth.oauth import get_gitee_oauth_client, get_github_oauth_client
from mul_in_one_nemo.auth.turnstile import turnstile_service
from mul_in_one_nemo.auth.manager import get_user_manager

logger = logging.getLogger(__name__)

router = APIRouter()


class RegisterWithCaptcha(BaseModel):
    """注册请求（含人机验证）."""
    email: str
    password: str
    username: str
    display_name: str | None = None
    turnstile_token: str | None = None


@router.post("/auth/register-with-captcha", response_model=UserRead, tags=["auth"])
async def register_with_captcha(
    data: RegisterWithCaptcha,
    request: Request,
    user_manager = Depends(get_user_manager)
):
    """带 Turnstile 验证的注册端点."""
    # 验证 Turnstile token
    if turnstile_service.enabled:
        if not data.turnstile_token:
            raise HTTPException(status_code=400, detail="Missing captcha token")
        
        client_ip = request.client.host if request.client else None
        success, error = await turnstile_service.verify_token(data.turnstile_token, client_ip)
        
        if not success:
            raise HTTPException(status_code=400, detail=error or "Captcha verification failed")
    
    # 创建用户
    user_create = UserCreate(
        email=data.email,
        password=data.password,
        username=data.username,
        display_name=data.display_name
    )
    
    try:
        user = await user_manager.create(user_create, request=request)
        return UserRead.model_validate(user)
    except UserAlreadyExists:
        raise HTTPException(status_code=400, detail="邮箱或用户名已被注册")
    except IntegrityError as exc:
        logger.warning("Integrity error when registering user %s: %s", data.email, exc)
        raise HTTPException(status_code=400, detail="邮箱或用户名已被注册")
    except Exception as exc:
        logger.exception("Failed to register user %s", data.email)
        raise HTTPException(status_code=500, detail="注册失败，请稍后重试")


@router.delete("/auth/account", status_code=status.HTTP_204_NO_CONTENT, tags=["auth"])
async def delete_account(
    user = Depends(current_active_user),
    user_manager = Depends(get_user_manager),
):
    """Delete the currently authenticated account."""
    try:
        await user_manager.delete(user)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception:
        logger.exception("Failed to delete account for user %s", getattr(user, "email", "unknown"))
        raise HTTPException(status_code=500, detail="删除账户失败，请稍后重试")


# 基础认证路由
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth",
    tags=["auth"],
)

# 注册路由
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

# 邮箱验证路由
router.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)

# 密码重置路由
router.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)

# 用户管理路由
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

# Gitee OAuth 路由（可选）
gitee_client = get_gitee_oauth_client()
if gitee_client:
    router.include_router(
        fastapi_users.get_oauth_router(
            gitee_client,
            auth_backend,
            "changeme-in-production",  # OAuth state secret
            associate_by_email=True,  # 通过邮箱关联已有账户
        ),
        prefix="/auth/gitee",
        tags=["auth"],
    )

# GitHub OAuth 路由（可选）
github_client = get_github_oauth_client()
if github_client:
    router.include_router(
        fastapi_users.get_oauth_router(
            github_client,
            auth_backend,
            "changeme-in-production",
            associate_by_email=True,
        ),
        prefix="/auth/github",
        tags=["auth"],
    )
