"""工序数据操作

定义对工序数据的增删改查操作
"""

from sqlalchemy.orm import Session
from typing import List
from ..models import Operation
from ..schemas import OperationCreate, OperationUpdate


def create_operation(db: Session, operation: OperationCreate):
    """创建工序"""
    db_operation = Operation(
        name=operation.name,
        default_pieces_per_hour=operation.default_pieces_per_hour
    )
    db.add(db_operation)
    db.commit()
    db.refresh(db_operation)
    return db_operation


def get_operation(db: Session, operation_id: int):
    """根据ID获取工序"""
    return db.query(Operation).filter(Operation.id == operation_id).first()


def get_operations(db: Session, skip: int = 0, limit: int = 100):
    """获取工序列表"""
    return db.query(Operation).offset(skip).limit(limit).all()


def update_operation(db: Session, operation_id: int, operation_update: OperationUpdate):
    """更新工序"""
    db_operation = db.query(Operation).filter(Operation.id == operation_id).first()
    if not db_operation:
        return None

    update_data = operation_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_operation, field, value)

    db.commit()
    db.refresh(db_operation)
    return db_operation


def delete_operation(db: Session, operation_id: int):
    """删除工序"""
    db_operation = db.query(Operation).filter(Operation.id == operation_id).first()
    if not db_operation:
        return None

    db.delete(db_operation)
    db.commit()
    return db_operation