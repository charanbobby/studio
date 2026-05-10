import os
import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from helper_service.auth import require_helper_key

@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("HELPER_AUTH_KEY", "test-key")
    app = FastAPI()
    @app.get("/secret", dependencies=[Depends(require_helper_key)])
    def secret(): return {"ok": True}
    return TestClient(app)

def test_missing_header_returns_401(app):
    r = app.get("/secret")
    assert r.status_code == 401

def test_wrong_key_returns_401(app):
    r = app.get("/secret", headers={"X-Helper-Key": "nope"})
    assert r.status_code == 401

def test_correct_key_returns_200(app):
    r = app.get("/secret", headers={"X-Helper-Key": "test-key"})
    assert r.status_code == 200
