from typing import Optional

from pydantic import BaseModel


class PasteRequest(BaseModel):
    source: str
    text: str


class CompanyOut(BaseModel):
    id: str
    name: str


class PersonOut(BaseModel):
    id: str
    name: str
    title: Optional[str] = None
    company: Optional[str] = None
    note: Optional[str] = None


class PasteResponse(BaseModel):
    message_id: str
    companies: list[CompanyOut]
    people: list[PersonOut]
