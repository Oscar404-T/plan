"""订单模型定义"""

from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.sql import func
from .base import Base


class Order(Base):
    """订单模型"""
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    # 可选的内部型号字符串
    internal_model = Column(String(255), nullable=True)
    # 产品尺寸（单位：mm），用于根据公式计算物料尺寸
    length = Column(Float, nullable=False)
    width = Column(Float, nullable=False)
    # 计算得到的尺寸（单位：inch），由 sqrt(length^2 + width^2) / 25.4 得出
    size = Column(Float, nullable=True)
    # 出货数量
    quantity = Column(Integer, nullable=False)
    # 估计良率（百分比，例如 98.5）
    estimated_yield = Column(Float, nullable=True)
    due_datetime = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    # 车间信息
    workshop = Column(String(255), nullable=True)
    # 后续可扩展状态等字段