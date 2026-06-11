def test_register_returns_token(client):
    response = client.post(
        "/auth/register",
        json={"email": "a@example.com", "password": "hunter2"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 0


def test_register_duplicate_email_fails(client):
    client.post(
        "/auth/register",
        json={"email": "a@example.com", "password": "hunter2"},
    )
    response = client.post(
        "/auth/register",
        json={"email": "a@example.com", "password": "other"},
    )
    assert response.status_code == 400


def test_login_succeeds_with_correct_password(client):
    client.post(
        "/auth/register",
        json={"email": "a@example.com", "password": "hunter2"},
    )
    response = client.post(
        "/auth/login",
        json={"email": "a@example.com", "password": "hunter2"},
    )
    assert response.status_code == 200
    assert len(response.json()["access_token"]) > 0


def test_login_fails_with_wrong_password(client):
    client.post(
        "/auth/register",
        json={"email": "a@example.com", "password": "hunter2"},
    )
    response = client.post(
        "/auth/login",
        json={"email": "a@example.com", "password": "nope"},
    )
    assert response.status_code == 401
