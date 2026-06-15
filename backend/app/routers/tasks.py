from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.tasks import TaskCreate, TaskOut, TaskUpdate
from app.services.tasks import (
    create_task,
    delete_task,
    list_tasks,
    update_task,
)

router = APIRouter(tags=["tasks"])


@router.post("/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def add_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_task(
        db, current_user.id, payload.title, payload.deadline, payload.priority
    )


@router.get("/tasks", response_model=list[TaskOut])
def get_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_tasks(db, current_user.id)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task_endpoint(
    task_id: str,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = update_task(
        db, current_user.id, task_id, payload.model_dump(exclude_unset=True)
    )
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not delete_task(db, current_user.id, task_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    return None
