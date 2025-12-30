"""用户数据结构定义

定义用户相关的Pydantic模型
"""

from pydantic import BaseModel
from typing import Optional


class UserBase(BaseModel):
    """用户基础模型"""
    username: str


class UserCreate(UserBase):
    """创建用户时的模型"""
    password: str


class UserRead(UserBase):
    """读取用户时的模型"""
    id: int
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """用户登录模型"""
    username: str
    password: str