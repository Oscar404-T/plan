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


def test_schedule_ui_shows_expected_overdue():
    setup_env()
    due = (datetime.utcnow() + timedelta(hours=2)).replace(microsecond=0).isoformat()
    # two operations: first fast, last very slow -> should predict overdue
    payload = {
        "length": 100.0,
        "width": 50.0,
        "quantity": 100,
        "due_datetime": due,
        "estimated_yield": 100.0,
        "operations": [
            {"operation_name": "cut", "pieces_per_hour": 1000},
            {"operation_name": "pack", "pieces_per_hour": 10}
        ]
    }
    r = client.post('/orders/', json=payload)
    assert r.status_code == 200
    order = r.json()
    oid = order['id'] if isinstance(order, dict) else order.get('id')

    r2 = client.get(f'/ui/orders/{oid}')
    assert r2.status_code == 200
    text = r2.text
    assert '预计超期' in text
    assert '预计完成' in text


def test_schedule_ui_shows_expected_on_time():
    setup_env()
    due = (datetime.utcnow() + timedelta(days=2)).replace(microsecond=0).isoformat()
    # make last op fast enough to meet due
    payload = {
        "length": 100.0,
        "width": 50.0,
        "quantity": 100,
        "due_datetime": due,
        "estimated_yield": 100.0,
        "operations": [
            {"operation_name": "cut", "pieces_per_hour": 1000},
            {"operation_name": "pack", "pieces_per_hour": 1000}
        ]
    }
    r = client.post('/orders/', json=payload)
    assert r.status_code == 200
    order = r.json()
    oid = order['id'] if isinstance(order, dict) else order.get('id')

    r2 = client.get(f'/ui/orders/{oid}')
    assert r2.status_code == 200
    text = r2.text
    assert '预计满足截止' in text or '满足截止' in text
    # when already fully allocated we may not display an estimated completion time; that's OK
    assert '预计超期' not in text
