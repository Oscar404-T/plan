from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ... import schemas
from ... import crud
from ...database.connection import get_db

router = APIRouter()


@router.post("/", response_model=schemas.CapacityRead)
def create_capacity(cap: schemas.CapacityCreate, db: Session = Depends(get_db)):
    return crud.create_capacity(db, cap)


@router.get("/", response_model=list[schemas.CapacityRead])
def list_capacities(db: Session = Depends(get_db)):
    return crud.list_capacities(db)