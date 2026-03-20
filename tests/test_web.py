from fastapi.testclient import TestClient

from tracking_to_event.web import create_app


def test_index_page_renders():
    client = TestClient(create_app(data_dir="data"))
    response = client.get("/")

    assert response.status_code == 200
    assert "Tracking to Event Studio" in response.text
    assert "Sample Game 1" in response.text


def test_analyze_endpoint_returns_payload():
    client = TestClient(create_app(data_dir="data"))
    response = client.get("/api/analyze", params={"gameId": 1, "startFrame": 1, "endFrame": 2500})

    assert response.status_code == 200
    payload = response.json()
    assert payload["game"]["id"] == 1
    assert payload["summary"]["eventCount"] > 0
    assert payload["validation"]["generatedEventCount"] > 0
    assert payload["events"]


def test_health_endpoint_returns_ok():
    client = TestClient(create_app(data_dir="data"))
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_security_headers_are_present():
    client = TestClient(create_app(data_dir="data"))
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "script-src 'self'" in response.headers["content-security-policy"]


def test_frames_endpoint_includes_player_numbers():
    client = TestClient(create_app(data_dir="data"))
    response = client.get("/api/frames", params={"gameId": 1, "startFrame": 1, "endFrame": 100, "sampleRate": 10})

    assert response.status_code == 200
    payload = response.json()
    assert payload["frames"]
    assert {"number", "x", "y"}.issubset(payload["frames"][0]["home"][0].keys())


def test_upload_rejects_non_csv_files():
    client = TestClient(create_app(data_dir="data"))
    response = client.post(
        "/api/upload",
        files={
            "home_file": ("home.txt", b"not,csv\n", "text/plain"),
            "away_file": ("away.csv", b"period,frame\n", "text/csv"),
        },
    )

    assert response.status_code == 400
    assert "CSV" in response.json()["detail"]
