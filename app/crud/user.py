"""用户数据操作

定义对用户数据的增删改查操作
"""

from sqlalchemy.orm import Session
from typing import Optional
from ..models import User
from ..security import get_password_hash, verify_password


def get_user_by_username(db: Session, username: str):
    """根据用户名获取用户"""
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(db: Session, user_id: int):
    """根据ID获取用户"""
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, username: str, password: str):
    """创建用户"""
    hashed_password = get_password_hash(password)
    db_user = User(username=username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, username: str, password: str):
    """验证用户"""
    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def update_user_password(db: Session, user_id: int, new_password: str):
    """更新用户密码"""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.hashed_password = get_password_hash(new_password)
        db.commit()
        db.refresh(user)
        return user
    return None


def verify_admin_credentials(db: Session, username: str, password: str):
    """验证管理员凭据"""
    from ..models.admin import Admin
    admin = db.query(Admin).filter(Admin.username == username).first()
    if not admin:
        return False
    
    # 使用与用户验证相同的密码验证函数
    try:
        return verify_password(password, admin.hashed_password)
    except:
        return False


def get_admin_by_username(db: Session, username: str):
    """根据用户名获取管理员"""
    from ..models.admin import Admin
    return db.query(Admin).filter(Admin.username == username).first()
