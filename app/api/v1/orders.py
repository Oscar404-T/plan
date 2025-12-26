from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ... import crud, schemas, models
from ...database.connection import get_db
from ...core.scheduler import get_shift_for_hour, schedule_order_operations
from datetime import datetime, timedelta
import math

router = APIRouter()


@router.post("/", response_model=schemas.OrderRead)
def create_order_endpoint(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    """创建新订单"""
    db_order = crud.create_order(db, order)
    return db_order


@router.get("/{order_id}", response_model=schemas.OrderRead)
def get_order_endpoint(order_id: int, db: Session = Depends(get_db)):
    db_order = crud.get_order(db, order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    return db_order


@router.delete("/{order_id}")
def delete_order_endpoint(order_id: int, db: Session = Depends(get_db)):
    """删除指定ID的订单"""
    success = crud.delete_order(db, order_id)
    if not success:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"message": "Order deleted successfully"}


@router.get("/{order_id}/schedule", response_model=schemas.ScheduleResponse)
def get_order_schedule(
    order_id: int,
    granularity: str = Query("hour", description="时间粒度: hour, shift, day"),
    db: Session = Depends(get_db)
):
    """获取订单排程数据"""
    # 获取订单信息
    order = crud.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # 构建每个订单的操作信息
    order_ops = crud.get_order_operations(db, order_id)
    ops_info = []
    for oo in order_ops:
        op = db.query(models.Operation).filter(models.Operation.id == oo.operation_id).first()
        if op:
            ops_info.append({
                "name": op.name,
                "pieces_per_hour": oo.pieces_per_hour if oo.pieces_per_hour else op.default_pieces_per_hour,
            })

    # 操作产能查找函数
    def capacity_lookup_per_op(op_name, dt):
        matched = next((o for o in ops_info if o["name"] == op_name), None)
        if matched and matched.get("pieces_per_hour"):
            return matched["pieces_per_hour"]
        shift = get_shift_for_hour(dt)
        cap = crud.get_capacity_by_shift(db, shift.value if hasattr(shift, "value") else shift)
        return cap.pieces_per_hour if cap else 0

    # 排程窗口
    now = datetime.utcnow()
    start = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    due = order.due_datetime

    # 计算投入量
    if order.estimated_yield and order.estimated_yield > 0:
        required_input = int(math.ceil(order.quantity / (order.estimated_yield / 100.0)))
    else:
        required_input = order.quantity

    sched = schedule_order_operations(start, due, order.length, order.width, required_input, ops_info, capacity_lookup_per_op)

    allocations = []
    for (s, e, shift, op_name, alloc) in sched["allocations"]:
        allocations.append({
            "start": s,
            "end": e,
            "shift": shift.value if hasattr(shift, "value") else str(shift),
            "operation": op_name,
            "allocated": alloc
        })

    # 计算截止日期相关标志
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

    return schemas.ScheduleResponse(
        order_id=order_id,
        requested_quantity=order.quantity,
        estimated_yield=order.estimated_yield,
        required_input=required_input,
        total_allocated=total_allocated,
        allocations=allocations,
        meets_due=meets_due,
        expected_completion=expected_completion,
        meets_due_estimate=meets_due_estimate,
        note=sched.get("note", None)
    )