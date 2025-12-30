"""数据库操作（CRUD）

封装常用的数据库读写操作，便于路由层调用并保持业务逻辑集中。
- create_order 会根据传入字段建立 Order 与关联的 OrderOperation
- get_order_operations 返回某订单的工序列表（按 seq 排序）
"""

from sqlalchemy.orm import Session
from .. import models, schemas
from ..security import get_password_hash, verify_password
from datetime import datetime
import math


# 用户相关操作
def get_user(db: Session, user_id: int):
    """根据 id 获取用户"""
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    """根据邮箱查找用户（用于避免重复注册）"""
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, user_schema: schemas.UserCreate):
    """创建新用户"""
    db_user = models.User(email=user_schema.email, name=user_schema.name)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# Capacity CRUD
def create_capacity(db: Session, cap: schemas.CapacityCreate):
    """创建新产能记录"""
    db_cap = models.Capacity(shift=cap.shift, pieces_per_hour=cap.pieces_per_hour, description=cap.description)
    db.add(db_cap)
    db.commit()
    db.refresh(db_cap)
    return db_cap


def list_capacities(db: Session):
    """列出所有产能记录"""
    return db.query(models.Capacity).all()


def get_capacity_by_shift(db: Session, shift: str):
    """根据班次获取产能"""
    return db.query(models.Capacity).filter(models.Capacity.shift == shift).first()


# Operations
def create_operation(db: Session, name: str, default_pieces_per_hour: int = None, description: str = None):
    """创建新工序"""
    db_op = models.Operation(name=name, default_pieces_per_hour=default_pieces_per_hour, description=description)
    db.add(db_op)
    db.commit()
    db.refresh(db_op)
    return db_op


def list_operations(db: Session):
    """列出所有工序"""
    return db.query(models.Operation).order_by(models.Operation.id).all()


# Admin helpers
def create_admin(db: Session, username: str, password: str, name: str = None):
    """创建管理员账户"""
    hashed = get_password_hash(password)
    db_admin = models.Admin(username=username, hashed_password=hashed, name=name)
    db.add(db_admin)
    db.commit()
    db.refresh(db_admin)
    return db_admin


def get_admin_by_username(db: Session, username: str):
    """根据用户名获取管理员"""
    return db.query(models.Admin).filter(models.Admin.username == username).first()


def verify_admin_credentials(db: Session, username: str, password: str) -> bool:
    """验证管理员凭据"""
    admin_user = get_admin_by_username(db, username)
    if not admin_user:
        return False
    return verify_password(password, admin_user.hashed_password)


# Orders
def create_order(db: Session, order_schema: schemas.OrderCreate):
    """创建新订单并关联工序
    
    如果未提供工序列表，则使用系统中所有已定义的工序
    """
    # 计算尺寸（如果未提供，公式：sqrt(length^2 + width^2) / 25.4）
    size_val = getattr(order_schema, 'size', None)
    if size_val is None:
        size_val = math.sqrt(order_schema.length ** 2 + order_schema.width ** 2) / 25.4

    db_order = models.Order(
        internal_model=getattr(order_schema, 'internal_model', None),
        length=order_schema.length,
        width=order_schema.width,
        thickness=order_schema.thickness,  # 添加thickness字段
        size=size_val,
        quantity=order_schema.quantity,
        estimated_yield=getattr(order_schema, 'estimated_yield', None),
        due_datetime=order_schema.due_datetime,
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # 关联工序
    ops = []
    if order_schema.operations:
        for idx, op in enumerate(order_schema.operations, start=1):
            # 根据名称查找工序或创建临时条目
            # 优先使用现有工序以允许重用默认值
            existing = db.query(models.Operation).filter(models.Operation.name == op.operation_name).first()
            if not existing:
                existing = create_operation(db, op.operation_name)
            db_op = models.OrderOperation(
                order_id=db_order.id, 
                operation_id=existing.id, 
                seq=idx, 
                pieces_per_hour=op.pieces_per_hour
            )
            db.add(db_op)
            ops.append(db_op)
    else:
        # 默认：按当前顺序附加数据库中的所有已知工序
        existing_ops = list_operations(db)
        for idx, existing in enumerate(existing_ops, start=1):
            db_op = models.OrderOperation(
                order_id=db_order.id, 
                operation_id=existing.id, 
                seq=idx, 
                pieces_per_hour=None
            )
            db.add(db_op)
            ops.append(db_op)
    db.commit()
    return db_order


def get_order(db: Session, order_id: int):
    """根据ID获取订单"""
    return db.query(models.Order).filter(models.Order.id == order_id).first()


def get_order_operations(db: Session, order_id: int):
    """获取订单的工序列表（按顺序）"""
    return db.query(models.OrderOperation).filter(
        models.OrderOperation.order_id == order_id
    ).order_by(models.OrderOperation.seq).all()


def list_orders(db: Session):
    """列出所有订单（按创建时间倒序）"""
    return db.query(models.Order).order_by(models.Order.created_at.desc()).all()