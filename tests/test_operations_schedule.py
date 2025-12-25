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
    # seed operations
    ops = crud.list_operations(db)
    if not ops:
        names = ["点胶","切割","边抛","边强","分片","酸洗","钢化","面强","AOI","包装"]
        for n in names:
            crud.create_operation(db, n)
    db.close()


def test_order_with_per_operation_capacity():
    setup_env()
    due = (datetime.utcnow() + timedelta(days=1)).replace(microsecond=0).isoformat()
    order_payload = {
        "length": 100.0,
        "width": 50.0,
        "quantity": 500,
        "due_datetime": due,
        # override per-op: set low capacity on '钢化' to force under-capacity there
        "operations": [
            {"operation_name": "点胶", "pieces_per_hour": 100},
            {"operation_name": "切割", "pieces_per_hour": 100},
            {"operation_name": "钢化", "pieces_per_hour": 20},
            {"operation_name": "包装", "pieces_per_hour": 100},
        ],
    }

    r = client.post("/schedule/", json=order_payload)
    assert r.status_code == 200
    data = r.json()
    assert 'allocations' in data
    # there should be allocations and a note about under-capacity due to '钢化'
    assert data['note'] is not None
    # ensure allocations report operation names
    ops = set(a['operation'] for a in data['allocations'])
    assert '钢化' in ops

