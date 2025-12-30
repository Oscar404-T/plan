"""车间产能数据结构定义

定义车间产能相关的Pydantic模型
"""

from pydantic import BaseModel
from typing import Optional


class WorkshopCapacityBase(BaseModel):
    """车间产能基础模型"""
    workshop: str
    operation_id: int
    machine_name: str
    machine_count: int
    cycle_time: float
    capacity_per_hour: float


class WorkshopCapacityCreate(WorkshopCapacityBase):
    """创建车间产能记录时的模型"""
    pass


class WorkshopCapacityUpdate(BaseModel):
    """更新车间产能记录时的模型"""
    workshop: Optional[str] = None
    operation_id: Optional[int] = None
    machine_name: Optional[str] = None
    machine_count: Optional[int] = None
    cycle_time: Optional[float] = None
    capacity_per_hour: Optional[float] = None


class WorkshopCapacityRead(WorkshopCapacityBase):
    """读取车间产能记录时的模型"""
    id: int
    
    class Config:
        from_attributes = True