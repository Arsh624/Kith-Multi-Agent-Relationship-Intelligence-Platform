from typing import Optional

from pydantic import BaseModel


class PersonCreate(BaseModel):
    name: str
    company: Optional[str] = None
