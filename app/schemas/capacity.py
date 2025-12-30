"""产能数据结构定义

定义产能相关的Pydantic模型
"""

from pydantic import BaseModel
from typing import Optional


class CapacityBase(BaseModel):
    """产能基础模型"""
    shift: str
    pieces_per_hour: int
    description: Optional[str] = None


class CapacityCreate(CapacityBase):
    """创建产能记录时的模型"""
    pass


class CapacityUpdate(BaseModel):
    """更新产能记录时的模型"""
    shift: Optional[str] = None
    pieces_per_hour: Optional[int] = None
    description: Optional[str] = None


class CapacityRead(CapacityBase):
    """读取产能记录时的模型"""
    id: int
    
    class Config:
        from_attributes = True


class CapacityWithOperation(CapacityRead):
    """包含工序信息的产能模型"""
    operation_name: str
    
    class Config:
        from_attributes = True