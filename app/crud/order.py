"""数据库操作（CRUD）- 订单相关

封装常用的数据库读写操作，便于路由层调用并保持业务逻辑集中。
- create_order 会根据传入字段建立 Order 与关联的 OrderOperation
- get_order_operations 返回某订单的工序列表（按 seq 排序）
"""

from sqlalchemy.orm import Session
from .. import models, schemas
from .crud import list_operations, create_operation  # 导入list_operations和create_operation函数
from datetime import datetime
import math


def create_order(db: Session, order: schemas.OrderCreate):
    # compute size if not provided (formula: sqrt(length^2 + width^2) / 25.4)
    size_val = getattr(order, 'size', None)
    if size_val is None:
        size_val = math.sqrt(order.length ** 2 + order.width ** 2) / 25.4

    db_order = models.Order(
        internal_model=getattr(order, 'internal_model', None),
        length=order.length,
        width=order.width,
        thickness=order.thickness,
        size=size_val,
        quantity=order.quantity,
        estimated_yield=getattr(order, 'estimated_yield', None),
        due_datetime=order.due_datetime,
        workshop=getattr(order, 'workshop', None),
        original_length=getattr(order, 'original_length', None),
        original_width=getattr(order, 'original_width', None),
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # attach operations
    ops = []
    if order.operations:
        for idx, op in enumerate(order.operations, start=1):
            # find operation by name or create transient entry
            # prefer existing Operation to allow reuse of defaults
            existing = db.query(models.Operation).filter(models.Operation.name == op.operation_name).first()
            if not existing:
                existing = create_operation(db, op.operation_name)
            db_op = models.OrderOperation(order_id=db_order.id, operation_id=existing.id, seq=idx, pieces_per_hour=op.pieces_per_hour)
            db.add(db_op)
            ops.append(db_op)
    else:
        # default: attach all known operations in DB in their current order
        existing_ops = list_operations(db)
        for idx, existing in enumerate(existing_ops, start=1):
            db_op = models.OrderOperation(order_id=db_order.id, operation_id=existing.id, seq=idx, pieces_per_hour=None)
            db.add(db_op)
            ops.append(db_op)
    db.commit()
    return db_order


def get_order(db: Session, order_id: int):
    return db.query(models.Order).filter(models.Order.id == order_id).first()


def get_order_operations(db: Session, order_id: int):
    """获取订单的工序列表"""
    from ..models.order_operation import OrderOperation
    return db.query(OrderOperation).filter(OrderOperation.order_id == order_id).order_by(OrderOperation.seq).all()


def get_orders(db: Session, skip: int = 0, limit: int = 100):
    """获取订单列表"""
    return db.query(models.Order).offset(skip).limit(limit).all()


def get_order_by_id(db: Session, order_id: int):
    """根据ID获取订单"""
    return db.query(models.Order).filter(models.Order.id == order_id).first()


def list_orders(db: Session):
    """获取所有订单，按创建时间倒序"""
    return db.query(models.Order).order_by(models.Order.created_at.desc()).all()


def update_order(db: Session, order_id: int, order_update: schemas.OrderUpdate):
    """更新订单"""
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        return None

    update_data = order_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_order, field, value)

    db.commit()
    db.refresh(db_order)
    return db_order


def delete_order(db: Session, order_id: int):
    """删除指定ID的订单及其关联的订单工序记录"""
    # 首先删除关联的订单工序记录
    order_operations = db.query(models.OrderOperation).filter(models.OrderOperation.order_id == order_id).all()
    for op in order_operations:
        db.delete(op)
    
    # 然后删除订单本身
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if order:
        db.delete(order)
        db.commit()
        return True
    return False