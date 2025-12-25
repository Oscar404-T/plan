"""模型定义（SQLAlchemy）

包含：User、Admin、Capacity、Order、Operation、OrderOperation 等数据库表的 ORM 定义。
注：字段注释使用中文以便阅读，ShiftEnum 用于表示白班/夜班。
"""

from sqlalchemy import Column, Integer, String, DateTime, Enum, Float
from sqlalchemy.sql import func
from .db import Base
import enum


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=True)


class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)


class ShiftEnum(str, enum.Enum):
    day = "day"
    night = "night"


class Capacity(Base):
    __tablename__ = "capacities"
    id = Column(Integer, primary_key=True, index=True)
    # 分班：'day' 或 'night'（枚举类型）
    shift = Column(Enum(ShiftEnum), nullable=False)
    # 每小时产能（单位：件/小时）
    pieces_per_hour = Column(Integer, nullable=False)
    # 可选说明
    description = Column(String(255), nullable=True)


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    # 可选的内部型号字符串
    internal_model = Column(String(255), nullable=True)
    # 产品尺寸（单位：mm），用于根据公式计算物料尺寸
    length = Column(Float, nullable=False)
    width = Column(Float, nullable=False)
    # 计算得到的尺寸（单位：inch），由 sqrt(length^2 + width^2) / 25.4 得出
    size = Column(Float, nullable=True)
    # 出货数量
    quantity = Column(Integer, nullable=False)
    # 估计良率（百分比，例如 98.5）
    estimated_yield = Column(Float, nullable=True)
    due_datetime = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    # 后续可扩展状态等字段



class Operation(Base):
    __tablename__ = "operations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    default_pieces_per_hour = Column(Integer, nullable=True)
    description = Column(String(255), nullable=True)


class OrderOperation(Base):
    __tablename__ = "order_operations"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, nullable=False, index=True)
    operation_id = Column(Integer, nullable=False)
    seq = Column(Integer, nullable=False)
    # per-order override of pieces per hour for this operation
    pieces_per_hour = Column(Integer, nullable=True)
