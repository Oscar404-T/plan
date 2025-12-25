Alembic scaffold (minimal)

Usage:

# install dev deps
python3 -m pip install -r dev-requirements.txt

# initialize alembic (skipped; scaffolded already)
# generate an autogenerate migration
alembic revision --autogenerate -m "initial schema"

# apply migrations
alembic upgrade head

Notes:
- The Alembic environment uses `app.config.settings.database_url` and `app.db.Base.metadata` as the target metadata.
- In CI / production, prefer to commit migration files and run `alembic upgrade head` during deployments.
