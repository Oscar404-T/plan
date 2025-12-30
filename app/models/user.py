"""用户表模型

定义用户相关的数据模型
"""

from sqlalchemy import Column, Integer, String
from ..database.connection import Base


class User(Base):

    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)