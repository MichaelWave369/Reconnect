from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture()
def client(tmp_path: Path):
    db_path = tmp_path / "test.db"
    upload_dir = tmp_path / "uploads"

    os.environ["RECONNECT_DB"] = str(db_path)
    os.environ["RECONNECT_UPLOAD_DIR"] = str(upload_dir)

    for module in ["app.db", "app.main"]:
        if module in sys.modules:
            importlib.reload(sys.modules[module])

    app_main = importlib.import_module("app.main")
    importlib.reload(app_main)
    app_main.init_db()

    with TestClient(app_main.app) as test_client:
        yield test_client
