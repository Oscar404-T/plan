from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from ... import schemas
from ... import crud
from ...database.connection import get_db
from ...core import auth as app_auth

router = APIRouter()


@router.post("/login")
def login(request: Request, username: str, password: str, db: Session = Depends(get_db)):
    success = app_auth.authenticate_and_login(request, db, username, password)
    if success:
        return RedirectResponse(url="/", status_code=303)
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")


@router.post("/logout")
def logout(request: Request):
    app_auth.clear_admin_session(request)
    return RedirectResponse(url="/", status_code=303)