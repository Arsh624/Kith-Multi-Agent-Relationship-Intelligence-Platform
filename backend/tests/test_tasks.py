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
