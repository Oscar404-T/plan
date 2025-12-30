"""产能数据操作

定义对产能数据的增删改查操作
"""

from sqlalchemy.orm import Session
from typing import List, Optional
from ..models import Capacity
from ..schemas import CapacityCreate, CapacityUpdate


def create_capacity(db: Session, capacity: CapacityCreate):
    """创建产能记录"""
    db_capacity = Capacity(
        shift=capacity.shift,
        pieces_per_hour=capacity.pieces_per_hour,
        description=capacity.description
    )
    db.add(db_capacity)
    db.commit()
    db.refresh(db_capacity)
    return db_capacity


def get_capacity(db: Session, capacity_id: int):
    """根据ID获取产能记录"""
    return db.query(Capacity).filter(Capacity.id == capacity_id).first()


def get_capacities_by_workshop(db: Session, workshop: str, skip: int = 0, limit: int = 100):
    """根据车间获取产能列表（兼容旧版本，但实际capacity表中没有workshop字段）"""
    # 由于旧的Capacity表没有workshop字段，这里返回所有记录
    return db.query(Capacity).offset(skip).limit(limit).all()


def get_capacities_by_operation(db: Session, operation_id: int, skip: int = 0, limit: int = 100):
    """根据工序获取产能列表（兼容旧版本，但实际capacity表中没有operation_id字段）"""
    # 由于旧的Capacity表没有operation_id字段，这里返回所有记录
    return db.query(Capacity).offset(skip).limit(limit).all()


def get_capacities_by_shift(db: Session, shift: str, skip: int = 0, limit: int = 100):
    """根据班次获取产能列表"""
    return db.query(Capacity).filter(Capacity.shift == shift).offset(skip).limit(limit).all()


def get_all_capacities(db: Session, skip: int = 0, limit: int = 100):
    """获取所有产能记录"""
    return db.query(Capacity).offset(skip).limit(limit).all()


def update_capacity(db: Session, capacity_id: int, capacity_update: CapacityUpdate):
    """更新产能记录"""
    db_capacity = db.query(Capacity).filter(Capacity.id == capacity_id).first()
    if not db_capacity:
        return None

    update_data = capacity_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_capacity, field, value)

    db.commit()
    db.refresh(db_capacity)
    return db_capacity


def delete_capacity(db: Session, capacity_id: int):
    """删除产能记录"""
    db_capacity = db.query(Capacity).filter(Capacity.id == capacity_id).first()
    if not db_capacity:
        return None

    db.delete(db_capacity)
    db.commit()
    return db_capacity


def get_capacity_by_shift(db: Session, shift: str):
    """根据班次获取产能"""
    # 查询指定班次的产能记录
    capacity = db.query(Capacity).filter(Capacity.shift == shift).first()
    if capacity:
        return capacity
    
    # 如果没有找到特定班次的产能，则创建并返回默认值
    default_capacity = Capacity(
        shift=shift,
        pieces_per_hour=10,  # 默认每小时10件
        description=f'{shift}班默认产能'
    )
    db.add(default_capacity)
    db.commit()
    
    return default_capacity


def list_capacities(db: Session):
    """获取所有产能记录"""
    return db.query(Capacity).all()