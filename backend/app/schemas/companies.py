from typing import Optional

from pydantic import BaseModel


class CompanyPatch(BaseModel):
    color: Optional[str] = None


class CompanyOut(BaseModel):
    id: str
    name: str
    color: Optional[str] = None
