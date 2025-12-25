# Plan — FastAPI + MySQL Example

Quick scaffold for a Python web app using FastAPI and MySQL (SQLAlchemy).

Setup

1. Create a virtualenv and activate it.
2. Copy `.env.example` to `.env` and edit MySQL credentials.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

Run

```bash
python main.py
# or
uvicorn app.main:app --reload
```

API

- POST /users/ — create user (json: {"email":"...","name":"..."})
- GET  /users/{id} — read user

Notes

- This scaffold uses `models.Base.metadata.create_all()` for quick start. Use Alembic for production migrations.
- Configure `.env` with your MySQL credentials.

**Quick local testing** ✅

- Start the app (it will not crash if DB is unavailable):

```bash
uvicorn app.main:app --reload
```

- Smoke test:

```bash
# root should respond 200
curl -sS http://127.0.0.1:8000/
# db health will return 200 when DB credentials and server are correct
curl -sS http://127.0.0.1:8000/health/db
```
## Development & Tests

Install development/test dependencies and run tests locally:

```bash
# install runtime deps (includes passlib for password hashing used by admin login)
python3 -m pip install -r requirements.txt

# install dev/test deps
python3 -m pip install -r dev-requirements.txt

# run test suite
pytest -q
```

Admin setup & login

```bash
# create DB + user (if you haven't already)
./scripts/init_local_mysql.sh
# seed default capacities, operations AND admin user
python3 scripts/seed_scheduler.py

# install runtime deps (ensure 'itsdangerous' and passlib are installed)
python3 -m pip install -r requirements.txt

# start the app
uvicorn app.main:app --reload

# visit the login UI in your browser:
http://127.0.0.1:8000/ui/login
# credentials (seeded):
# username: 0210042432
# password: Cao99063010
```

Troubleshooting

- If you see an error mentioning `ModuleNotFoundError: No module named 'itsdangerous'`, install it directly and restart the app:

```bash
python3 -m pip install itsdangerous
```
If your environment can't reach PyPI, refer to the troubleshooting section above (mirrors / trusted-host). You can also run a single test file directly with `pytest tests/test_ui_placeholders.py -q`.
**Use a local MySQL (recommended, no Docker)**

If you already have MySQL installed and running locally, use the following steps to create a database and a user for development.

macOS (Homebrew):

```bash
# install if missing
brew install mysql
# start the service
brew services start mysql
# or run manually
mysql.server start
```

Ubuntu / Debian:

```bash
sudo apt update
sudo apt install mysql-server
sudo systemctl start mysql
```

Create database and user (adjust username/password as needed):

```bash
# run as root (you may be prompted for your root password)
mysql -u root -p <<'SQL'
CREATE DATABASE IF NOT EXISTS plan_db;
CREATE USER IF NOT EXISTS 'plan'@'localhost' IDENTIFIED WITH mysql_native_password BY 'changeme';
GRANT ALL PRIVILEGES ON plan_db.* TO 'plan'@'localhost';
FLUSH PRIVILEGES;
SQL
```

If you prefer the user to be reachable from other hosts on your LAN, replace `'localhost'` with `'%'` and ensure your MySQL server is configured to listen on the interface.

There is also a convenience script included to create the DB and user from the command line:

```bash
# run (unix permissions required):
./scripts/init_local_mysql.sh
```

**Notes & troubleshooting**

- Update `.env` (or `DATABASE_URL`) with the MySQL credentials you created (e.g. `MYSQL_USER=plan`, `MYSQL_PASSWORD=changeme`, `MYSQL_DB=plan_db`, `MYSQL_HOST=127.0.0.1`).
- If you see auth plugin errors referencing `sha256_password` or `caching_sha2_password`, prefer `mysql_native_password` for the dev user or install `cryptography` in your environment (already listed in `requirements.txt`).
- The app uses `models.Base.metadata.create_all()` for quick local startup; consider using Alembic for production migrations.

Update `.env` (or use `DATABASE_URL`) with the correct credentials to let the app create tables and operate normally.

**MySQL auth note:** If you see an error mentioning `sha256_password` or `caching_sha2_password`, install `cryptography` and/or use `mysql_native_password` for local dev. The required package is already in `requirements.txt`.

---

## Additional developer notes (中文)

- 如果你在本地使用默认的 SQLite (`sqlite:///./dev.db`)，当模型发生改变时，已有的 `dev.db` 可能不包含新字段。为避免测试或本地运行时出现 "table has no column" 的错误，可以运行：

```bash
# 删除并重新创建表（开发 / 测试用途）
python -c "from app.db import engine, Base; Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine)"
```

- 推荐在生产中使用 Alembic 来管理数据库迁移（避免手动 drop/create）。

### 使用 Alembic（快速入门）

项目包含一个最小的 Alembic scaffold，配置文件位于 `alembic.ini`，迁移环境位于 `alembic/env.py`，并使用 `app.config.settings.database_url` 与 `app.db.Base.metadata`。

常用命令：

```bash
# 安装开发依赖（包括 alembic）
python3 -m pip install -r dev-requirements.txt

# 生成自动化迁移（第一次运行会创建初始 schema）
alembic revision --autogenerate -m "initial schema"

# 应用迁移
alembic upgrade head
```

请在 CI 或发布流程中将生成的迁移文件（`alembic/versions/*.py`）提交到仓库，并在部署时运行 `alembic upgrade head`。

- 常用脚本：

  - `./scripts/init_local_mysql.sh`：创建开发用的 MySQL 数据库与用户（支持 `--root-pw`, `--user`, `--password`, `--db` 等参数）。
  - `python3 scripts/seed_scheduler.py --admin`：初始化 Capacities、Operations，并可创建管理员账号（默认用户名 `0210042432`，密码 `Cao99063010`，可用 `--username/--password` 覆盖）。
  - `python3 scripts/manage_admin.py --username <name> --password <pw>`：创建或重置管理员密码。

- 测试说明：
  - 项目附带 pytest 测试套件：`pytest -q`。
  - 测试环境会在每个测试前清空并重建表以确保架构与模型一致（见 `tests/conftest.py`）。

---

If you'd like, I can add an `alembic/` scaffold and a short migration README section as a follow-up.
# plan
