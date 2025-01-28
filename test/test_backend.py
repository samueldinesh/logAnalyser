import io
from fastapi.testclient import TestClient
from backend import app  # Replace 'main' with your app's module name


# Mock valid log file content
valid_log_file = io.BytesIO (b"""
[2025-01-19 10:00:00] ERROR 404: Resource not found
[2025-01-19 10:05:00] ERROR 500: Internal server error
[2025-01-19 10:10:00] INFO: System running normally
""")

# Mock invalid file content
empty_log_file = io.BytesIO (b"")

def test_basic_analysis():
    client = TestClient(app)
    response = client.post(
        "/basic-analysis/",
        files={"file": ("test.log", valid_log_file, "text/plain")},
    )
    assert response.status_code == 200
    assert "Error Summary" in response.json()
    assert len(response.json()["Error Summary"]) > 0

def test_summarize_log():
    client = TestClient(app)
    response = client.post(
        "/summarize-log/",
        files={"file": ("test.log", valid_log_file, "text/plain")},
    )
    assert response.status_code == 200
    assert "summary" in response.json()
    assert len(response.json()["summary"]) > 0

def test_query_log():
    client = TestClient(app)
    query = "What is the most common error?"
    response = client.post(
        "/query-log/",
        files={"file": ("test.log", valid_log_file, "text/plain")},
        params={"query": query},
    )
    assert response.status_code == 200
    assert "response" in response.json()
    assert len(response.json()["response"]) > 0

def test_download_error_summary():
    client = TestClient(app)
    response = client.post(
        "/download-error-summary/",
        files={"file": ("test.log", valid_log_file, "text/plain")},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv"

def test_empty_file():
    client = TestClient(app)
    response = client.post(
        "/basic-analysis/",
        files={"file": ("empty.log", empty_log_file, "text/plain")},
    )
    assert response.status_code == 400
    assert "File is empty" in response.json()["detail"]
