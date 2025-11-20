def test_rate_limit_predict(client):
    # Usa un identificador aislado para no heredar consumo previo
    headers = {"X-Rate-Key": "test-limit-1"}
    successes = 0
    last_status = None
    for i in range(12):
        r = client.post("/predict", json={"prompt": f"Hola {i}"}, headers=headers)
        last_status = r.status_code
        if r.status_code == 200:
            successes += 1
        else:
            break
    assert successes == 10  # exactamente 10 permitidas
    assert last_status == 429
