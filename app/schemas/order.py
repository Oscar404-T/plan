"""订单数据结构定义

定义订单相关的Pydantic模型
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class OrderBase(BaseModel):
    """订单基础模型"""
    order_number: str
    internal_model: Optional[str] = None
    customer: Optional[str] = None
    product_name: str
    length: float
    width: Optional[float] = None
    thickness: Optional[float] = None
    quantity: int
    estimated_yield: Optional[float] = None
    due_datetime: datetime
    workshop: Optional[str] = None
    original_length: Optional[float] = None
    original_width: Optional[float] = None


class OrderCreate(OrderBase):
    """创建订单时的模型"""
    pass


class OrderUpdate(BaseModel):
    """更新订单时的模型"""
    order_number: Optional[str] = None
    internal_model: Optional[str] = None
    customer: Optional[str] = None
    product_name: Optional[str] = None
    length: Optional[float] = None
    width: Optional[float] = None
    thickness: Optional[float] = None
    quantity: Optional[int] = None
    estimated_yield: Optional[float] = None
    due_datetime: Optional[datetime] = None
    workshop: Optional[str] = None
    original_length: Optional[float] = None
    original_width: Optional[float] = None


class OrderRead(OrderBase):
    """读取订单时的模型"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True