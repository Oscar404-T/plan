# Plan 排产系统

这是一个基于 FastAPI 和 MySQL 的 Python Web 应用快速脚手架，适用于构建现代化的 RESTful API 服务。系统集成了数据库操作（SQLAlchemy）、用户认证、管理后台和自动化测试能力。

## 功能特性

- 用户管理：支持创建用户 (`POST /users/`) 和查询用户 (`GET /users/{id}`)
- 数据库健康检查：`GET /health/db` 检查数据库连接状态
- 根路径可用性检测：`GET /` 返回服务运行状态
- 管理员登录界面：提供 UI 登录页面 `/ui/login`，支持密码哈希验证
- 脚本支持：支持初始化数据库、种子数据填充、管理员账号管理等运维任务
- 订单排程：支持创建订单并自动计算排产计划

## 系统架构

采用典型的分层架构（Layered Architecture），包括：

- **API 层**（`app/main.py`, `routers`）：处理 HTTP 请求路由
- **业务逻辑层**（`app/crud.py`, `app/scheduler.py`）：封装数据操作和调度逻辑
- **数据访问层**（`app/db.py`, `app/models.py`）：基于 SQLAlchemy ORM 实现持久化
- **安全层**（`app/auth.py`, `app/security.py`）：实现 JWT 认证和密码加密
- **配置层**（`app/config.py`）：使用 Pydantic Settings 管理环境变量

## 技术栈

- **Web 框架**: FastAPI
- **异步服务器**: Uvicorn
- **ORM**: SQLAlchemy
- **数据库驱动**: PyMySQL
- **环境变量管理**: python-dotenv + pydantic-settings
- **数据验证**: Pydantic
- **密码哈希**: passlib[bcrypt]
- **模板引擎**: Jinja2
- **数据库迁移**: Alembic

## 快速开始

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 复制环境配置文件：

```bash
cp .env.example .env
# 编辑 .env 中的数据库连接信息
```

3. 初始化数据库（以本地 MySQL 为例）：

```bash
./scripts/init_local_mysql.sh
python scripts/seed_scheduler.py --admin
```

4. 启动应用：

```bash
uvicorn app.main:app --reload
```

## UI界面

访问 `http://127.0.0.1:8000/ui/login` 进入管理员登录界面，登录后可以创建订单并查看排产结果。

## API文档

启动应用后，访问 `http://127.0.0.1:8000/docs` 查看交互式API文档。

## 许可证

MIT
