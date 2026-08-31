import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_evaluate_valid():
    resp = client.post("/evaluate", json={"expression": "2+2"})
    assert resp.status_code == 200
    assert resp.json()["result"] == 4.0

def test_evaluate_division():
    resp = client.post("/evaluate", json={"expression": "10/2"})
    assert resp.status_code == 200
    assert resp.json()["result"] == 5.0

def test_evaluate_invalid_syntax():
    resp = client.post("/evaluate", json={"expression": "2++2"})
    assert resp.status_code == 400

def test_evaluate_unsafe():
    resp = client.post("/evaluate", json={"expression": "__import__('os')"})
    assert resp.status_code == 400

def test_validate_valid():
    resp = client.post("/validate", json={"state": 5, "action": "+"})
    assert resp.status_code == 200
    assert resp.json()["valid"] is True

def test_validate_division_by_zero():
    resp = client.post("/validate", json={"state": 0, "action": "/"})
    assert resp.status_code == 200
    assert resp.json()["valid"] is False
    assert "Division by zero" in resp.json()["reason"]

def test_validate_invalid_action():
    resp = client.post("/validate", json={"state": 0, "action": "%"})
    assert resp.status_code == 200
    assert resp.json()["valid"] is False
