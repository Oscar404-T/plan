"""工序数据库模型

定义工序相关的数据模型
"""

from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import relationship
from ..database.connection import Base


class Operation(Base):
    """工序表"""
    __tablename__ = "operations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)  # 工序名称
    default_pieces_per_hour = Column(Integer, nullable=True)  # 默认每小时产能
    description = Column(String(255), nullable=True)  # 描述

    # 关联车间产能表
    workshop_capacities = relationship("WorkshopCapacity", back_populates="operation")