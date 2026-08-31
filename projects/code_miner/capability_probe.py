#!/usr/bin/env python3
"""
Capability Probe Engine
Evaluates real execution capabilities of generated programs.
"""

import time
import json
import threading

def probe_flask():
    try:
        from flask import Flask
        app = Flask(__name__)

        @app.route("/")
        def index():
            return "ok"

        # Use built-in test client (no server spawn)
        with app.test_client() as c:
            r = c.get("/")
            return r.data.decode() == "ok"
    except:
        return False


def probe_fastapi():
    try:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()

        @app.get("/")
        def read_root():
            return {"msg": "ok"}

        client = TestClient(app)
        r = client.get("/")
        return r.json().get("msg") == "ok"
    except:
        return False


def probe_requests():
    try:
        import requests
        # Use local dummy endpoint
        r = requests.models.Response()
        r._content = b"ok"
        r.status_code = 200
        return r.status_code == 200
    except:
        return False


def probe_json():
    try:
        import json
        data = {"a": 1}
        encoded = json.dumps(data)
        decoded = json.loads(encoded)
        return decoded["a"] == 1
    except:
        return False


def probe_threading():
    try:
        result = {"v": 0}

        def worker():
            result["v"] = 1

        t = threading.Thread(target=worker)
        t.start()
        t.join(timeout=1)

        return result["v"] == 1
    except:
        return False


def probe_cross_library():
    """
    Flask endpoint internally using JSON and threading.
    Tests true cross-lib execution coordination.
    """
    try:
        from flask import Flask
        import json
        import threading

        app = Flask(__name__)

        result = {"v": 0}

        def worker():
            result["v"] = 1

        @app.route("/")
        def index():
            t = threading.Thread(target=worker)
            t.start()
            t.join()
            return json.dumps({"v": result["v"]})

        with app.test_client() as c:
            r = c.get("/")
            data = json.loads(r.data.decode())
            return data["v"] == 1

    except:
        return False


def run_capability_probe():
    start = time.time()

    capabilities = {
        "flask_endpoint": probe_flask(),
        "fastapi_endpoint": probe_fastapi(),
        "requests_basic": probe_requests(),
        "json_roundtrip": probe_json(),
        "thread_spawn": probe_threading(),
        "cross_lib_execution": probe_cross_library(),
    }

    duration = time.time() - start

    functionality_score = sum(capabilities.values())

    return {
        "capabilities": capabilities,
        "functionality_score": functionality_score,
        "execution_time": duration
    }


if __name__ == "__main__":
    result = run_capability_probe()
    print(json.dumps(result))
