from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal, Base, engine
from app import crud
from datetime import datetime, timedelta
import pytest

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    caps = crud.list_capacities(db)
    if not caps:
        crud.create_capacity(db, type('C',(object,),{'shift':'day','pieces_per_hour':100,'description':'day'}))
        crud.create_capacity(db, type('C',(object,),{'shift':'night','pieces_per_hour':60,'description':'night'}))
    db.close()


def test_ui_placeholder_returns_400():
    r = client.get('/ui/orders/%7Border_id%7D')
    assert r.status_code == 400
    assert 'placeholder' in r.json().get('detail', '').lower()


def test_csv_placeholder_returns_400():
    r = client.get('/schedule/%7Border_id%7D/csv')
    assert r.status_code == 400
    assert 'placeholder' in r.json().get('detail', '').lower()
