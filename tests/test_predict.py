def test_predict_without_token(client):
    r = client.post("/predict", json={"prompt": "Hola"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["generated_text"].startswith("OUTPUT:Hola")


def test_predict_with_token(client):
    # Register + login
    client.post("/auth/register", json={"username": "user2", "password": "pass2"})
    r_login = client.post("/auth/login", data={"username": "user2", "password": "pass2"})
    token = r_login.json()["access_token"]

    r = client.post(
        "/predict",
        json={"prompt": "Probando"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["generated_text"].startswith("OUTPUT:Probando")
