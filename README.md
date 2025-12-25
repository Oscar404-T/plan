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

**Run a local MySQL with Docker Compose**

You can quickly run a MySQL server for local development:

```yaml
# docker-compose.yml
version: '3.8'
services:
  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: changeme
      MYSQL_DATABASE: plan_db
    ports:
      - "3306:3306"
    command: --default-authentication-plugin=mysql_native_password
```

Then bring it up:

```bash
docker compose up -d
```

**If you prefer to create a specific user**

```sql
-- connect as root and run:
CREATE USER 'plan'@'%' IDENTIFIED WITH mysql_native_password BY 'changeme';
GRANT ALL PRIVILEGES ON plan_db.* TO 'plan'@'%';
FLUSH PRIVILEGES;
```

Update `.env` (or use `DATABASE_URL`) with the correct credentials to let the app create tables and operate normally.

**MySQL auth note:** If you see an error mentioning `sha256_password` or `caching_sha2_password`, install `cryptography` and/or use `mysql_native_password` for local dev. The required package is already in `requirements.txt`.
# plan
