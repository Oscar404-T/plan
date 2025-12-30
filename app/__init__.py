"""应用模块入口

提供统一的模块导入接口
"""

from . import (
    auth,
    config,
    crud,
    db,
    models,
    schemas,
    security,
    core,
)

# 从子模块导入关键组件
from .config import settings
from .db import get_db, engine, Base
from .auth import is_admin, authenticate_admin, create_access_token, verify_token
from .crud import verify_admin_credentials
from .auth import set_admin_session, clear_admin_session

# 创建别名以匹配代码中的引用
app_auth = auth

__all__ = [
    "auth",
    "app_auth",
    "config", 
    "crud",
    "db",
    "models",
    "schemas",
    "security",
    "core",
    "settings",
    "get_db",
    "engine",
    "Base",
    "is_admin",
    "authenticate_admin",
    "create_access_token",
    "verify_token",
    "verify_admin_credentials",
    "set_admin_session",
    "clear_admin_session"
]