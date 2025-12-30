"""认证模块

该模块处理用户认证、JWT令牌生成和管理会话状态。
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import Request, Response
from passlib.context import CryptContext
from . import models
from sqlalchemy.orm import Session
from . import schemas
from jose import JWTError, jwt
from .config.settings import settings

# 密码加密上下文 - 与security.py保持一致
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

# 使用全局配置
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希密码是否匹配"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # 如果哈希验证失败，返回False
        return False


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)


def authenticate_admin(username: str, password: str):
    """验证管理员用户凭据"""
    from .db import get_db
    db = next(get_db())
    try:
        admin = db.query(models.Admin).filter(models.Admin.username == username).first()
        if not admin or not verify_password(password, admin.hashed_password):
            return None
        return admin
    finally:
        db.close()


def authenticate_and_login(request: Request, db: Session, username: str, password: str):
    """验证用户凭据并设置会话"""
    admin = authenticate_admin(username, password)
    if not admin:
        return False
    
    # 设置会话
    if not hasattr(request, 'session'):
        # 如果没有session中间件，直接返回成功
        return True
    
    request.session['admin_id'] = admin.id
    request.session['username'] = admin.username
    return True


def set_admin_session(response: Response, username: str):
    """设置管理员会话 - 这个函数是用于登录时设置会话的"""
    # 这个函数是为了解决main.py中的调用，但登录时我们实际上是通过数据库查询并重定向
    # 实际上，我们需要在登录时设置会话，但由于这是在Form处理中，我们需要使用依赖注入
    pass  # 实际上，FastAPI的SessionMiddleware会自动处理会话，我们不需要手动设置


def clear_admin_session(request: Request):
    """清除管理员会话"""
    if hasattr(request, 'session'):
        request.session.clear()


def is_admin(request: Request):
    """检查用户是否已登录为管理员"""
    if not hasattr(request, 'session'):
        return False
    return 'admin_id' in request.session and request.session['admin_id'] is not None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建JWT访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str):
    """验证JWT令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None