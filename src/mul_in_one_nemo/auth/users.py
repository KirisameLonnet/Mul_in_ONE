"""FastAPI-Users authentication setup with JWT and OAuth."""

from fastapi_users import FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)

from mul_in_one_nemo.config import Settings
from mul_in_one_nemo.db.models import User

from .manager import get_user_manager

# 配置 Bearer Token 传输（Authorization: Bearer <token>）
bearer_transport = BearerTransport(tokenUrl="auth/login")


def get_jwt_strategy() -> JWTStrategy:
    """获取 JWT 策略."""
    settings = Settings.from_env()
    return JWTStrategy(
        secret=settings.jwt_secret,
        lifetime_seconds=settings.access_token_expire_minutes * 60,
        algorithm=settings.jwt_algorithm,
    )


# 认证后端（使用 JWT）
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

# FastAPI-Users 主实例
fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend],
)

# 获取当前活跃用户或者超级管理员依赖
current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)
