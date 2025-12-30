"""产能数据库模型

定义产能相关的数据模型
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum
import sqlalchemy
from sqlalchemy.orm import relationship
from ..database.connection import Base


class Capacity(Base):
    """产能表"""
    __tablename__ = "capacities"

    id = Column(Integer, primary_key=True, index=True)
    shift = Column(Enum('day', 'night', name='shiftenum'), nullable=False)  # 班次
    pieces_per_hour = Column(Integer, nullable=False)  # 每小时产能
    description = Column(String(255), nullable=True)  # 描述
    
    