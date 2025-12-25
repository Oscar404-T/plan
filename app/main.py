from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from . import crud, models, schemas
from .db import engine, get_db, Base
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="Plan App")


@app.on_event("startup")
def create_tables():
    """Attempt to create tables on startup; don't crash app if DB is unavailable."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
    except SQLAlchemyError as exc:
        logger.warning("Could not create tables on startup: %s", exc)


@app.get("/", tags=["meta"])
def root():
    """Simple root endpoint so GET / returns 200 (useful for smoke tests)."""
    return {"status": "ok"}


from fastapi.responses import JSONResponse
from sqlalchemy import text


@app.get("/health/db", tags=["meta"])
def health_db():
    """Attempt a lightweight DB query and return 200 if successful, 503 otherwise."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"db": "ok"}
    except Exception as exc:
        # Keep the error short for the response; full details are in logs
        return JSONResponse(status_code=503, content={"db": "error", "detail": str(exc)})


@app.post("/users/", response_model=schemas.UserRead)
def create_user_endpoint(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = crud.get_user_by_email(db, user.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db, user)


@app.get("/users/{user_id}", response_model=schemas.UserRead)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user
