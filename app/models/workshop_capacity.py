"""车间产能数据库模型

定义车间产能相关的数据模型
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from ..database.connection import Base


class WorkshopCapacity(Base):
    """车间产能表"""
    __tablename__ = "workshop_capacities"

    id = Column(Integer, primary_key=True, index=True)
    workshop = Column(String(255), nullable=False)  # 车间
    operation_id = Column(Integer, ForeignKey("operations.id"))  # 工序ID
    machine_name = Column(String(255), nullable=False)  # 机台名称
    machine_count = Column(Integer, nullable=False)  # 机台数量
    cycle_time = Column(Float, nullable=False)  # 生产节拍（秒/件）
    capacity_per_hour = Column(Float, nullable=False)  # 每小时产能（件/小时）
    
    # 关联工序表 - 使用字符串形式的类名避免初始化错误
    operation = relationship("Operation", back_populates="workshop_capacities")