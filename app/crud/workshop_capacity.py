"""车间产能数据操作

定义对车间产能数据的增删改查操作
"""

from sqlalchemy.orm import Session
from typing import List, Optional
from ..models import WorkshopCapacity
from ..schemas import WorkshopCapacityCreate, WorkshopCapacityUpdate


def create_workshop_capacity(db: Session, capacity: WorkshopCapacityCreate):
    """创建车间产能记录"""
    db_capacity = WorkshopCapacity(
        workshop=capacity.workshop,
        operation_id=capacity.operation_id,
        machine_name=capacity.machine_name,
        machine_count=capacity.machine_count,
        cycle_time=capacity.cycle_time,
        capacity_per_hour=capacity.capacity_per_hour
    )
    db.add(db_capacity)
    db.commit()
    db.refresh(db_capacity)
    return db_capacity


def get_workshop_capacity(db: Session, capacity_id: int):
    """根据ID获取车间产能记录"""
    return db.query(WorkshopCapacity).filter(WorkshopCapacity.id == capacity_id).first()


def get_workshop_capacities_by_workshop(db: Session, workshop: str, skip: int = 0, limit: int = 100):
    """根据车间获取产能列表"""
    return db.query(WorkshopCapacity).filter(WorkshopCapacity.workshop == workshop).offset(skip).limit(limit).all()


def get_workshop_capacities_by_operation(db: Session, operation_id: int, skip: int = 0, limit: int = 100):
    """根据工序获取产能列表"""
    return db.query(WorkshopCapacity).filter(WorkshopCapacity.operation_id == operation_id).offset(skip).limit(limit).all()


def get_all_workshop_capacities(db: Session, skip: int = 0, limit: int = 100):
    """获取所有车间产能记录"""
    return db.query(WorkshopCapacity).offset(skip).limit(limit).all()


def update_workshop_capacity(db: Session, capacity_id: int, capacity_update: WorkshopCapacityUpdate):
    """更新车间产能记录"""
    db_capacity = db.query(WorkshopCapacity).filter(WorkshopCapacity.id == capacity_id).first()
    if not db_capacity:
        return None

    update_data = capacity_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_capacity, field, value)

    db.commit()
    db.refresh(db_capacity)
    return db_capacity


def delete_workshop_capacity(db: Session, capacity_id: int):
    """删除车间产能记录"""
    db_capacity = db.query(WorkshopCapacity).filter(WorkshopCapacity.id == capacity_id).first()
    if not db_capacity:
        return None

    db.delete(db_capacity)
    db.commit()
    return db_capacity