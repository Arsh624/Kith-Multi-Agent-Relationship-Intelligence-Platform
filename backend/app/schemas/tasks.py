from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TaskCreate(BaseModel):
    title: str
    deadline: Optional[date] = None
    priority: str = "medium"


class TaskUpdate(BaseModel):
    done: bool


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    deadline: Optional[date] = None
    priority: str
    done: bool
    created_at: datetime
