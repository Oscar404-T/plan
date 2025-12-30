"""API数据模型模块

定义所有 Pydantic 模型（请求/响应结构体）
"""

from enum import Enum
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime


class ShiftEnum(str, Enum):
    A = "A"
    B = "B"
    C = "C"


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str
    full_name: Optional[str] = None


class UserRead(UserBase):
    id: int
    full_name: Optional[str] = None

    class Config:
        from_attributes = True


class CapacityBase(BaseModel):
    shift: str
    pieces_per_hour: int
    description: Optional[str] = None


class CapacityCreate(CapacityBase):
    pass


class CapacityRead(CapacityBase):
    id: int

    class Config:
        from_attributes = True


class OperationBase(BaseModel):
    name: str
    default_pieces_per_hour: Optional[int] = None
    description: Optional[str] = None


class OperationCreate(OperationBase):
    pass


class OperationRead(OperationBase):
    id: int

    class Config:
        from_attributes = True


class OrderOperationBase(BaseModel):
    operation_name: str
    pieces_per_hour: Optional[int] = None


class OrderOperationCreate(OrderOperationBase):
    pass


class OrderOperationRead(OrderOperationBase):
    id: int
    order_id: int

    class Config:
        from_attributes = True


class OrderBase(BaseModel):
    internal_model: Optional[str] = None  # 内部型号
    length: float  # 产品长（mm）
    width: float   # 产品宽（mm）
    thickness: float   # 板厚（micron）
    size: Optional[float] = None  # 计算得到的尺寸（inch），公式：sqrt(length^2 + width^2) / 25.4
    quantity: int  # 出货数量
    estimated_yield: Optional[float] = None  # 预估良率（%）
    due_datetime: datetime  # 最晚交期（本地时间）
    workshop: Optional[str] = None  # 车间
    original_length: Optional[float] = None  # 原玻长（mm）
    original_width: Optional[float] = None   # 原玻宽（mm）


class OrderCreate(OrderBase):
    operations: Optional[List['OrderOperationCreate']] = None


class OrderRead(OrderBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ScheduleAllocation(BaseModel):
    start: datetime
    end: datetime
    shift: str
    operation: str
    allocated: int


class ScheduleResponse(BaseModel):
    order_id: int
    requested_quantity: int
    estimated_yield: Optional[float] = None
    required_input: int
    total_allocated: int
    allocations: List[ScheduleAllocation]
    note: Optional[str] = None
    meets_due: bool
    expected_completion: Optional[datetime] = None
    meets_due_estimate: Optional[bool] = None

    class Config:
        from_attributes = True


# 解决向前引用问题
OrderCreate.update_forward_refs()


from .user import UserCreate, UserRead, UserLogin
from .order import OrderCreate, OrderUpdate, OrderRead
from .operation import OperationCreate, OperationRead, OperationUpdate
from .capacity import CapacityCreate, CapacityUpdate, CapacityRead, CapacityWithOperation
from .workshop_capacity import (
    WorkshopCapacityBase,
    WorkshopCapacityCreate,
    WorkshopCapacityUpdate,
    WorkshopCapacityRead
)

__all__ = [
    "UserCreate", 
    "UserRead", 
    "UserLogin",
    "OrderCreate", 
    "OrderUpdate", 
    "OrderRead",
    "OperationCreate", 
    "OperationRead", 
    "OperationUpdate",
    "CapacityCreate",
    "CapacityUpdate",
    "CapacityRead",
    "CapacityWithOperation",
    "WorkshopCapacityBase",
    "WorkshopCapacityCreate", 
    "WorkshopCapacityUpdate",
    "WorkshopCapacityRead"
]
