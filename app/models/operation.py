from sqlalchemy import Column, Integer, String
from .base import Base


class Operation(Base):
    __tablename__ = "operations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    default_pieces_per_hour = Column(Integer, nullable=True)
    description = Column(String(255), nullable=True)