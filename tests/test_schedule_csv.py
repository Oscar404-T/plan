from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal, Base, engine
from app import crud
import pytest
from datetime import datetime, timedelta

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    # seed capacities
    caps = crud.list_capacities(db)
    if not caps:
        crud.create_capacity(db, type('C',(object,),{'shift':'day','pieces_per_hour':100,'description':'day'}))
        crud.create_capacity(db, type('C',(object,),{'shift':'night','pieces_per_hour':60,'description':'night'}))
    db.close()
    yield


def test_schedule_csv_endpoint():
    due = (datetime.utcnow() + timedelta(days=1)).replace(microsecond=0).isoformat()
    order_payload = {"length": 100.0, "width": 50.0, "quantity": 500, "due_datetime": due}
    # create order
    r = client.post("/orders/", json=order_payload)
    assert r.status_code == 200
    order = r.json()
    order_id = order.get('id') if isinstance(order, dict) else order['id']

    r2 = client.get(f"/schedule/{order_id}/csv")
    assert r2.status_code == 200
    text = r2.text
    # header should include start,end,shift and allocated (operation may also be present)
    assert "start,end,shift" in text
    assert "allocated" in text
    # The CSV contains a header; allocations may be empty depending on capacity/timing
    # (do not assert allocations content here)
