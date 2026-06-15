from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.task import Task

_PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


def create_task(
    db: Session,
    user_id: str,
    title: str,
    deadline: Optional[date],
    priority: str = "medium",
) -> Task:
    task = Task(
        user_id=user_id,
        title=title,
        deadline=deadline,
        priority=priority or "medium",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def list_tasks(db: Session, user_id: str) -> list[Task]:
    tasks = db.scalars(select(Task).where(Task.user_id == user_id)).all()
    return sorted(
        tasks,
        key=lambda t: (
            t.done,
            _PRIORITY_RANK.get(t.priority, 1),
            t.deadline is None,
            t.deadline or date.max,
            t.created_at,
        ),
    )


def set_task_done(
    db: Session, user_id: str, task_id: str, done: bool
) -> Optional[Task]:
    task = db.scalar(
        select(Task).where(Task.id == task_id, Task.user_id == user_id)
    )
    if task is None:
        return None
    task.done = done
    db.commit()
    db.refresh(task)
    return task


def update_task(
    db: Session, user_id: str, task_id: str, fields: dict
) -> Optional[Task]:
    task = db.scalar(
        select(Task).where(Task.id == task_id, Task.user_id == user_id)
    )
    if task is None:
        return None
    if "title" in fields and fields["title"] is not None:
        title = fields["title"].strip()
        if title:
            task.title = title
    if "priority" in fields and fields["priority"]:
        task.priority = fields["priority"]
    if "deadline" in fields:
        task.deadline = fields["deadline"]
    if "done" in fields and fields["done"] is not None:
        task.done = fields["done"]
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, user_id: str, task_id: str) -> bool:
    task = db.scalar(
        select(Task).where(Task.id == task_id, Task.user_id == user_id)
    )
    if task is None:
        return False
    db.delete(task)
    db.commit()
    return True
