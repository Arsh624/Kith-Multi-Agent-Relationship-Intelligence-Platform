from app.security import hash_password, verify_password


def test_hash_password_is_not_plaintext():
    hashed = hash_password("hunter2")
    assert hashed != "hunter2"
    assert len(hashed) > 0


def test_verify_password_accepts_correct_and_rejects_wrong():
    hashed = hash_password("hunter2")
    assert verify_password("hunter2", hashed) is True
    assert verify_password("wrong", hashed) is False
