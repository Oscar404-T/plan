#!/usr/bin/env python3
"""Seed sample capacities for day/night.

This script is runnable directly (python scripts/seed_scheduler.py) and also import-safe.
If you see `ModuleNotFoundError: No module named 'app'`, run from the project root or set PYTHONPATH=. before running.
"""
import sys
from pathlib import Path

# Ensure project root is on sys.path when running the script directly
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import SessionLocal, Base, engine
from app import crud


import argparse


def main():
    parser = argparse.ArgumentParser(description='Seed capacities, default operations, and optionally an admin account.')
    parser.add_argument('--no-caps', action='store_true', help='Skip seeding capacities')
    parser.add_argument('--no-ops', action='store_true', help='Skip seeding default operations')
    parser.add_argument('--admin', action='store_true', help='Create admin user with provided --username/--password')
    parser.add_argument('--username', default='0210042432', help='Admin username to create')
    parser.add_argument('--password', default='Cao99063010', help='Admin password to set')
    args = parser.parse_args()

    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        print("Warning: could not create tables on startup:", exc)

    try:
        with SessionLocal() as db:
            # if capacities exist, skip (unless --no-caps set)
            if not args.no_caps:
                caps = crud.list_capacities(db)
                if caps:
                    print("Capacities already seeded")
                else:
                    print("Seeding capacities: day=100 pieces/hr, night=60 pieces/hr")
                    crud.create_capacity(db, type('C',(object,),{'shift':'day','pieces_per_hour':100,'description':'Day shift default'}) )
                    crud.create_capacity(db, type('C',(object,),{'shift':'night','pieces_per_hour':60,'description':'Night shift default'}) )
                    print("Done")

            # seed default operations if none exist (unless --no-ops)
            if not args.no_ops:
                ops = crud.list_operations(db)
                if ops:
                    print("Operations already seeded")
                else:
                    default_ops = [
                        "点胶",
                        "切割",
                        "边抛",
                        "边强",
                        "分片",
                        "酸洗",
                        "钢化",
                        "面强",
                        "AOI",
                        "包装",
                    ]
                    print("Seeding default operations")
                    for name in default_ops:
                        crud.create_operation(db, name)
                    print("Done seeding operations")

            # optionally ensure admin user exists / create or update
            if args.admin:
                admin = crud.get_admin_by_username(db, args.username)
                if admin:
                    print(f'Admin user {args.username} already exists; updating password')
                    # reuse manage_admin behavior by updating via CRUD
                    admin.hashed_password = __import__('app.security', fromlist=['get_password_hash']).get_password_hash(args.password)
                    admin.name = 'Administrator'
                    db.add(admin)
                    db.commit()
                    print('Admin password updated')
                else:
                    print(f'Creating admin user {args.username}')
                    crud.create_admin(db, args.username, args.password, name='Administrator')
                    print('Admin user created')

    except Exception as exc:
        print('Error while seeding data:', exc)


if __name__ == '__main__':
    main()
