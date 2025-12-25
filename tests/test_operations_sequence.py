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
    # ensure operations exist
    ops = crud.list_operations(db)
    if not ops:
        crud.create_operation(db, 'op1')
        crud.create_operation(db, 'op2')
    db.close()


def test_operations_do_not_overlap():
    setup_env()
    due = (datetime.utcnow() + timedelta(days=1)).replace(microsecond=0).isoformat()
    payload = {
        "length": 100.0,
        "width": 50.0,
        "quantity": 200,
        "due_datetime": due,
        "estimated_yield": 100.0,
        "operations": [
            {"operation_name": "op1", "pieces_per_hour": 50},
            {"operation_name": "op2", "pieces_per_hour": 100}
        ]
    }
    r = client.post('/schedule/', json=payload)
    assert r.status_code == 200
    data = r.json()
    allocations = data['allocations']

    # group allocations by operation
    grouped = {}
    for a in allocations:
        grouped.setdefault(a['operation'], []).append((a['start'], a['end']))

    assert 'op1' in grouped and 'op2' in grouped

    # ensure that the latest end time of op1 is <= earliest start of op2
    op1_latest_end = max(end for (_, end) in grouped['op1'])
    op2_earliest_start = min(start for (start, _) in grouped['op2'])

    assert op1_latest_end <= op2_earliest_start, f"Operations overlapped: op1 ends at {op1_latest_end}, op2 starts at {op2_earliest_start}"
