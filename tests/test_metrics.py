def test_metrics_endpoint(client):
    # Realiza una petición para generar métricas
    r1 = client.get("/health")
    assert r1.status_code == 200
    # Verifica header X-Request-Id
    assert r1.headers.get("X-Request-Id")
    r2 = client.get("/metrics")
    assert r2.status_code == 200
    data = r2.json()
    assert "total_requests" in data
    assert data["total_requests"] >= 2  # /health + /metrics cuentan
    assert "path_counts" in data
    assert "/health" in data["path_counts"]
    assert "/metrics" in data["path_counts"]
    assert "avg_latency_ms" in data
    assert "model_loaded" in data
    # Nuevas métricas por status
    assert "status_counts" in data
    assert 200 in map(int, data["status_counts"].keys()) or 200 in data["status_counts"]
    assert "path_status_counts" in data