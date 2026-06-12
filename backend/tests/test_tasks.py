from datetime import date

from app.models.user import User
from app.security import hash_password
from app.services.tasks import (
    create_task,
    delete_task,
    list_tasks,
    set_task_done,
)


def _make_user(db_session, email="t@example.com"):
    user = User(email=email, hashed_password=hash_password("x"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_create_task_defaults_to_medium_and_not_done(db_session):
    user = _make_user(db_session)
    task = create_task(db_session, user.id, "Call Dipunj", None, "medium")
    assert task.priority == "medium"
    assert task.done is False
    assert task.deadline is None


def test_list_orders_open_first_then_priority_then_deadline(db_session):
    user = _make_user(db_session)
    low = create_task(db_session, user.id, "low", None, "low")
    high = create_task(db_session, user.id, "high", None, "high")
    medium = create_task(db_session, user.id, "medium", None, "medium")
    done = create_task(db_session, user.id, "done", None, "high")
    set_task_done(db_session, user.id, done.id, True)

    ordered = [t.title for t in list_tasks(db_session, user.id)]
    assert ordered == ["high", "medium", "low", "done"]


def test_deadline_sorts_before_no_deadline_within_priority(db_session):
    user = _make_user(db_session)
    no_deadline = create_task(db_session, user.id, "someday", None, "medium")
    soon = create_task(db_session, user.id, "soon", date(2026, 6, 20), "medium")

    ordered = [t.title for t in list_tasks(db_session, user.id)]
    assert ordered == ["soon", "someday"]


def test_set_task_done_and_delete(db_session):
    user = _make_user(db_session)
    task = create_task(db_session, user.id, "x", None, "medium")
    updated = set_task_done(db_session, user.id, task.id, True)
    assert updated.done is True
    assert delete_task(db_session, user.id, task.id) is True
    assert delete_task(db_session, user.id, task.id) is False


def test_set_task_done_scoped_to_user(db_session):
    owner = _make_user(db_session, "owner@example.com")
    other = _make_user(db_session, "other@example.com")
    task = create_task(db_session, owner.id, "x", None, "medium")
    assert set_task_done(db_session, other.id, task.id, True) is None


def _register(client, email="te@example.com"):
    response = client.post(
        "/auth/register", json={"email": email, "password": "hunter2"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_task_endpoints_crud(client):
    headers = _register(client)

    created = client.post(
        "/tasks",
        headers=headers,
        json={"title": "Email recruiter", "priority": "high"},
    )
    assert created.status_code == 201
    task_id = created.json()["id"]
    assert created.json()["done"] is False

    listed = client.get("/tasks", headers=headers).json()
    assert any(t["id"] == task_id for t in listed)

    patched = client.patch(
        f"/tasks/{task_id}", headers=headers, json={"done": True}
    )
    assert patched.status_code == 200
    assert patched.json()["done"] is True

    removed = client.delete(f"/tasks/{task_id}", headers=headers)
    assert removed.status_code == 204
    assert client.delete(f"/tasks/{task_id}", headers=headers).status_code == 404


def test_task_create_without_deadline(client):
    headers = _register(client)
    response = client.post("/tasks", headers=headers, json={"title": "Just do it"})
    assert response.status_code == 201
    body = response.json()
    assert body["deadline"] is None
    assert body["priority"] == "medium"


def test_tasks_require_auth(client):
    assert client.get("/tasks").status_code in (401, 403)
    assert client.post("/tasks", json={"title": "x"}).status_code in (401, 403)
