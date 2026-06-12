from typing import Optional

from pydantic import BaseModel


class ExtractedCompany(BaseModel):
    name: str


class ExtractedPerson(BaseModel):
    name: str
    title: Optional[str] = None
    company: Optional[str] = None
    note: Optional[str] = None


class ExtractionResult(BaseModel):
    companies: list[ExtractedCompany] = []
    people: list[ExtractedPerson] = []
