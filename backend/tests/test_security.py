from app.security import hash_password, verify_password, create_access_token, decode_access_token


def test_hash_password_is_not_plaintext():
    hashed = hash_password("hunter2")
    assert hashed != "hunter2"
    assert len(hashed) > 0


def test_verify_password_accepts_correct_and_rejects_wrong():
    hashed = hash_password("hunter2")
    assert verify_password("hunter2", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_token_roundtrip_returns_subject():
    token = create_access_token("user-123")
    assert decode_access_token(token) == "user-123"


def test_decode_rejects_garbage_token():
    assert decode_access_token("not-a-real-token") is None
