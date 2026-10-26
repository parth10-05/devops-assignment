import base64, json, os, sys, urllib.request, urllib.error

BASE = os.getenv("GATEWAY_URL", f"http://127.0.0.1:{os.getenv('GATEWAY_PORT', '8085')}").rstrip("/")
AUTH = base64.b64encode(f"{os.getenv('SMOKE_USER', 'smoke')}:{os.getenv('SMOKE_PASSWORD', 'smoke')}".encode()).decode()


def call(method: str, path: str, body: dict | None = None, auth: bool = True):
    req = urllib.request.Request(BASE + path, method=method)
    if auth:
        req.add_header("Authorization", f"Basic {AUTH}")
    data = json.dumps(body).encode() if body else None
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, data, timeout=30) as r:
            raw = r.read()
            try:
                return r.status, json.loads(raw)
            except Exception:
                return r.status, raw.decode(errors="replace")
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw.decode(errors="replace")


def check(step_no: int, name: str, condition: bool):
    print(f"[{step_no}] {name}: {'ok' if condition else 'FAILED'}")
    if not condition:
        sys.exit(1)


def main():
    s, b = call("GET", "/healthz", auth=False)
    check(1, "GET /healthz", s == 200)

    s, b = call("GET", "/api/labels")
    check(2, "GET /api/labels", s == 200 and len(b.get("labels", [])) == 10)

    ticket = {"subject": "Smoke", "body": "VPN cannot connect.", "source": "smoke", "dataset_label": None}
    s, b = call("POST", "/api/tickets", ticket)
    check(3, "POST /api/tickets", s == 201)
    pid = b["prediction"]["prediction_id"]

    s, b = call("GET", "/api/tickets/pending?limit=100")
    check(4, "GET /api/tickets/pending", s == 200 and isinstance(b, list))

    fb = {"prediction_id": pid, "is_correct": True, "corrected_label": None}
    s, _ = call("POST", "/feedback-api/feedback", fb)
    check(5, "POST /feedback-api/feedback", s == 201)

    s, _ = call("POST", "/feedback-api/feedback", fb)
    check(6, "repeat feedback -> 409", s == 409)

    print(f"SMOKE OK: {b['prediction']['model_version'] if isinstance(b, dict) and 'prediction' in b else 'success'}")


if __name__ == "__main__":
    main()
