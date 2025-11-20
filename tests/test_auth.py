def test_register_and_login(client):
    # Register
    r = client.post("/auth/register", json={"username": "user1", "password": "pass1"})
    assert r.status_code == 200, r.text
    # Duplicate register should fail
    r_dup = client.post("/auth/register", json={"username": "user1", "password": "pass1"})
    assert r_dup.status_code == 400

    # Login
    r_login = client.post("/auth/login", data={"username": "user1", "password": "pass1"})
    assert r_login.status_code == 200, r_login.text
    token = r_login.json().get("access_token")
    assert token and isinstance(token, str)
