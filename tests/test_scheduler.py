import pytest
from datetime import datetime, timedelta
from app.scheduler import schedule_order
from app.models import ShiftEnum


def fake_capacity(shift):
    return 100 if shift == ShiftEnum.day else 60


def test_schedule_allocates_within_capacity():
    start = datetime(2025,1,1,8,0)
    due = start + timedelta(hours=5)
    qty = 300
    res = schedule_order(start, due, 10.0, 5.0, qty, fake_capacity)
    assert res['total_allocated'] == 300 or res['total_allocated'] <= 5*100


def test_schedule_under_capacity_note():
    start = datetime(2025,1,1,8,0)
    due = start + timedelta(hours=1)
    qty = 500
    res = schedule_order(start, due, 10.0, 5.0, qty, fake_capacity)
    assert res['total_allocated'] <= 100
    assert res['note'] is not None
