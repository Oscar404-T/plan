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
    """Schedule qty through a sequence of operations using a pipelined, per-piece simulation.

    说明：
      - 模拟从 start 到 due 的每小时生产，按工序顺序处理；
      - 第一道工序从可用投入（qty）开始处理，处理完成的件在小时结束时可用于下一道工序；
      - 每小时每道工序的产能由 capacity_lookup_per_op(op_name, hour_dt) 提供（支持 per-order 覆盖）；
      - 如果截止前最后一道工序无法完成所有数量，则返回 note 表示 under-capacity。

    返回：联合分配清单，元素为 (hour_start, hour_end, shift, operation_name, allocated)
    """
    # Prepare data structures
    op_names = [op.get("name") for op in operations]
    processed = {name: 0 for name in op_names}  # 已由该工序处理完成（累加）
    # finished_by_time[op_name] = {finish_time_datetime: count}
    finished_by_time: dict = {name: {} for name in op_names}
    allocations_map: dict = {name: [] for name in op_names}

    cursor = start.replace(minute=0, second=0, microsecond=0)

    # simulate hour by hour forward until due
    while cursor < due:
        any_progress = False
        for idx, name in enumerate(op_names):
            cap = capacity_lookup_per_op(name, cursor)
            if idx == 0:
                # first op can process from remaining input
                available = qty - processed[name]
            else:
                prev = op_names[idx - 1]
                # compute how many of prev have finished by cursor (i.e., finished at or before cursor)
                finished_total_up_to_cursor = sum(count for t, count in finished_by_time[prev].items() if t <= cursor)
                available = max(0, finished_total_up_to_cursor - processed[name])

            alloc = min(cap, available)
            if alloc > 0:
                hour_end = cursor + timedelta(hours=1)
                shift = get_shift_for_hour(cursor)
                allocations_map[name].append((cursor, hour_end, shift, alloc))

                processed[name] += alloc
                finish_time = cursor + timedelta(hours=1)
                finished_by_time[name].setdefault(finish_time, 0)
                finished_by_time[name][finish_time] += alloc
                any_progress = True
        # advance time
        # If no progress was possible this hour, we still advance cursor to next hour (maybe future capacity is available)
        cursor = cursor + timedelta(hours=1)

    # Flatten allocations into chronological list
    flat = []
    for name in op_names:
        for (s, e, shift, alloc) in allocations_map.get(name, []):
            flat.append((s, e, shift, name, alloc))
    # sort flat by start time to be deterministic
    flat.sort(key=lambda x: (x[0], x[3]))

    # total allocated on last operation
    last_op_name = op_names[-1] if op_names else None
    allocated_on_last = processed[last_op_name] if last_op_name else 0

    note = None
    if allocated_on_last < qty:
        note = f"Operation '{last_op_name}' under-capacity: requested {qty}, allocated {allocated_on_last}."

    return {"total_allocated": allocated_on_last, "allocations": flat, "note": note}


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
