from fastapi.testclient import TestClient

from tracking_to_event.web import create_app


def test_index_page_renders():
    client = TestClient(create_app(data_dir="data"))
    response = client.get("/")

    assert response.status_code == 200
    assert "Tracking To Event Studio" in response.text
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
