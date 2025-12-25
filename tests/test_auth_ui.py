from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal, Base, engine
from app import crud
from app import auth as app_auth
import pytest

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    # Ensure tables exist and capacities/ops seeded for UI
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    caps = crud.list_capacities(db)
    if not caps:
        crud.create_capacity(db, type('C',(object,),{'shift':'day','pieces_per_hour':100,'description':'day'}))
        crud.create_capacity(db, type('C',(object,),{'shift':'night','pieces_per_hour':60,'description':'night'}))
    ops = crud.list_operations(db)
    if not ops:
        crud.create_operation(db, '点胶')
        crud.create_operation(db, '切割')
    # ensure admin exists
    admin = crud.get_admin_by_username(db, '0210042432')
    if not admin:
        crud.create_admin(db, '0210042432', 'Cao99063010', name='Administrator')
    db.close()


@pytest.mark.skipif(not app_auth.SESSIONS_AVAILABLE, reason="sessions not available in this environment")
def test_login_page_renders():
    r = client.get('/ui/login')
    assert r.status_code == 200
    assert '管理员登录' in r.text


@pytest.mark.skipif(not app_auth.SESSIONS_AVAILABLE, reason="sessions not available in this environment")
def test_login_fails_with_wrong_credentials():
    r = client.post('/ui/login', data={'username': 'nope', 'password': 'bad'})
    # Should render login page with 401 status
    assert r.status_code == 401
    assert '用户名或密码错误' in r.text


@pytest.mark.skipif(not app_auth.SESSIONS_AVAILABLE, reason="sessions not available in this environment")
def test_login_success_and_redirects_and_sets_cookie():
    r = client.post('/ui/login', data={'username': '0210042432', 'password': 'Cao99063010'})
    # TestClient follows redirects by default; after successful login we should end up at the order creation page
    assert r.status_code == 200
    assert '创建订单' in r.text
    # session cookie should be present in the client's cookie jar
    assert 'session' in client.cookies


@pytest.mark.skipif(not app_auth.SESSIONS_AVAILABLE, reason="sessions not available in this environment")
def test_protected_page_requires_login_then_allows_after_login():
    # ensure we start logged out
    client.cookies.clear()

    # without login should render login page (redirect followed)
    r = client.get('/ui/orders/create')
    assert r.status_code == 200
    assert '管理员登录' in r.text

    # login
    client.post('/ui/login', data={'username': '0210042432', 'password': 'Cao99063010'})

    # now should be allowed
    r2 = client.get('/ui/orders/create')
    assert r2.status_code == 200
    assert '创建订单' in r2.text


@pytest.mark.skipif(not app_auth.SESSIONS_AVAILABLE, reason="sessions not available in this environment")
def test_logout_clears_session_and_redirects():
    # login first
    client.post('/ui/login', data={'username': '0210042432', 'password': 'Cao99063010'})
    # ensure access
    r = client.get('/ui/orders/create')
    assert r.status_code == 200

    # logout (TestClient follows redirect to login page)
    r2 = client.get('/ui/logout')
    assert r2.status_code == 200
    assert '管理员登录' in r2.text

    # after logout, accessing protected page returns login page again
    r3 = client.get('/ui/orders/create')
    assert r3.status_code == 200
    assert '管理员登录' in r3.text
