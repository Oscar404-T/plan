"""应用入口与路由（中文注释）

该模块定义 FastAPI 应用实例和中间件配置。
路由定义已拆分到 app/api/v1/ 目录下按功能模块组织。
"""

from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from .config.settings import settings
from .db import engine, Base

# 导入所有路由模块以注册路由
from .api.v1 import auth_router, users_router, capacities_router, operations_router, orders_router

import logging
from . import crud
from . import schemas
from .db import get_db
from . import auth as app_auth
from .core.scheduler import schedule_order_operations, get_shift_for_hour
from . import models
from datetime import datetime, timedelta
import math
from sqlalchemy.orm import Session
import io
import csv

logger = logging.getLogger(__name__)

# 登录验证依赖
def require_admin_login(request: Request):
    """检查用户是否已登录，如果没有则重定向到登录页面"""
    if not app_auth.is_admin(request):
        return RedirectResponse(url="/ui/login", status_code=303)
    return request


app = FastAPI(title="Plan App")

# Session middleware (simple cookie-based session)
secret = settings.SECRET_KEY or "change-me-in-production"

# Try to load SessionMiddleware (dependent on itsdangerous); if missing, disable session-based UI and show a helpful message
_sessions_available = True
try:
    from starlette.middleware.sessions import SessionMiddleware
    app.add_middleware(SessionMiddleware, secret_key=secret)
except Exception as exc:  # pragma: no cover - runtime environment may lack optional deps
    import logging
    logging.getLogger(__name__).warning("SessionMiddleware not available: %s. UI login will be disabled until you install 'itsdangerous'", exc)
    _sessions_available = False


templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def create_tables():
    """应用启动时尝试创建表；若数据库不可用则仅记录警告而不抛出异常，方便本地开发。"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
    except Exception as exc:
        logger.warning("Could not create tables on startup: %s", exc)


# 健康检查路由
@app.get("/", tags=["meta"])
def root():
    """根路由，用于快速探活（返回 200）。"""
    return {"status": "ok"}


from fastapi.responses import JSONResponse
from sqlalchemy import text


@app.get("/health/db", tags=["meta"])
def health_db():
    """Attempt a lightweight DB query and return 200 if successful, 503 otherwise."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"db": "ok"}
    except Exception as exc:
        # Keep the error short for the response; full details are in logs
        return JSONResponse(status_code=500, content={"db": "error", "detail": str(exc)})


# 包含各个API路由
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(users_router, prefix="/api/v1", tags=["users"])
app.include_router(capacities_router, prefix="/api/v1", tags=["capacities"])
app.include_router(operations_router, prefix="/api/v1", tags=["operations"])
app.include_router(orders_router, prefix="/api/v1", tags=["orders"])


# UI 路由
@app.get("/ui/login", response_class=HTMLResponse)
def login_page(request: Request):
    """渲染登录页面"""
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/ui/login")
def login(
    username: str = Form(...), 
    password: str = Form(...), 
    request: Request = Request,
    db: Session = Depends(get_db)
):
    """处理登录请求"""
    success = app_auth.authenticate_and_login(request, db, username, password)
    if success:
        return RedirectResponse(url="/ui/orders/create", status_code=303)
    else:
        return templates.TemplateResponse("login.html", {"request": request, "error": "用户名或密码错误"}, status_code=401)


@app.get("/ui/logout")
def logout(request: Request):
    """处理登出请求"""
    app_auth.clear_admin_session(request)
    return RedirectResponse(url="/ui/login", status_code=303)


@app.get("/ui/orders/{order_id}/schedule", response_class=HTMLResponse)
def view_order_schedule_ui(order_id: int, request: Request, db: Session = Depends(get_db)):
    # 检查用户是否已登录
    if not app_auth.is_admin(request):
        return RedirectResponse(url="/ui/login", status_code=303)
        
    try:
        # 获取订单信息
        db_order = crud.get_order(db, order_id)
        if not db_order:
            raise HTTPException(status_code=404, detail="订单未找到")
        
        # 获取订单的工序信息
        order_ops = crud.get_order_operations(db, order_id)
        ops_info = []
        for oo in order_ops:
            op = db.query(models.Operation).filter(models.Operation.id == oo.operation_id).first()
            if op:
                ops_info.append({
                    "name": op.name,
                    "pieces_per_hour": oo.pieces_per_hour if oo.pieces_per_hour else op.default_pieces_per_hour,
                })

        # 调度函数
        def capacity_lookup_per_op(op_name, dt):
            matched = next((o for o in ops_info if o["name"] == op_name), None)
            if matched and matched.get("pieces_per_hour"):
                return matched["pieces_per_hour"]
            shift = get_shift_for_hour(dt)
            cap = crud.get_capacity_by_shift(db, shift.value if hasattr(shift, "value") else shift)
            return cap.pieces_per_hour if cap else 0

        # 计算排程
        now = datetime.utcnow()
        start = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        due = db_order.due_datetime

        # 计算投入量（考虑估计良率：投入量 = 出货数量 / (估计良率/100)）
        req_qty = db_order.quantity
        if db_order.estimated_yield and db_order.estimated_yield > 0:
            req_qty = int(math.ceil(db_order.quantity / (db_order.estimated_yield / 100.0)))

        sched = schedule_order_operations(start, due, db_order.length, db_order.width, req_qty, ops_info, capacity_lookup_per_op)

        # 格式化分配数据
        allocations = []
        for (s, e, shift, op_name, alloc) in sched["allocations"]:
            allocations.append({
                "start": s,
                "end": e,
                "shift": shift.value if hasattr(shift, "value") else str(shift),
                "operation": op_name,
                "allocated": alloc
            })

        # 计算统计信息
        total_allocated = sched.get("total_allocated", 0)
        meets_due = total_allocated >= req_qty
        expected_completion = None
        meets_due_estimate = meets_due
        
        if not meets_due:
            remaining_qty = req_qty - total_allocated
            last_op_name = ops_info[-1]["name"] if ops_info else None
            last_op_pph = next((o.get('pieces_per_hour') for o in ops_info if o.get('name') == last_op_name), None)
            last_op_ends = [a["end"] for a in allocations if a["operation"] == last_op_name]
            last_alloc_end = max(last_op_ends) if last_op_ends else None
            if last_op_pph and last_op_pph > 0:
                hours_needed = int(math.ceil(remaining_qty / last_op_pph))
                base = last_alloc_end if last_alloc_end else start
                expected_completion = base + timedelta(hours=hours_needed)
                meets_due_estimate = expected_completion <= due

        # 计算分配百分比
        allocated_pct = (total_allocated / req_qty) * 100 if req_qty > 0 else 0
        remaining = req_qty - total_allocated
        
        is_admin = app_auth.is_admin(request)

        return templates.TemplateResponse("schedule.html", {
            "request": request,
            "order": db_order,
            "required_input": req_qty,
            "total_allocated": total_allocated,
            "allocations": allocations,
            "meets_due": meets_due,
            "expected_completion": expected_completion,
            "meets_due_estimate": meets_due_estimate,
            "allocated_pct": allocated_pct,
            "remaining": remaining,
            "ops_info": ops_info,
            "is_admin": is_admin
        })
        
    except Exception as e:
        logger.error(f"Error displaying schedule for order {order_id}: {str(e)}", exc_info=True)
        return templates.TemplateResponse("order_list.html", {
            "request": request, 
            "orders": crud.list_orders(db),
            "error": f"查看订单排程时发生错误: {str(e)}",
            "is_admin": app_auth.is_admin(request)
        })


@app.get("/ui/orders", response_class=HTMLResponse)
def list_orders_ui(request: Request, db: Session = Depends(get_db)):
    # 检查用户是否已登录
    if not app_auth.is_admin(request):
        return RedirectResponse(url="/ui/login", status_code=303)
        
    try:
        # 获取所有订单，按创建时间倒序排列
        orders = crud.list_orders(db)
        is_admin = app_auth.is_admin(request)
        
        return templates.TemplateResponse("order_list.html", {
            "request": request, 
            "orders": orders,
            "is_admin": is_admin
        })
    except Exception as e:
        logger.error(f"Error listing orders: {str(e)}", exc_info=True)
        return templates.TemplateResponse("order_form.html", {
            "request": request, 
            "operations": crud.list_operations(db),
            "error": f"获取订单列表时发生错误: {str(e)}",
            "is_admin": app_auth.is_admin(request)
        })


@app.get("/ui/orders/create", response_class=HTMLResponse)
def create_order_ui(request: Request, db: Session = Depends(get_db)):
    # 检查用户是否已登录
    if not app_auth.is_admin(request):
        return RedirectResponse(url="/ui/login", status_code=303)
        
    try:
        is_admin = app_auth.is_admin(request)
        return templates.TemplateResponse("order_form.html", {
            "request": request, 
            "operations": crud.list_operations(db),
            "is_admin": is_admin
        })
    except Exception as e:
        logger.error(f"Error loading order creation form: {str(e)}", exc_info=True)
        return templates.TemplateResponse("order_form.html", {
            "request": request, 
            "operations": crud.list_operations(db),
            "error": f"加载订单创建表单时发生错误: {str(e)}",
            "is_admin": app_auth.is_admin(request)
        })


@app.post("/ui/orders/create", response_class=HTMLResponse)
async def create_order_ui(
    internal_model: str = Form(None),
    length: float = Form(...),
    width: float = Form(...),
    quantity: int = Form(...),
    estimated_yield: float = Form(None),
    due_datetime: str = Form(...),
    workshop: str = Form(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """处理订单创建请求并返回排产结果"""
    # 检查用户是否已登录
    if not app_auth.is_admin(request):
        return RedirectResponse(url="/ui/login", status_code=303)
    
    try:
        # 解析日期时间
        due_dt = datetime.fromisoformat(due_datetime.replace('T', ' '))
        
        # 从请求中获取表单数据
        form_data = await request.form()
        
        # 收集工序信息
        operations = []
        all_ops = crud.list_operations(db)
        for op in all_ops:
            op_qty = form_data.get(f"op_{op.id}")
            if op_qty and op_qty.strip():
                operations.append(schemas.OrderOperationCreate(
                    operation_name=op.name,
                    pieces_per_hour=int(op_qty)
                ))
        
        # 创建订单请求对象
        order_data = schemas.OrderCreate(
            internal_model=internal_model,
            length=length,
            width=width,
            quantity=quantity,
            estimated_yield=estimated_yield,
            due_datetime=due_dt,
            workshop=workshop,
            operations=operations if operations else None
        )
        
        # 创建订单并计算排产
        db_order = crud.create_order(db, order_data)
        
        # 构建工序信息
        order_ops = crud.get_order_operations(db, db_order.id)
        ops_info = []
        for oo in order_ops:
            op = db.query(models.Operation).filter(models.Operation.id == oo.operation_id).first()
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
        due = due_dt

        # 检查是否有工序定义，如果没有则无法排程
        if not ops_info:
            logger.error("No operations defined for scheduling")
            return templates.TemplateResponse("order_form.html", {
                "request": request, 
                "operations": all_ops,
                "error": "无法排程：未定义任何工序，请先添加工序。",
                "is_admin": app_auth.is_admin(request)
            })

        # 计算投入量（考虑估计良率：投入量 = 出货数量 / (估计良率/100)）
        if order_data.estimated_yield and order_data.estimated_yield > 0:
            required_input = int(math.ceil(order_data.quantity / (order_data.estimated_yield / 100.0)))
        else:
            required_input = order_data.quantity

        sched = schedule_order_operations(start, due, order_data.length, order_data.width, required_input, ops_info, capacity_lookup_per_op)

        allocations = []
        for (s, e, shift, op_name, alloc) in sched["allocations"]:
            allocations.append({
                "start": s, 
                "end": e, 
                "shift": shift.value if hasattr(shift, "value") else str(shift), 
                "operation": op_name, 
                "allocated": alloc
            })

        # compute deadline-related flags similar to UI
        total_allocated = sched.get("total_allocated", 0)
        meets_due = total_allocated >= required_input
        expected_completion = None
        meets_due_estimate = meets_due
        if not meets_due:
            remaining_qty = required_input - total_allocated
            last_op_name = ops_info[-1]["name"] if ops_info else None
            last_oph = next((o.get('pieces_per_hour') for o in ops_info if o.get('name') == last_op_name), None)
            last_op_ends = [a[1] for a in sched['allocations'] if a[3] == last_op_name]
            last_alloc_end = max(last_op_ends) if last_op_ends else None
            if last_oph and last_oph > 0:
                hours_needed = int(math.ceil(remaining_qty / last_oph))
                base = last_alloc_end if last_alloc_end else start
                expected_completion = base + timedelta(hours=hours_needed)
                meets_due_estimate = expected_completion <= due

        # 计算分配百分比
        allocated_pct = (total_allocated / required_input) * 100 if required_input > 0 else 0
        remaining = required_input - total_allocated

        return templates.TemplateResponse("schedule.html", {
            "request": request,
            "order": db_order,
            "required_input": required_input,
            "total_allocated": total_allocated,
            "allocations": allocations,
            "meets_due": meets_due,
            "expected_completion": expected_completion,
            "meets_due_estimate": meets_due_estimate,
            "allocated_pct": allocated_pct,
            "remaining": remaining,
            "is_admin": app_auth.is_admin(request)
        })
    
    except ValueError as ve:
        logger.error(f"Value error during order creation: {str(ve)}")
        return templates.TemplateResponse("order_form.html", {
            "request": request, 
            "operations": crud.list_operations(db),
            "error": f"输入值错误: {str(ve)}",
            "is_admin": app_auth.is_admin(request)
        })
    except Exception as e:
        logger.error(f"Error during order creation and scheduling: {str(e)}", exc_info=True)
        return templates.TemplateResponse("order_form.html", {
            "request": request, 
            "operations": crud.list_operations(db),
            "error": f"创建订单和排程时发生错误: {str(e)}",
            "is_admin": app_auth.is_admin(request)
        })


# Order and scheduling API endpoint
@app.post("/schedule/", response_model=schemas.ScheduleResponse)
def schedule_endpoint(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    try:
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

        # 检查是否有工序定义
        if not ops_info:
            raise HTTPException(status_code=400, detail="No operations defined for scheduling")

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
    except Exception as e:
        logger.error(f"Error during API scheduling: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Scheduling error: {str(e)}")


@app.get("/schedule/{order_id}/csv")
def get_schedule_csv(order_id: int, request: Request, db: Session = Depends(get_db)):
    """导出排程结果为CSV格式"""
    # 检查用户是否已登录
    if not app_auth.is_admin(request):
        return RedirectResponse(url="/ui/login", status_code=303)
    
    order = crud.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # 重新计算排程以获取分配数据
    order_ops = crud.get_order_operations(db, order_id)
    ops_info = []
    for oo in order_ops:
        op = db.query(models.Operation).filter(models.Operation.id == oo.operation_id).first()
        if op:
            ops_info.append({
                "name": op.name,
                "pieces_per_hour": oo.pieces_per_hour if oo.pieces_per_hour else op.default_pieces_per_hour,
            })

    def capacity_lookup_per_op(op_name, dt):
        matched = next((o for o in ops_info if o["name"] == op_name), None)
        if matched and matched.get("pieces_per_hour"):
            return matched["pieces_per_hour"]
        shift = get_shift_for_hour(dt)
        cap = crud.get_capacity_by_shift(db, shift.value if hasattr(shift, "value") else shift)
        return cap.pieces_per_hour if cap else 0

    now = datetime.utcnow()
    start = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

    # 计算投入量
    if order.estimated_yield and order.estimated_yield > 0:
        required_input = int(math.ceil(order.quantity / (order.estimated_yield / 100.0)))
    else:
        required_input = order.quantity

    sched = schedule_order_operations(start, order.due_datetime, order.length, order.width, required_input, ops_info, capacity_lookup_per_op)

    # 创建CSV数据
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["开始时间", "结束时间", "班次", "工序", "分配数量"])
    
    for (s, e, shift, op_name, alloc) in sched["allocations"]:
        writer.writerow([
            s.strftime('%Y-%m-%d %H:%M'),
            e.strftime('%Y-%m-%d %H:%M'),
            shift.value if hasattr(shift, "value") else str(shift),
            op_name,
            alloc
        ])
    
    # 转换为字节流
    output.seek(0)
    content = output.getvalue().encode('utf-8-sig')  # 使用BOM确保Excel能正确识别UTF-8
    output.close()
    
    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=order_{order_id}_schedule.csv"
        }
    )


@app.delete("/ui/orders/{order_id}")
def delete_order_ui(order_id: int, request: Request, db: Session = Depends(get_db)):
    """处理订单删除请求"""
    if not app_auth.is_admin(request):
        return RedirectResponse(url="/ui/login", status_code=303)
    
    success = crud.delete_order(db, order_id)
    if not success:
        # 如果订单不存在，返回错误信息
        return templates.TemplateResponse("order_list.html", {
            "request": request,
            "orders": crud.list_orders(db),
            "error": "订单不存在",
            "is_admin": True
        })
    
    # 删除成功后重定向到订单列表
    return RedirectResponse(url="/ui/orders", status_code=303)
