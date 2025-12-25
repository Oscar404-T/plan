#!/usr/bin/env python3
"""Create or reset an admin user password.

Usage:
  # create or update admin '0210042432' with the given password
  python3 scripts/manage_admin.py --username 0210042432 --password Cao99063010

This script is intentionally simple and will create DB tables if missing.
If the database is unreachable you'll see the DB errors; run ./scripts/init_local_mysql.sh first.
"""
import sys
from pathlib import Path
import argparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import SessionLocal, Base, engine
from app import crud
from app.security import get_password_hash


def main():
    parser = argparse.ArgumentParser(description='Create or reset an admin user password')
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--name", default="Administrator")
    args = parser.parse_args()

    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        print("Warning: could not create tables on startup:", exc)

    with SessionLocal() as db:
        admin = crud.get_admin_by_username(db, args.username)
        if admin:
            print(f"Updating password for existing admin: {args.username}")
            admin.hashed_password = get_password_hash(args.password)
            admin.name = args.name
            db.add(admin)
            db.commit()
            print("Password updated")
        else:
            print(f"Creating admin user: {args.username}")
            crud.create_admin(db, args.username, args.password, name=args.name)
            print("Admin created")


if __name__ == '__main__':
    main()