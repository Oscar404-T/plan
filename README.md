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
# plan
