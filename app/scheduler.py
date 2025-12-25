"""调度器模块

实现按小时分配产能的逻辑，并包含从截止时间向前分配（为保证工序顺序）
主要函数：
- allocate_by_capacity: 从起始向前分配到截止（按时间向前）
- allocate_backward: 从截止向前分配（用于串联工序，保证后工序先完成）
- schedule_order_operations: 对多道工序按顺序做向后分配
"""

from datetime import datetime, timedelta, time
from typing import List, Tuple
from .models import ShiftEnum

# 班次窗口（本地时刻，无时区处理），符合需求：
# 白班 08:00 - 19:00（11 小时，含 1 小时休息）
# 夜班 20:00 - 07:00（11 小时，含 1 小时休息）
# 调度以小时为粒度，按整点切分

DAY_START = time(8, 0)
DAY_END = time(19, 0)
NIGHT_START = time(20, 0)
NIGHT_END = time(7, 0)


def is_day_shift(dt: datetime) -> bool:
    t = dt.time()
    return DAY_START <= t < DAY_END


def is_night_shift(dt: datetime) -> bool:
    t = dt.time()
    # night includes times from 20:00 to 23:59 or 00:00 to 07:00
    return (t >= NIGHT_START) or (t < NIGHT_END)


def next_hour(dt: datetime) -> datetime:
    return (dt + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)


def get_shift_for_hour(dt: datetime) -> ShiftEnum:
    if is_day_shift(dt):
        return ShiftEnum.day
    return ShiftEnum.night


def allocate_by_capacity(start: datetime, end: datetime, qty: int, capacity_lookup) -> Tuple[int, List[Tuple[datetime, datetime, ShiftEnum, int]]]:
    """按时间正序分配数量到每小时槽位。

    参数：
      - start, end: 调度窗口（start 包含，end 排除）
      - qty: 需分配的目标数量
      - capacity_lookup(shift): 根据班次或时间返回该小时的产能
    返回：已分配总数与每小时分配清单
    """
    allocations = []
    cursor = start.replace(minute=0, second=0, microsecond=0)
    total_allocated = 0

    while cursor < end and total_allocated < qty:
        hour_end = cursor + timedelta(hours=1)
        shift = get_shift_for_hour(cursor)
        cap = capacity_lookup(shift)
        alloc = min(cap, qty - total_allocated)
        if alloc > 0:
            allocations.append((cursor, hour_end, shift, alloc))
            total_allocated += alloc
        cursor = hour_end
    return total_allocated, allocations


def allocate_backward(start: datetime, end: datetime, qty: int, capacity_lookup_op) -> (int, list):
    """从截止时间向前分配，用于保证工序之间的先后顺序。

    例如：最后一道工序优先从截止时间向前排班，前一道工序必须在其开始前完成。
    """
    allocations = []
    total_allocated = 0

    # normalize end to hour boundary
    cursor_end = end.replace(minute=0, second=0, microsecond=0)
    # we will consider the hour starting at cursor_end - 1 hour
    while cursor_end > start and total_allocated < qty:
        hour_start = cursor_end - timedelta(hours=1)
        shift = get_shift_for_hour(hour_start)
        cap = capacity_lookup_op(hour_start)
        alloc = min(cap, qty - total_allocated)
        if alloc > 0:
            allocations.append((hour_start, cursor_end, shift, alloc))
            total_allocated += alloc
        cursor_end = hour_start

    # allocations are collected from latest to earliest; reverse to chronological order
    allocations.reverse()
    return total_allocated, allocations


# Per-operation sequential scheduler
def schedule_order_operations(start: datetime, due: datetime, length: float, width: float, qty: int, operations: list, capacity_lookup_per_op) -> dict:
    """Schedule qty through a sequence of operations.

    operations: list of {'name': str}
    capacity_lookup_per_op(op_name, hour_dt) -> int

    策略说明（已中文注释）：
      - 从最后一道工序开始，向截止时间回溯分配；
      - 前一道工序的可用截止时间为后一工序最早分配开始时间；
      - 若某道工序无法在截止前分配完全部数量，则在返回结果的 note 字段标注为 "under-capacity"。

    返回：联合分配清单，元素为 (hour_start, hour_end, shift, operation_name, allocated)
    """
    op_allocations = {}
    op_deadline = due
    overall_allocated = True
    note = None

    # Iterate operations backwards
    for op in reversed(operations):
        name = op.get("name")
        # capacity_lookup for this op: wrapper
        def cap_lookup_for_hour(dt, op_name=name):
            return capacity_lookup_per_op(op_name, dt)

        allocated, allocs = allocate_backward(start, op_deadline, qty, cap_lookup_for_hour)
        op_allocations[name] = allocs
        if allocated < qty:
            overall_allocated = False
            note = f"Operation '{name}' under-capacity: requested {qty}, allocated {allocated}."
        # next op's deadline becomes earliest start of this op's allocations
        if allocs:
            earliest = allocs[0][0]
            op_deadline = earliest
        else:
            # no allocation at all; set deadline to start to prevent prior allocation
            op_deadline = start

    # Flatten allocations into a list with operation name
    flat = []
    for op in operations:
        name = op.get("name")
        allocs = op_allocations.get(name, [])
        for (s, e, shift, alloc) in allocs:
            flat.append((s, e, shift, name, alloc))

    # total allocated on last operation
    last_op_name = operations[-1]["name"] if operations else None
    last_allocs = op_allocations.get(last_op_name, []) if last_op_name else []
    allocated_on_last = sum(a[3] for a in last_allocs)

    return {"total_allocated": allocated_on_last, "allocations": flat, "note": note if not overall_allocated else None}


# Backwards-compatible simple scheduler for single-operation tests
def schedule_order(start: datetime, due: datetime, length: float, width: float, qty: int, capacity_lookup):
    """Compatibility wrapper used by tests that expect a single operation scheduler.

    capacity_lookup(shift) -> int
    """
    def capacity_lookup_per_op(op_name, dt):
        shift = get_shift_for_hour(dt)
        return capacity_lookup(shift)

    ops = [{"name": "single"}]
    return schedule_order_operations(start, due, length, width, qty, ops, capacity_lookup_per_op)
