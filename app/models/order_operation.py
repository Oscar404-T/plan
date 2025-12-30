"""订单工序数据库模型

定义订单工序相关的数据模型
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from ..database.connection import Base


class OrderOperation(Base):
    """订单工序表"""
    __tablename__ = "order_operations"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))  # 订单ID
    operation_id = Column(Integer, ForeignKey("operations.id"))  # 工序ID
    seq = Column(Integer, nullable=False)  # 工序序号
    pieces_per_hour = Column(Integer, nullable=True)  # 每小时件数