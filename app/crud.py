"""数据库操作（CRUD）

封装常用的数据库读写操作，便于路由层调用并保持业务逻辑集中。
- create_order 会根据传入字段建立 Order 与关联的 OrderOperation
- get_order_operations 返回某订单的工序列表（按 seq 排序）
"""

from sqlalchemy.orm import Session
from . import models, schemas
from datetime import datetime


# 用户相关操作
def get_user(db: Session, user_id: int):
    """根据 id 获取用户"""
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    """根据邮箱查找用户（用于避免重复注册）"""
    return db.query(models.User).filter(models.User.email == email).first()
import math


def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(email=user.email, name=user.name)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# Capacity CRUD
def create_capacity(db: Session, cap: schemas.CapacityCreate):
    db_cap = models.Capacity(shift=cap.shift, pieces_per_hour=cap.pieces_per_hour, description=cap.description)
    db.add(db_cap)
    db.commit()
    db.refresh(db_cap)
    return db_cap


def list_capacities(db: Session):
    return db.query(models.Capacity).all()


def get_capacity_by_shift(db: Session, shift: str):
    return db.query(models.Capacity).filter(models.Capacity.shift == shift).first()


# Operations
def create_operation(db: Session, name: str, default_pieces_per_hour: int = None, description: str = None):
    db_op = models.Operation(name=name, default_pieces_per_hour=default_pieces_per_hour, description=description)
    db.add(db_op)
    db.commit()
    db.refresh(db_op)
    return db_op


def list_operations(db: Session):
    return db.query(models.Operation).order_by(models.Operation.id).all()


# Admin helpers
from .security import get_password_hash, verify_password


def create_admin(db: Session, username: str, password: str, name: str = None):
    hashed = get_password_hash(password)
    db_admin = models.Admin(username=username, hashed_password=hashed, name=name)
    db.add(db_admin)
    db.commit()
    db.refresh(db_admin)
    return db_admin


def get_admin_by_username(db: Session, username: str):
    return db.query(models.Admin).filter(models.Admin.username == username).first()


def verify_admin_credentials(db: Session, username: str, password: str) -> bool:
    admin = get_admin_by_username(db, username)
    if not admin:
        return False
    return verify_password(password, admin.hashed_password)


# Orders
def create_order(db: Session, order: schemas.OrderCreate):
    # compute size if not provided (formula: sqrt(length^2 + width^2) / 25.4)
    size_val = getattr(order, 'size', None)
    if size_val is None:
        size_val = math.sqrt(order.length ** 2 + order.width ** 2) / 25.4

    db_order = models.Order(
        internal_model=getattr(order, 'internal_model', None),
        length=order.length,
        width=order.width,
        size=size_val,
        quantity=order.quantity,
        estimated_yield=getattr(order, 'estimated_yield', None),
        due_datetime=order.due_datetime,
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
    return db.query(models.OrderOperation).filter(models.OrderOperation.order_id == order_id).order_by(models.OrderOperation.seq).all()


def list_orders(db: Session):
    return db.query(models.Order).order_by(models.Order.created_at.desc()).all()
