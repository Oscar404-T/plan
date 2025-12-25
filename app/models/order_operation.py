from sqlalchemy import Column, Integer, String
from .base import Base


class OrderOperation(Base):
    __tablename__ = "order_operations"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, nullable=False, index=True)
    operation_id = Column(Integer, nullable=False)
    seq = Column(Integer, nullable=False)
    # per-order override of pieces per hour for this operation
    pieces_per_hour = Column(Integer, nullable=True)