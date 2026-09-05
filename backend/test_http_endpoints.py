import json
import time
import urllib.request

BASE_URL = "http://127.0.0.1:8000"

def test_api():
    print("Testing live REST API endpoints via HTTP...")
    email = f"http-test-{int(time.time())}@example.com"
    auth_payload = json.dumps({
        "email": email,
        "password": "secret123",
        "name": "HTTP Test"
    }).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/api/auth/register",
        data=auth_payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        auth = json.loads(resp.read().decode())
        token = auth["access_token"]
        user_id = auth["user"]["id"]

    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. GET /api/watchlist
    req = urllib.request.Request(f"{BASE_URL}/api/watchlist?user_id={user_id}", headers=headers)
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        print("[GET /api/watchlist]", data)
        assert "symbols" in data

    # 2. POST /api/watchlist/add
    payload = json.dumps({"user_id": user_id, "symbol": "SBIN"}).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/api/watchlist/add",
        data=payload,
        headers={"Content-Type": "application/json", **headers},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        print("[POST /api/watchlist/add]", data)

    # 3. POST /api/watchlist/remove
    payload = json.dumps({"user_id": user_id, "symbol": "SBIN"}).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/api/watchlist/remove",
        data=payload,
        headers={"Content-Type": "application/json", **headers},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        print("[POST /api/watchlist/remove]", data)

    # 4. POST /api/session/update
    payload = json.dumps({"user_id": user_id}).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/api/session/update",
        data=payload,
        headers={"Content-Type": "application/json", **headers},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        print("[POST /api/session/update]", data)

    # 5. GET /api/watchlist/insights
    req = urllib.request.Request(f"{BASE_URL}/api/watchlist/insights?user_id={user_id}&sort=attention", headers=headers)
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        print("[GET /api/watchlist/insights]", json.dumps(data, indent=2))
        assert "items" in data

    print("\nALL HTTP API ENDPOINTS TESTED AND VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    test_api()
