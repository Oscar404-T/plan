"""用户模型定义

包含User、Admin、Capacity、Order、Operation、OrderOperation 等数据库表的 ORM 定义。
注：字段注释使用中文以便阅读，ShiftEnum 用于表示白班/夜班。
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.sql import func
from .base import Base


class User(Base):
    """用户模型"""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=True)