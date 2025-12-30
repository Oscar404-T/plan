"""产能API路由

定义产能相关的API端点
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ... import crud, schemas
from ...database.connection import get_db

router = APIRouter()


@router.post("/capacities/", response_model=schemas.CapacityRead)
def create_new_capacity(capacity: schemas.CapacityCreate, db: Session = Depends(get_db)):
    """创建新的产能记录"""
    return crud.create_capacity(db=db, capacity=capacity)


@router.get("/capacities/{capacity_id}", response_model=schemas.CapacityRead)
def read_capacity(capacity_id: int, db: Session = Depends(get_db)):
    """根据ID获取产能记录"""
    capacity = crud.get_capacity(db=db, capacity_id=capacity_id)
    if not capacity:
        raise HTTPException(status_code=404, detail="产能记录未找到")
    return capacity


@router.put("/capacities/{capacity_id}", response_model=schemas.CapacityRead)
def update_capacity(capacity_id: int, capacity_update: schemas.CapacityUpdate, db: Session = Depends(get_db)):
    """更新产能记录"""
    db_capacity = crud.update_capacity(db=db, capacity_id=capacity_id, capacity_update=capacity_update)
    if not db_capacity:
        raise HTTPException(status_code=404, detail="产能记录未找到")
    return db_capacity


@router.delete("/capacities/{capacity_id}")
def delete_capacity(capacity_id: int, db: Session = Depends(get_db)):
    """删除产能记录"""
    db_capacity = crud.delete_capacity(db=db, capacity_id=capacity_id)
    if not db_capacity:
        raise HTTPException(status_code=404, detail="产能记录未找到")
    return {"message": "产能记录删除成功"}


@router.get("/capacities/", response_model=List[schemas.CapacityRead])
def read_capacities(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取产能列表"""
    capacities = crud.get_all_capacities(db=db, skip=skip, limit=limit)
    return capacities


@router.get("/capacities/workshop/{workshop}", response_model=List[schemas.CapacityRead])
def read_capacities_by_workshop(workshop: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """根据车间获取产能列表"""
    capacities = crud.get_capacities_by_workshop(db=db, workshop=workshop, skip=skip, limit=limit)
    return capacities