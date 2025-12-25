"""应用入口与路由（中文注释）

该模块定义 FastAPI 路由，包括：健康检查、用户/容量/工序/订单的 CRUD，以及调度和 UI 页面。
注意：为保持简单，使用基于 session 的轻量登录保护订单创建 UI（依赖 Starlette 的 SessionMiddleware）。
"""

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from . import crud, models, schemas
from .db import engine, get_db, Base
from sqlalchemy.exc import SQLAlchemyError
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

app = FastAPI(title="Plan App")

# Session middleware (simple cookie-based session)
from .config import settings
secret = settings.secret_key or "change-me-in-production"

# Try to load SessionMiddleware (dependent on itsdangerous); if missing, disable session-based UI and show a helpful message
_sessions_available = True
try:
    from starlette.middleware.sessions import SessionMiddleware
    app.add_middleware(SessionMiddleware, secret_key=secret)
except Exception as exc:  # pragma: no cover - runtime environment may lack optional deps
    import logging
    logging.getLogger(__name__).warning("SessionMiddleware not available: %s. UI login will be disabled until you install 'itsdangerous'", exc)
    _sessions_available = False

from .security import verify_password as verify_password_fn
from . import crud as app_crud
from . import auth as app_auth  # 认证相关工具函数，统一放到 app/auth.py


@app.on_event("startup")
def create_tables():
    """应用启动时尝试创建表；若数据库不可用则仅记录警告而不抛出异常，方便本地开发。"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
    except SQLAlchemyError as exc:
        logger.warning("Could not create tables on startup: %s", exc)


# -------------------- 基础路由（健康检查等） --------------------
@app.get("/", tags=["meta"])
def root():
    """根路由，用于快速探活（返回 200）。"""
    return {"status": "ok"}


from fastapi.responses import JSONResponse, RedirectResponse
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
        return JSONResponse(status_code=503, content={"db": "error", "detail": str(exc)})


@app.post("/users/", response_model=schemas.UserRead)
def create_user_endpoint(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = crud.get_user_by_email(db, user.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db, user)


@app.get("/users/{user_id}", response_model=schemas.UserRead)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


# Capacity endpoints
# 产能（按班次）相关的 CRUD 接口，用于配置白班/夜班的 pieces_per_hour
@app.post("/capacities/", response_model=schemas.CapacityRead)
def create_capacity(cap: schemas.CapacityCreate, db: Session = Depends(get_db)):
    return crud.create_capacity(db, cap)


@app.get("/capacities/", response_model=list[schemas.CapacityRead])
def list_capacities(db: Session = Depends(get_db)):
    return crud.list_capacities(db)


# Operation endpoints
# 工序相关接口：用于维护可用的工序及其默认产能
@app.post("/operations/", response_model=schemas.OperationRead)
def create_operation(op: schemas.OperationCreate, db: Session = Depends(get_db)):
    return crud.create_operation(db, op.name, op.default_pieces_per_hour, op.description)


@app.get("/operations/", response_model=list[schemas.OperationRead])
def list_operations(db: Session = Depends(get_db)):
    return crud.list_operations(db)


# Order and scheduling endpoints
# 订单相关接口：创建订单并可调用调度算法计算排产（API 用法）
@app.post("/orders/", response_model=schemas.OrderRead)
def create_order_endpoint(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    db_order = crud.create_order(db, order)
    return db_order


@app.get("/orders/{order_id}", response_model=schemas.OrderRead)
def get_order_endpoint(order_id: int, db: Session = Depends(get_db)):
    db_order = crud.get_order(db, order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    return db_order


@app.post("/schedule/", response_model=schemas.ScheduleResponse)
def schedule_endpoint(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    # create order record for reference
    db_order = crud.create_order(db, order)

    # build per-order operations info
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
        shift = __import__("app.scheduler", fromlist=["get_shift_for_hour"]).get_shift_for_hour(dt)
        cap = crud.get_capacity_by_shift(db, shift.value if hasattr(shift, "value") else shift)
        return cap.pieces_per_hour if cap else 0

    # scheduling window: start now (rounded up to next hour) until due_datetime
    now = datetime.utcnow()
    start = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    due = order.due_datetime

    # 计算投入量（考虑估计良率：投入量 = 出货数量 / (估计良率/100)）
    import math
    if order.estimated_yield and order.estimated_yield > 0:
        required_input = int(math.ceil(order.quantity / (order.estimated_yield / 100.0)))
    else:
        required_input = order.quantity

    sched = __import__("app.scheduler", fromlist=["schedule_order_operations"]).schedule_order_operations(start, due, order.length, order.width, required_input, ops_info, capacity_lookup_per_op)

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
            import math
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


# CSV export endpoint
# 模板与 CSV 导出（UI 使用 Jinja 模板渲染）
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates
from fastapi import Request

templates = Jinja2Templates(directory="templates")


@app.get("/schedule/{order_id}/csv")
def schedule_csv(order_id: str, db: Session = Depends(get_db)):
    # Accept a string and try to coerce to int; return 400 for invalid placeholders (e.g., '{order_id}')
    try:
        oid = int(order_id)
    except ValueError:
        s = order_id.strip()
        if s.startswith("{") and s.endswith("}"):
            raise HTTPException(status_code=400, detail="order_id placeholder detected; replace {order_id} with a numeric id")
        raise HTTPException(status_code=400, detail="order_id must be an integer")

    db_order = crud.get_order(db, oid)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    # build per-order operations info
    order_ops = crud.get_order_operations(db, db_order.id)
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
        shift = __import__("app.scheduler", fromlist=["get_shift_for_hour"]).get_shift_for_hour(dt)
        cap = crud.get_capacity_by_shift(db, shift.value if hasattr(shift, "value") else shift)
        return cap.pieces_per_hour if cap else 0

    # Recompute schedule from now
    now = datetime.utcnow()
    start = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    due = db_order.due_datetime

    # 计算投入量（考虑估计良率：投入量 = 出货数量 / (估计良率/100)）
    import math
    req_qty = db_order.quantity
    if db_order.estimated_yield and db_order.estimated_yield > 0:
        req_qty = int(math.ceil(db_order.quantity / (db_order.estimated_yield / 100.0)))

    sched = __import__("app.scheduler", fromlist=["schedule_order_operations"]).schedule_order_operations(start, due, db_order.length, db_order.width, req_qty, ops_info, capacity_lookup_per_op)

    # Build CSV
    lines = ["start,end,shift,operation,allocated"]
    for (s, e, shift, op_name, alloc) in sched["allocations"]:
        lines.append(f"{s.isoformat()},{e.isoformat()},{shift.value if hasattr(shift, 'value') else shift},{op_name},{alloc}")
    csv_text = "\n".join(lines)

    headers = {"Content-Disposition": f"attachment; filename=order_{oid}_schedule.csv"}
    return Response(content=csv_text, media_type="text/csv", headers=headers)


# Order create UI
from fastapi import Form

# Helper: robust form parsing with fallback to urlencoded body when python-multipart is missing
async def _get_form_dict(request: Request):
    """Return a dict-like mapping of form fields to single values.
    Tries Starlette's request.form() first; if that fails with AssertionError
    (missing python-multipart), falls back to parsing the raw urlencoded body.
    """
    try:
        form = await request.form()
        return dict(form)
    except AssertionError:
        # fallback: parse body as application/x-www-form-urlencoded
        raw = await request.body()
        try:
            parsed = __import__('urllib.parse', fromlist=['parse_qs']).parse_qs(raw.decode())
        except Exception:
            return {}
        return {k: v[0] for k, v in parsed.items()}



# UI 登录页（仅用于本地轻量管理，生产建议使用更完善的认证方案）
@app.get("/ui/login")
def ui_login(request: Request):
    # 若会话不可用，提示安装 itsdangerous
    if not _sessions_available or not app_auth.SESSIONS_AVAILABLE:
        return templates.TemplateResponse("login.html", {"request": request, "error": "会话功能不可用：请安装 itsdangerous（python3 -m pip install itsdangerous）并重启应用。"})
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/ui/login")
async def ui_login_post(request: Request, db: Session = Depends(get_db)):
    # 若会话不可用，提示安装 itsdangerous
    if not _sessions_available or not app_auth.SESSIONS_AVAILABLE:
        return templates.TemplateResponse("login.html", {"request": request, "error": "会话功能不可用：请安装 python-multipart 与 itsdangerous（python3 -m pip install python-multipart itsdangerous）并重启应用。"}, status_code=503)

    form = await _get_form_dict(request)
    username = form.get('username')
    password = form.get('password')

    # 使用 app_auth 提供的统一接口进行身份验证并设置 session
    if app_auth.authenticate_and_login(request, db, username, password):
        return RedirectResponse(url='/ui/orders/create', status_code=303)

    return templates.TemplateResponse("login.html", {"request": request, "error": "用户名或密码错误"}, status_code=401)


@app.get("/ui/logout")
def ui_logout(request: Request):
    # 尝试清除会话（若可用），然后跳回登录页
    app_auth.clear_admin_session(request)
    return RedirectResponse(url='/ui/login', status_code=303)


@app.get("/ui/orders/create")
def ui_create_order(request: Request, db: Session = Depends(get_db)):
    # If sessions aren't available, show an explanatory message and hint to install itsdangerous
    if not _sessions_available:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Server is missing 'itsdangerous' (required for sessions). Run: python3 -m pip install itsdangerous and restart."}, status_code=503)

    # Require admin login
    if not app_auth.is_admin(request):
        return RedirectResponse(url='/ui/login')
    ops = crud.list_operations(db)
    return templates.TemplateResponse("order_form.html", {"request": request, "operations": ops})


@app.post("/ui/orders/create")
async def ui_create_order_post(request: Request, db: Session = Depends(get_db)):
    # If sessions aren't available, show an explanatory message and hint to install itsdangerous
    if not _sessions_available:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Server is missing 'itsdangerous' (required for sessions). Run: python3 -m pip install itsdangerous and restart."}, status_code=503)

    # Require admin login
    if not request.session.get('admin_id'):
        return RedirectResponse(url='/ui/login')

    # prepare operations (in case we need to re-render the form on error)
    ops = crud.list_operations(db)

    # read form data (robust to missing python-multipart)
    form = await _get_form_dict(request)

    internal_model = form.get('internal_model')
    length = float(form.get('length') or 0)
    width = float(form.get('width') or 0)
    # prefer submitted size (from client) but compute server-side as fallback / authoritative
    try:
        size = float(form.get('size')) if form.get('size') else None
    except Exception:
        size = None
    quantity = int(form.get('quantity'))
    estimated_yield = None
    if form.get('estimated_yield'):
        try:
            estimated_yield = float(form.get('estimated_yield'))
        except Exception:
            estimated_yield = None
    due_datetime = form.get('due_datetime')

    ops = crud.list_operations(db)
    ops_payload = []
    for op in ops:
        key = f"op_{op.id}"
        val = form.get(key)
        if val:
            try:
                pph = int(val)
            except Exception:
                pph = None
        else:
            pph = None
        ops_payload.append({"operation_name": op.name, "pieces_per_hour": pph})

    # convert local datetime-local input to ISO
    from datetime import datetime
    due_dt = datetime.fromisoformat(due_datetime)

    # create order directly via CRUD
    from types import SimpleNamespace
    db_order = crud.create_order(db, SimpleNamespace(**{
        'internal_model': internal_model,
        'length': length,
        'width': width,
        'size': size,
        'quantity': quantity,
        'estimated_yield': estimated_yield,
        'due_datetime': due_dt,
        'operations': [SimpleNamespace(**o) for o in ops_payload]
    }))

    is_admin = app_auth.is_admin(request)

    return templates.TemplateResponse("schedule.html", {"request": request, "order": db_order, "allocations": [], "is_admin": is_admin})


@app.get("/ui/orders/{order_id}")
def ui_order(order_id: str, request: Request, db: Session = Depends(get_db)):
    # Accept string ID and provide a friendly 400 if placeholder used
    try:
        oid = int(order_id)
    except ValueError:
        s = order_id.strip()
        if s.startswith("{") and s.endswith("}"):
            raise HTTPException(status_code=400, detail="order_id placeholder detected; replace {order_id} with a numeric id")
        raise HTTPException(status_code=400, detail="order_id must be an integer")

    db_order = crud.get_order(db, oid)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    def capacity_lookup(shift):
        cap = crud.get_capacity_by_shift(db, shift.value if hasattr(shift, "value") else shift)
        return cap.pieces_per_hour if cap else 0

    now = datetime.utcnow()
    start = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    due = db_order.due_datetime

    order_ops = crud.get_order_operations(db, db_order.id)
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
        shift = __import__("app.scheduler", fromlist=["get_shift_for_hour"]).get_shift_for_hour(dt)
        cap = crud.get_capacity_by_shift(db, shift.value if hasattr(shift, "value") else shift)
        return cap.pieces_per_hour if cap else 0

    # 计算投入量并用于调度
    import math
    req_qty = db_order.quantity
    if db_order.estimated_yield and db_order.estimated_yield > 0:
        req_qty = int(math.ceil(db_order.quantity / (db_order.estimated_yield / 100.0)))

    sched = __import__("app.scheduler", fromlist=["schedule_order_operations"]).schedule_order_operations(start, due, db_order.length, db_order.width, req_qty, ops_info, capacity_lookup_per_op)

    allocations = []
    for (s, e, shift, op_name, alloc) in sched["allocations"]:
        allocations.append({"start": s, "end": e, "shift": shift.value if hasattr(shift, "value") else str(shift), "operation": op_name, "allocated": alloc})

    is_admin = app_auth.is_admin(request)

    # Summary stats for UI
    total_allocated = sched.get("total_allocated", 0)
    required_input_val = req_qty
    try:
        allocated_pct = round((total_allocated / required_input_val) * 100, 2) if required_input_val > 0 else 0.0
    except Exception:
        allocated_pct = 0.0
    remaining = max(0, required_input_val - total_allocated)

    # Determine last operation name (used to compute completion times)
    last_op_name = ops_info[-1]["name"] if ops_info else None
    # find latest end time allocated for last operation
    last_op_ends = [a['end'] for a in allocations if a['operation'] == last_op_name]
    last_alloc_end = max(last_op_ends) if last_op_ends else None

    # Estimate completion if under-allocated: estimate additional hours using per-op pph if available
    expected_completion = None
    meets_due = total_allocated >= required_input_val
    meets_due_estimate = meets_due
    if not meets_due:
        remaining_qty = required_input_val - total_allocated
        # per-op pieces per hour preference
        last_op_pph = next((o.get('pieces_per_hour') for o in ops_info if o.get('name') == last_op_name), None)
        if last_op_pph and last_op_pph > 0:
            import math
            hours_needed = int(math.ceil(remaining_qty / last_op_pph))
            base = last_alloc_end if last_alloc_end else start
            expected_completion = base + timedelta(hours=hours_needed)
            meets_due_estimate = expected_completion <= due

    return templates.TemplateResponse("schedule.html", {"request": request, "order": db_order, "allocations": allocations, "is_admin": is_admin, "required_input": req_qty, "total_allocated": total_allocated, "allocated_pct": allocated_pct, "remaining": remaining, "meets_due": meets_due, "expected_completion": expected_completion, "meets_due_estimate": meets_due_estimate})
