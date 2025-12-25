from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal, Base, engine
from app import crud
from datetime import datetime, timedelta

client = TestClient(app)


def setup_env():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    caps = crud.list_capacities(db)
    if not caps:
        crud.create_capacity(db, type('C',(object,),{'shift':'day','pieces_per_hour':100,'description':'day'}))
        crud.create_capacity(db, type('C',(object,),{'shift':'night','pieces_per_hour':60,'description':'night'}))
    db.close()


def test_schedule_ui_shows_summary():
    setup_env()
    due = (datetime.utcnow() + timedelta(days=1)).replace(microsecond=0).isoformat()
    payload = {"length": 100.0, "width": 50.0, "quantity": 100, "due_datetime": due, "estimated_yield": 50.0}
    r = client.post('/orders/', json=payload)
    assert r.status_code == 200
    order = r.json()
    oid = order['id'] if isinstance(order, dict) else order.get('id')

    r2 = client.get(f'/ui/orders/{oid}')
    assert r2.status_code == 200
    text = r2.text
    assert '投入量' in text
    # required input for 50% of 100 should be 200
    assert '200' in text
    assert '已分配' in text
