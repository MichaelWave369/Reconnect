from __future__ import annotations

import importlib.util
from pathlib import Path


MAIN_PATH = Path(__file__).resolve().parents[1] / "main.py"


def _load_main_module():
    spec = importlib.util.spec_from_file_location("reconnect_backend_main", MAIN_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_import_backend_main_does_not_run_uvicorn(monkeypatch):
    called = {"run": 0}

    def fake_run(*args, **kwargs):
        called["run"] += 1
        raise AssertionError("uvicorn.run should never execute during import")

    monkeypatch.setattr("uvicorn.run", fake_run)

    mod = _load_main_module()

    assert called["run"] == 0
    assert callable(mod.run)


def test_reload_disabled_for_streamlit(monkeypatch):
    mod = _load_main_module()

    monkeypatch.setenv("RECONNECT_RELOAD", "1")
    monkeypatch.setenv("STREAMLIT_SERVER_PORT", "8501")

    assert mod._is_reload_enabled() is False
