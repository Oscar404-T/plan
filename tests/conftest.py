import os
import sys
from pathlib import Path
import pytest

# Ensure project root is on sys.path so tests can import 'app' package
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Ensure tests run against a clean DB schema for each test to avoid stale sqlite schema issues
from app.db import Base, engine

@pytest.fixture(autouse=True)
def reset_db():
    # Drop all and re-create so the test DB matches the current models exactly
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
