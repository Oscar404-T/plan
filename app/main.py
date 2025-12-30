"""FastAPI主应用入口

实现RESTful API服务，包含用户管理、产能配置、工序管理、订单管理等功能模块
- 使用依赖注入管理数据库会话
- 集成认证授权机制
- 提供API和UI两种访问方式
"""

import os
import sys
from datetime import datetime, timedelta
import json
from typing import List, Optional
import math

from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from .api.v1 import (
    users_router,
    orders_router,
    operations_router,
    capacities_router,
    workshop_capacities_router  # 新增车间产能路由
)
from .database.connection import get_db
from . import crud, models, schemas, app_auth
from .core.scheduler import get_shift_for_hour, schedule_order_operations
from .utils.helpers import calculate_max_cutting_count, calculate_layers
from .config.settings import settings

# 创建FastAPI应用实例
app = FastAPI(title="生产计划系统", version="1.0.0")

# 添加Session中间件
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="session",
    max_age=3600  # 会话有效期1小时
)

# 挂载API路由
app.include_router(users_router, prefix="/api/v1")
app.include_router(orders_router, prefix="/api/v1")
app.include_router(operations_router, prefix="/api/v1")
app.include_router(capacities_router, prefix="/api/v1")
app.include_router(workshop_capacities_router, prefix="/api/v1")  # 新增车间产能API路由

# 配置模板目录
templates = Jinja2Templates(directory="templates")

# UI路由
@app.get("/ui/login", response_class=HTMLResponse)
def login_form(request: Request):
    """渲染登录表单"""
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/ui/login", response_class=HTMLResponse)
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    """处理登录请求"""
    admin = crud.get_admin_by_username(next(get_db()), username)
    if admin and app_auth.verify_password(password, admin.hashed_password):
        # 设置会话
        request.session['admin_id'] = admin.id
        request.session['username'] = admin.username
        response = RedirectResponse(url="/ui/orders", status_code=303)
        return response
    else:
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "用户名或密码错误"}
        )


@app.get("/ui/logout")
def logout(request: Request):
    """处理登出请求"""
    app_auth.clear_admin_session(request)
    return RedirectResponse(url="/ui/login", status_code=303)


@app.get("/ui/orders", response_class=HTMLResponse)
def orders_list(request: Request, db: Session = Depends(get_db)):
    """渲染订单列表页面"""
    if not app_auth.is_admin(request):
        return RedirectResponse(url="/ui/login", status_code=303)
    
    orders = crud.list_orders(db)
    return templates.TemplateResponse(
        "order_list.html", {"request": request, "orders": orders, "is_admin": True}
    )


@app.get("/ui/orders/create")
def order_form(request: Request, db: Session = Depends(get_db)):
    """订单创建表单界面"""
    if not app_auth.is_admin(request):
        return RedirectResponse(url="/ui/login", status_code=303)
    
    # 获取所有工序用于下拉选择
    operations = crud.get_operations(db)  # 使用正确的函数名
    
    return templates.TemplateResponse("order_form.html", {
        "request": request,
        "operations": operations,
        "is_admin": True
    })


@app.post("/ui/orders/create", response_class=HTMLResponse)
async def create_order_ui(
    internal_model: str = Form(None),
    length: float = Form(...),
    width: float = Form(...),
    thickness: float = Form(None),
    original_length: float = Form(None),
    original_width: float = Form(None),
    quantity: int = Form(...),
    estimated_yield: float = Form(None),
    due_datetime: str = Form(...),
    workshop: str = Form(None),
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
            thickness=thickness,
            original_length=original_length,
            original_width=original_width,
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
            # 直接使用字符串形式的班次
            shift_str = shift.value if hasattr(shift, "value") else shift
            cap = crud.get_capacity_by_shift(db, shift_str)
            return cap.pieces_per_hour if cap else 0

        # scheduling window: start now (rounded up to next hour) until due_datetime
        now = datetime.utcnow()
        start = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        due = due_dt

        # 计算投入量（考虑估计良率：投入量 = 出货数量 / (估计良率/100)）
        if order_data.estimated_yield and order_data.estimated_yield > 0:
            required_input = int(math.ceil(order_data.quantity / (order_data.estimated_yield / 100.0)))
        else:
            required_input = order_data.quantity

        sched = schedule_order_operations(start, due, order_data.length, order_data.width, required_input, ops_info, capacity_lookup_per_op)

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

        def serialize_allocations(allocations):
            """将包含datetime对象的allocations转换为可序列化的格式"""
            serialized = []
            for alloc in allocations:
                start_time, end_time, shift_type, op_name, allocated = alloc
                serialized.append((
                    start_time.isoformat() if start_time else None,
                    end_time.isoformat() if end_time else None,
                    shift_type,
                    op_name,
                    allocated
                ))
            return serialized
        
        # 序列化排程数据
        serialized_allocations = serialize_allocations(sched["allocations"])
            
        # 格式化预计完成时间
        formatted_completion = expected_completion.isoformat() if expected_completion else None
            
        # 渲染排程结果页面
        return templates.TemplateResponse("schedule.html", {
            "request": request,
            "order": db_order,
            "allocations": serialized_allocations,
            "total_allocated": total_allocated,
            "required_input": required_input,
            "meets_due": meets_due,
            "expected_completion": formatted_completion,
            "meets_due_estimate": meets_due_estimate,
            "calculate_max_cutting_count": calculate_max_cutting_count,
            "calculate_layers": calculate_layers,
            "allocated_pct": allocated_pct,
            "remaining": remaining,
            "is_admin": True
        })
        
    except ValueError as e:
        # 处理日期时间格式错误等值错误
        error_msg = f"输入值错误: {str(e)}"
        return templates.TemplateResponse("order_form.html", {
            "request": request, 
            "operations": crud.list_operations(db),
            "error": error_msg,
            "is_admin": True
        })
    except Exception as e:
        # 处理其他可能的错误
        error_msg = f"创建订单时发生错误: {str(e)}"
        return templates.TemplateResponse("order_form.html", {
            "request": request, 
            "operations": crud.list_operations(db),
            "error": error_msg,
            "is_admin": True
        })


@app.get("/ui/orders/{order_id}/edit")
def edit_order_form(request: Request, order_id: int, db: Session = Depends(get_db)):
    """订单编辑表单界面"""
    if not app_auth.is_admin(request):
        return RedirectResponse(url="/ui/login", status_code=303)
    
    order = crud.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单未找到")
    
    # 获取所有工序用于下拉选择
    operations = crud.get_operations(db)
    
    # 获取订单相关的工序操作信息
    order_operations = crud.get_order_operations(db, order_id)
    
    return templates.TemplateResponse("order_form.html", {
        "request": request,
        "order": order,
        "operations": operations,
        "order_operations": order_operations,
        "is_admin": True
    })


@app.post("/ui/orders/{order_id}/edit")
async def update_order_ui(
    order_id: int,
    internal_model: str = Form(None),
    length: float = Form(...),
    width: float = Form(...),
    thickness: float = Form(None),
    original_length: float = Form(None),
    original_width: float = Form(None),
    quantity: int = Form(...),
    estimated_yield: float = Form(None),
    due_datetime: str = Form(...),
    workshop: str = Form(None),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """处理订单编辑请求"""
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
        
        # 创建订单更新对象
        order_data = schemas.OrderUpdate(
            internal_model=internal_model,
            length=length,
            width=width,
            thickness=thickness,
            original_length=original_length,
            original_width=original_width,
            quantity=quantity,
            estimated_yield=estimated_yield,
            due_datetime=due_dt,
            workshop=workshop,
            operations=operations if operations else None
        )
        
        # 更新订单
        updated_order = crud.update_order(db, order_id, order_data)
        if not updated_order:
            raise HTTPException(status_code=404, detail="订单未找到")
        
        # 如果有工序信息，需要更新关联的工序操作
        if operations:
            # 删除旧的订单工序记录
            old_ops = crud.get_order_operations(db, order_id)
            for op in old_ops:
                db.delete(op)
            
            # 创建新的订单工序记录
            for idx, op in enumerate(operations, start=1):
                # 查找工序ID
                operation_db = db.query(models.Operation).filter(models.Operation.name == op.operation_name).first()
                if operation_db:
                    db_op = models.OrderOperation(
                        order_id=order_id,
                        operation_id=operation_db.id,
                        seq=idx,
                        pieces_per_hour=op.pieces_per_hour
                    )
                    db.add(db_op)
            db.commit()
        
        # 重定向到订单详情页面
        return RedirectResponse(url=f"/ui/orders/{order_id}", status_code=303)
    except ValueError as e:
        # 解析日期失败等错误
        order = crud.get_order(db, order_id)
        operations = crud.get_operations(db)
        order_operations = crud.get_order_operations(db, order_id)
        
        return templates.TemplateResponse("order_form.html", {
            "request": request,
            "order": order,
            "operations": operations,
            "order_operations": order_operations,
            "error": f"输入数据有误: {str(e)}",
            "is_admin": True
        })
    except Exception as e:
        # 其他错误
        order = crud.get_order(db, order_id)
        operations = crud.get_operations(db)
        order_operations = crud.get_order_operations(db, order_id)
        
        return templates.TemplateResponse("order_form.html", {
            "request": request,
            "order": order,
            "operations": operations,
            "order_operations": order_operations,
            "error": f"更新订单失败: {str(e)}",
            "is_admin": True
        })


@app.get("/ui/orders/{order_id}", response_class=HTMLResponse)
def view_order_schedule(request: Request, order_id: int, db: Session = Depends(get_db)):
    """查看订单排程详情"""
    if not app_auth.is_admin(request):
        return RedirectResponse(url="/ui/login", status_code=303)
    
    order = crud.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单未找到")
    
    # 获取订单操作信息
    order_ops = crud.get_order_operations(db, order_id)
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
        matched = next((o for o in ops_info if o["name"] == op_name), None)
        if matched and matched.get("pieces_per_hour"):
            return matched["pieces_per_hour"]
        shift = get_shift_for_hour(dt)
        # 直接使用字符串形式的班次
        shift_str = shift.value if hasattr(shift, "value") else shift
        cap = crud.get_capacity_by_shift(db, shift_str)
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
            meets_due_estimate = expected_completion <= order.due_datetime

    def serialize_allocations(allocations):
        """将包含datetime对象的allocations转换为可序列化的格式"""
        serialized = []
        for alloc in allocations:
            start_time, end_time, shift_type, op_name, allocated = alloc
            serialized.append((
                start_time.isoformat() if start_time else None,
                end_time.isoformat() if end_time else None,
                shift_type,
                op_name,
                allocated
            ))
        return serialized

    # 序列化排程数据
    serialized_allocations = serialize_allocations(sched["allocations"])
    
    # 格式化预计完成时间
    formatted_completion = expected_completion.isoformat() if expected_completion else None
    
    # 计算分配百分比
    allocated_pct = (total_allocated / required_input * 100) if required_input > 0 else 0
    
    # 计算剩余数量
    remaining = required_input - total_allocated if not meets_due else 0

    return templates.TemplateResponse("schedule.html", {
        "request": request,
        "order": order,
        "allocations": serialized_allocations,
        "total_allocated": total_allocated,
        "required_input": required_input,
        "meets_due": meets_due,
        "expected_completion": formatted_completion,
        "meets_due_estimate": meets_due_estimate,
        "calculate_max_cutting_count": calculate_max_cutting_count,
        "calculate_layers": calculate_layers,
        "allocated_pct": allocated_pct,
        "remaining": remaining,
        "is_admin": True
    })


@app.get("/ui/orders/{order_id}/schedule")
def redirect_to_order_schedule(order_id: int, request: Request):
    """重定向旧的URL格式到新的URL格式"""
    if not app_auth.is_admin(request):
        return RedirectResponse(url="/ui/login", status_code=303)
    
    return RedirectResponse(url=f"/ui/orders/{order_id}", status_code=303)




@app.get("/ui/orders/{order_id}/csv", response_class=HTMLResponse)
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
        # 直接使用字符串形式的班次
        shift_str = shift.value if hasattr(shift, "value") else shift
        cap = crud.get_capacity_by_shift(db, shift_str)
        return cap.pieces_per_hour if cap else 0

    now = datetime.utcnow()
    start = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

    # 计算投入量
    if order.estimated_yield and order.estimated_yield > 0:
        required_input = int(math.ceil(order.quantity / (order.estimated_yield / 100.0)))
    else:
        required_input = order.quantity

    sched = schedule_order_operations(start, order.due_datetime, order.length, order.width, required_input, ops_info, capacity_lookup_per_op)

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
            meets_due_estimate = expected_completion <= order.due_datetime

    # 构建CSV内容
    csv_content = "工序,班次,开始时间,结束时间,分配数量\n"
    for alloc in sched["allocations"]:
        csv_content += f"{alloc[3]},{alloc[2]},{alloc[0].strftime('%Y-%m-%d %H:%M')},{alloc[1].strftime('%Y-%m-%d %H:%M')},{alloc[4]}\n"

    # 返回CSV响应
    from fastapi.responses import Response
    response = Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=order_{order_id}_schedule.csv"}
    )
    return response


# 产能管理相关路由
@app.get("/ui/capacities")
def capacities_list(request: Request):
    """渲染产能列表页面"""
    if not app_auth.is_admin(request):
        return RedirectResponse(url="/ui/login", status_code=303)
    
    db = next(get_db())
    try:
        # 获取所有工序和产能数据
        operations = crud.get_operations(db)
        capacities = crud.get_all_workshop_capacities(db, skip=0, limit=100)  # 使用新的CRUD函数
        
        # 使用固定的班次值，因为Shift枚举不存在
        shifts = ['day', 'night']
        
        return templates.TemplateResponse("capacity_form.html", {
            "request": request,
            "operations": operations,
            "capacities": capacities,
            "shifts": shifts,
            "is_admin": True
        })
    finally:
        db.close()


@app.post("/ui/capacities/create")
def create_capacity_ui(
    request: Request,
    workshop: str = Form(...),
    operation_id: int = Form(...),
    machine_name: str = Form(...),
    machine_count: int = Form(...),
    cycle_time: float = Form(...),
    capacity_per_hour: float = Form(...),
    db: Session = Depends(get_db)
):
    """创建产能记录的UI路由"""
    if not app_auth.is_admin(request):
        return RedirectResponse(url="/ui/login", status_code=303)
    
    try:
        # 创建产能记录
        capacity_data = schemas.WorkshopCapacityCreate(  # 使用新的Schema
            workshop=workshop,
            operation_id=operation_id,
            machine_name=machine_name,
            machine_count=machine_count,
            cycle_time=cycle_time,
            capacity_per_hour=capacity_per_hour
        )
        crud.create_workshop_capacity(db, capacity_data)  # 使用新的CRUD函数
        
        # 重定向回产能管理页面
        return RedirectResponse(url="/ui/capacities", status_code=303)
    except Exception as e:
        # 获取所有工序和产能数据
        operations = crud.get_operations(db)
        capacities = crud.get_all_workshop_capacities(db, skip=0, limit=100)  # 使用新的CRUD函数
        
        return templates.TemplateResponse("capacity_form.html", {
            "request": request,
            "operations": operations,
            "capacities": capacities,
            "error": f"创建产能记录失败: {str(e)}",
            "is_admin": True
        })


@app.post("/ui/capacities/{capacity_id}/update")
def update_capacity_ui(
    request: Request,
    capacity_id: int,
    workshop: str = Form(...),
    operation_id: int = Form(...),
    machine_name: str = Form(...),
    machine_count: int = Form(...),
    cycle_time: float = Form(...),
    capacity_per_hour: float = Form(...),
    db: Session = Depends(get_db)
):
    """更新产能记录的UI路由"""
    if not app_auth.is_admin(request):
        return RedirectResponse(url="/ui/login", status_code=303)
    
    try:
        # 更新产能记录
        capacity_data = schemas.WorkshopCapacityUpdate(
            workshop=workshop,
            operation_id=operation_id,
            machine_name=machine_name,
            machine_count=machine_count,
            cycle_time=cycle_time,
            capacity_per_hour=capacity_per_hour
        )
        updated_capacity = crud.update_workshop_capacity(db, capacity_id, capacity_data)
        if not updated_capacity:
            raise HTTPException(status_code=404, detail="产能记录未找到")
        
        # 重定向回产能管理页面
        return RedirectResponse(url="/ui/capacities", status_code=303)
    except HTTPException:
        raise
    except Exception as e:
        # 获取所有工序和产能数据
        operations = crud.get_operations(db)
        capacities = crud.get_all_workshop_capacities(db, skip=0, limit=100)
        
        return templates.TemplateResponse("capacity_form.html", {
            "request": request,
            "operations": operations,
            "capacities": capacities,
            "error": f"更新产能记录失败: {str(e)}",
            "is_admin": True
        })


@app.post("/ui/capacities/{capacity_id}/delete")
def delete_capacity_ui(
    request: Request,
    capacity_id: int,
    db: Session = Depends(get_db)
):
    """删除产能记录的UI路由"""
    if not app_auth.is_admin(request):
        return RedirectResponse(url="/ui/login", status_code=303)
    
    try:
        # 删除产能记录
        deleted_capacity = crud.delete_workshop_capacity(db, capacity_id)
        if not deleted_capacity:
            raise HTTPException(status_code=404, detail="产能记录未找到")
        
        # 重定向回产能管理页面
        return RedirectResponse(url="/ui/capacities", status_code=303)
    except HTTPException:
        raise
    except Exception as e:
        # 获取所有工序和产能数据
        operations = crud.get_operations(db)
        capacities = crud.get_all_workshop_capacities(db, skip=0, limit=100)
        
        return templates.TemplateResponse("capacity_form.html", {
            "request": request,
            "operations": operations,
            "capacities": capacities,
            "error": f"删除产能记录失败: {str(e)}",
            "is_admin": True
        })


# 此路由可能与上面的 /ui/capacities 冲突或冗余，建议删除或重命名为具体的编辑路由，例如 /ui/capacities/{id}/edit
# 这里先将其注释掉，以避免冲突。
# @app.get("/ui/capacities/edit", response_class=HTMLResponse)
# def capacity_edit_form(request: Request, db: Session = Depends(get_db)):
#     """渲染产能编辑表单"""
#     if not app_auth.is_admin(request):
#         return RedirectResponse(url="/ui/login", status_code=303)
#     
#     capacities = crud.list_capacities(db)
#     shifts = ['day', 'night']
#     return templates.TemplateResponse(
#         "capacity_edit.html",  # 假设有一个专用的编辑模板
#         {
#             "request": request, 
#             "capacities": capacities, 
#             "shifts": shifts, 
#             "is_admin": True
#         }
#     )


@app.post("/ui/capacities/update", response_class=HTMLResponse)
def update_capacity(
    request: Request,
    shift: str = Form(...),
    pieces_per_hour: int = Form(...),
    db: Session = Depends(get_db)
):
    """处理产能更新请求"""
    if not app_auth.is_admin(request):
        return RedirectResponse(url="/ui/login", status_code=303)
    
    try:
        # 更新或创建产能记录
        capacity = crud.update_capacity_by_shift(db, shift, pieces_per_hour)
        return RedirectResponse(url="/ui/capacities", status_code=303)
    except Exception as e:
        return templates.TemplateResponse(
            "capacity_form.html",
            {
                "request": request,
                "error": f"更新产能失败: {str(e)}",
                "capacities": crud.list_capacities(db),
                "shifts": ['day', 'night'],
                "is_admin": True
            }
        )


# 健康检查端点
@app.get("/health/db")
def health_check(db: Session = Depends(get_db)):
    """检查数据库连接状态"""
    try:
        # 尝试执行一个简单的查询
        db.execute("SELECT 1")
        return {"status": "healthy", "database": "reachable"}
    except Exception:
        raise HTTPException(status_code=503, detail="Database connection failed")


# 根路径 - 返回服务状态
@app.get("/")
def read_root():
    """返回服务运行状态"""
    return {"service": "Production Planning System", "status": "running"}