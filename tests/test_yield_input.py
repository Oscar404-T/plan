from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal, Base, engine
from app import crud
from datetime import datetime, timedelta
import math

client = TestClient(app)


def setup_env():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    caps = crud.list_capacities(db)
    if not caps:
        crud.create_capacity(db, type('C',(object,),{'shift':'day','pieces_per_hour':100,'description':'day'}))
        crud.create_capacity(db, type('C',(object,),{'shift':'night','pieces_per_hour':60,'description':'night'}))
    db.close()


def test_required_input_calculation():
    setup_env()
    due = (datetime.utcnow() + timedelta(days=1)).replace(microsecond=0).isoformat()
    payload = {"length": 100.0, "width": 50.0, "quantity": 500, "due_datetime": due, "estimated_yield": 98.5}
    r = client.post('/schedule/', json=payload)
    assert r.status_code == 200
    data = r.json()
    expected = int(math.ceil(500 / (98.5 / 100.0)))
    assert data.get('required_input') == expected


def test_required_input_with_low_yield():
    setup_env()
    due = (datetime.utcnow() + timedelta(days=1)).replace(microsecond=0).isoformat()
    payload = {"length": 100.0, "width": 50.0, "quantity": 100, "due_datetime": due, "estimated_yield": 50.0}
    r = client.post('/schedule/', json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data.get('required_input') == 200
