"""Integration tests for API endpoints."""


def test_health_check(client):
    """Test the health check endpoint."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "configured" in data
    assert "llm_provider" in data


def test_home_page(client):
    """Test that the home page loads."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "农业" in resp.text or "report" in resp.text.lower()


def test_history_page(client):
    """Test that the history page loads."""
    resp = client.get("/history")
    assert resp.status_code == 200


def test_reports_list(client):
    """Test the reports API list."""
    resp = client.get("/api/reports")
    assert resp.status_code == 200
    data = resp.json()
    assert "reports" in data
    assert isinstance(data["reports"], list)


def test_report_not_found(client):
    """Test requesting a non-existent report."""
    resp = client.get("/api/reports/nonexistent123")
    assert resp.status_code == 404


def test_docs_page(client):
    """Test the Swagger docs page loads."""
    resp = client.get("/docs")
    assert resp.status_code == 200


def test_research_validation(client):
    """Test that empty query is rejected."""
    resp = client.post("/api/research", json={"query": ""})
    assert resp.status_code == 422  # Validation error


def test_openapi_schema(client):
    """Test the OpenAPI schema is generated."""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "paths" in schema
    assert "/api/health" in schema["paths"]
    assert "/api/research" in schema["paths"]
