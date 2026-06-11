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


def test_me_returns_current_user_with_valid_token(client):
    register = client.post(
        "/auth/register",
        json={"email": "a@example.com", "password": "hunter2"},
    )
    token = register.json()["access_token"]
    response = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "a@example.com"


def test_me_rejects_missing_token(client):
    response = client.get("/auth/me")
    assert response.status_code in (401, 403)


def test_me_rejects_invalid_token(client):
    response = client.get(
        "/auth/me", headers={"Authorization": "Bearer garbage"}
    )
    assert response.status_code == 401
