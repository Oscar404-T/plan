"""Pydantic 模式（schemas）

用于请求与响应的数据验证与序列化。这里添加中文注释以便于团队理解字段含义。
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    name: Optional[str] = None


class UserRead(BaseModel):
    id: int
    email: EmailStr
    name: Optional[str] = None

    # pydantic v2: use `from_attributes` in model_config instead of orm_mode
    model_config = {"from_attributes": True}


class CapacityCreate(BaseModel):
    shift: str
    pieces_per_hour: int
    description: Optional[str] = None


class CapacityRead(BaseModel):
    id: int
    shift: str
    pieces_per_hour: int
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class OperationCreate(BaseModel):
    name: str
    default_pieces_per_hour: Optional[int] = None
    description: Optional[str] = None


class OperationRead(BaseModel):
    id: int
    name: str
    default_pieces_per_hour: Optional[int] = None
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class OrderOperationCreate(BaseModel):
    operation_name: str
    pieces_per_hour: Optional[int] = None


class OrderCreate(BaseModel):
    internal_model: Optional[str] = None  # 内部型号
    length: float  # 产品长（mm）
    width: float   # 产品宽（mm）
    size: Optional[float] = None  # 计算得到的尺寸（inch），公式：sqrt(length^2 + width^2) / 25.4
    quantity: int  # 出货数量
    estimated_yield: Optional[float] = None  # 预估良率（%）
    due_datetime: datetime  # 最晚交期（本地时间）
    # 按序的工序列表；若未提供则使用系统默认工序
    operations: Optional[List[OrderOperationCreate]] = None


class OrderRead(BaseModel):
    id: int
    internal_model: Optional[str] = None
    length: float
    width: float
    size: Optional[float] = None
    estimated_yield: Optional[float] = None
    quantity: int
    due_datetime: datetime

    model_config = {"from_attributes": True}


class HourAllocation(BaseModel):
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
    allocations: List[HourAllocation]
    note: Optional[str] = None
    meets_due: bool
    expected_completion: Optional[datetime] = None
    meets_due_estimate: Optional[bool] = None
