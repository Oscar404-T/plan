from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from ... import schemas
from ... import crud
from ...database.connection import get_db
from ...core.scheduler import schedule_order_operations, get_shift_for_hour
import math

router = APIRouter()


@router.post("/", response_model=schemas.OrderRead)
def create_order_endpoint(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    db_order = crud.create_order(db, order)
    return db_order


@router.get("/{order_id}", response_model=schemas.OrderRead)
def get_order_endpoint(order_id: int, db: Session = Depends(get_db)):
    db_order = crud.get_order(db, order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    return db_order


@router.post("/schedule", response_model=schemas.ScheduleResponse)
def schedule_endpoint(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    # create order record for reference
    db_order = crud.create_order(db, order)

    # build per-order operations info
    order_ops = crud.get_order_operations(db, db_order.id)
    ops_info = []
    for oo in order_ops:
        op = db.query(crud.models.Operation).filter(crud.models.Operation.id == oo.operation_id).first()
        if op:
            ops_info.append({
                "name": op.name,
                "pieces_per_hour": oo.pieces_per_hour if oo.pieces_per_hour else op.default_pieces_per_hour,
            })

    # fallback global capacity lookup for an operation
    def capacity_lookup_per_op(op_name, dt):
        # find operation entry in ops_info
        matched = next((o for o in ops_info if o["name"] == op_name), None)
        if matched and matched.get("pieces_per_hour"):
            # return the override/default defined per operation
            return matched["pieces_per_hour"]
        # else fallback to global shift capacity
        shift = get_shift_for_hour(dt)
        cap = crud.get_capacity_by_shift(db, shift.value if hasattr(shift, "value") else shift)
        return cap.pieces_per_hour if cap else 0

    # scheduling window: start now (rounded up to next hour) until due_datetime
    now = datetime.utcnow()
    start = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    due = order.due_datetime

    # 计算投入量（考虑估计良率：投入量 = 出货数量 / (估计良率/100)）
    if order.estimated_yield and order.estimated_yield > 0:
        required_input = int(math.ceil(order.quantity / (order.estimated_yield / 100.0)))
    else:
        required_input = order.quantity

    sched = schedule_order_operations(start, due, order.length, order.width, required_input, ops_info, capacity_lookup_per_op)

    allocations = []
    for (s, e, shift, op_name, alloc) in sched["allocations"]:
        allocations.append({"start": s, "end": e, "shift": shift.value if hasattr(shift, "value") else str(shift), "operation": op_name, "allocated": alloc})

    # compute deadline-related flags similar to UI
    total_allocated = sched.get("total_allocated", 0)
    meets_due = total_allocated >= required_input
    expected_completion = None
    meets_due_estimate = meets_due
    if not meets_due:
        remaining_qty = required_input - total_allocated
        last_op_name = ops_info[-1]["name"] if ops_info else None
        last_op_pph = next((o.get('pieces_per_hour') for o in ops_info if o.get('name') == last_op_name), None)
        last_op_ends = [a[1] for a in sched['allocations'] if a[3] == last_op_name]
        last_alloc_end = max(last_op_ends) if last_op_ends else None
        if last_op_pph and last_op_pph > 0:
            hours_needed = int(math.ceil(remaining_qty / last_op_pph))
            base = last_alloc_end if last_alloc_end else start
            expected_completion = base + timedelta(hours=hours_needed)
            meets_due_estimate = expected_completion <= due

    return {
        "order_id": db_order.id,
        "requested_quantity": order.quantity,
        "estimated_yield": order.estimated_yield,
        "required_input": required_input,
        "total_allocated": sched["total_allocated"],
        "allocations": allocations,
        "note": sched["note"],
        "meets_due": meets_due,
        "expected_completion": expected_completion,
        "meets_due_estimate": meets_due_estimate,
    }