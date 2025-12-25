"""认证与会话相关的工具函数

责任：
- 提供对 session 可用性的集中检测（itsdangerous 导入检查）
- 提供安全的读取/写入 admin session（避免直接在未安装 SessionMiddleware 时访问 request.session）
- 提供登录验证并在成功时写入 session

这个模块不自动安装中间件；中间件仍由 `app/main.py` 在应用启动时尝试添加。
"""
from typing import Optional
from fastapi import Request

from . import crud

# 会话功能依赖 itsdangerous（由 Starlette 的 SessionMiddleware 使用）
try:
    import itsdangerous  # type: ignore
    SESSIONS_AVAILABLE = True
except Exception:
    SESSIONS_AVAILABLE = False


def _has_session_scope(request: Request) -> bool:
    """检查当前请求是否包含 session scope（即 SessionMiddleware 已安装）。"""
    return "session" in request.scope


def get_admin_id(request: Request) -> Optional[int]:
    """安全地从 request 中获取 admin_id；若不可用或未登录返回 None。"""
    if not SESSIONS_AVAILABLE:
        return None
    if not _has_session_scope(request):
        return None
    return request.session.get("admin_id")


def is_admin(request: Request) -> bool:
    """判断当前 request 是否由已登录的管理员发起。"""
    return bool(get_admin_id(request))


def set_admin_session(request: Request, admin_id: int) -> None:
    """在 request.session 中设置 admin_id（仅当会话可用时）。"""
    if not SESSIONS_AVAILABLE:
        return
    if not _has_session_scope(request):
        return
    request.session["admin_id"] = admin_id


def clear_admin_session(request: Request) -> None:
    """清除当前请求的 admin 会话（若存在）。"""
    if not SESSIONS_AVAILABLE:
        return
    if not _has_session_scope(request):
        return
    request.session.pop("admin_id", None)


def authenticate_and_login(request: Request, db, username: str, password: str) -> bool:
    """验证管理员凭证，验证通过则在 session 中写入 admin_id 并返回 True，否则返回 False。

    注意：如果会话不可用，则仅进行凭证验证但不写入 session（返回 False 表示登录未完成）。
    """
    if not username or not password:
        return False
    valid = crud.verify_admin_credentials(db, username, password)
    if not valid:
        return False
    admin = crud.get_admin_by_username(db, username)
    if not admin:
        return False
    # 如果会话可用则写入
    if SESSIONS_AVAILABLE and _has_session_scope(request):
        set_admin_session(request, admin.id)
        return True
    # 会话不可用时仍返回 False（提示用户安装 itsdangerous）
    return False
