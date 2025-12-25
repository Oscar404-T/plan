from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ... import schemas
from ... import crud
from ...database.connection import get_db

router = APIRouter()


@router.post("/", response_model=schemas.OperationRead)
def create_operation(op: schemas.OperationCreate, db: Session = Depends(get_db)):
    return crud.create_operation(db, op.name, op.default_pieces_per_hour, op.description)


@router.get("/", response_model=list[schemas.OperationRead])
def list_operations(db: Session = Depends(get_db)):
    return crud.list_operations(db)