"""产能模型定义"""

from sqlalchemy import Column, Integer, String, Enum, Float
from .base import Base
from enum import Enum as PyEnum


class ShiftEnum(str, PyEnum):
    day = "day"
    night = "night"


class Capacity(Base):
    """产能模型"""
    __tablename__ = "capacities"
    id = Column(Integer, primary_key=True, index=True)
    # 分班：'day' 或 'night'（枚举类型）
    shift = Column(Enum(ShiftEnum), nullable=False)
    # 每小时产能（单位：件/小时）
    pieces_per_hour = Column(Integer, nullable=False)
    # 可选说明
    description = Column(String(255), nullable=True)