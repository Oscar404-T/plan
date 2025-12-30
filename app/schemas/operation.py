"""工序数据结构定义

定义工序相关的Pydantic模型
"""

from pydantic import BaseModel
from typing import Optional


class OperationBase(BaseModel):
    """工序基础模型"""
    name: str
    default_pieces_per_hour: Optional[float] = None


class OperationCreate(OperationBase):
    """创建工序时的模型"""
    name: str


class OperationUpdate(BaseModel):
    """更新工序时的模型"""
    name: Optional[str] = None
    default_pieces_per_hour: Optional[float] = None


class OperationRead(OperationBase):
    """读取工序时的模型"""
    id: int
    
    class Config:
        from_attributes = True