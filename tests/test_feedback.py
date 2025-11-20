def test_feedback_storage_and_length_limit(client):
    # Register + login
    client.post("/auth/register", json={"username": "fbuser", "password": "fbpass"})
    r_login = client.post("/auth/login", data={"username": "fbuser", "password": "fbpass"})
    token = r_login.json()["access_token"]

    # Valid feedback
    r_ok = client.post("/feedback", json={"text": "Muy bueno"}, headers={"Authorization": f"Bearer {token}"})
    assert r_ok.status_code == 200, r_ok.text

    # Over limit feedback ( >5000 chars )
    too_long = "a" * 6000
    r_long = client.post("/feedback", json={"text": too_long}, headers={"Authorization": f"Bearer {token}"})
    # Pydantic validation error -> 422
    assert r_long.status_code == 422


def test_feedback_xss_sanitization(client):
    # Intentar inyección de script
    dangerous = "<script>alert('xss')</script>"
    r = client.post("/feedback", json={"text": dangerous})
    assert r.status_code == 400
    assert "no permitido" in r.json()["detail"].lower()

    # Intentar iframe
    iframe_text = "<iframe src='evil.com'></iframe>"
    r2 = client.post("/feedback", json={"text": iframe_text})
    assert r2.status_code == 400

    # Texto seguro con HTML escapado
    safe_text = "Esto es <b>seguro</b> y válido"
    r3 = client.post("/feedback", json={"text": safe_text})
    assert r3.status_code == 200
