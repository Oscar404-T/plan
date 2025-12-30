"""车间产能API路由

定义车间产能相关的API端点
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ... import crud, schemas
from ...database.connection import get_db

router = APIRouter()


@router.post("/workshop-capacities/", response_model=schemas.WorkshopCapacityRead)
def create_workshop_capacity(
    capacity: schemas.WorkshopCapacityCreate,
    db: Session = Depends(get_db)
):
    """创建车间产能记录"""
    db_capacity = crud.create_workshop_capacity(db, capacity)
    return db_capacity


@router.get("/workshop-capacities/{capacity_id}", response_model=schemas.WorkshopCapacityRead)
def get_workshop_capacity(capacity_id: int, db: Session = Depends(get_db)):
    """获取指定ID的车间产能记录"""
    capacity = crud.get_workshop_capacity(db, capacity_id)
    if not capacity:
        raise HTTPException(status_code=404, detail="车间产能记录未找到")
    return capacity


@router.put("/workshop-capacities/{capacity_id}", response_model=schemas.WorkshopCapacityRead)
def update_workshop_capacity(
    capacity_id: int,
    capacity_update: schemas.WorkshopCapacityUpdate,
    db: Session = Depends(get_db)
):
    """更新车间产能记录"""
    db_capacity = crud.update_workshop_capacity(db, capacity_id, capacity_update)
    if not db_capacity:
        raise HTTPException(status_code=404, detail="车间产能记录未找到")
    return db_capacity


@router.delete("/workshop-capacities/{capacity_id}")
def delete_workshop_capacity(capacity_id: int, db: Session = Depends(get_db)):
    """删除车间产能记录"""
    capacity = crud.delete_workshop_capacity(db, capacity_id)
    if not capacity:
        raise HTTPException(status_code=404, detail="车间产能记录未找到")
    return {"message": "车间产能记录已删除"}


@router.get("/workshop-capacities/", response_model=list[schemas.WorkshopCapacityRead])
def get_workshop_capacities(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取车间产能列表"""
    capacities = crud.get_all_workshop_capacities(db, skip=skip, limit=limit)
    return capacities


@router.get("/workshop-capacities/workshop/{workshop}", response_model=list[schemas.WorkshopCapacityRead])
def get_workshop_capacities_by_workshop(workshop: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """根据车间获取产能列表"""
    capacities = crud.get_workshop_capacities_by_workshop(db, workshop, skip=skip, limit=limit)
    return capacities


@router.get("/workshop-capacities/operation/{operation_id}", response_model=list[schemas.WorkshopCapacityRead])
def get_workshop_capacities_by_operation(operation_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """根据工序获取产能列表"""
    capacities = crud.get_workshop_capacities_by_operation(db, operation_id, skip=skip, limit=limit)
    return capacities