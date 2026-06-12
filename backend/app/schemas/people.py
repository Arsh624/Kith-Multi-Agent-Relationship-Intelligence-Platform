from typing import Optional

from pydantic import BaseModel


class PersonCreate(BaseModel):
    name: str
    company: Optional[str] = None
    known_through: Optional[str] = None


class PersonDetail(BaseModel):
    id: str
    name: str
    title: Optional[str] = None
    company: Optional[str] = None
    note: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None


class PersonPatch(BaseModel):
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
