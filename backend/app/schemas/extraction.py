from typing import Optional

from pydantic import BaseModel


class ExtractedCompany(BaseModel):
    name: str


class ExtractedPerson(BaseModel):
    name: str
    title: Optional[str] = None
    company: Optional[str] = None
    note: Optional[str] = None


class ExtractedRelationship(BaseModel):
    from_person: str
    to_person: str
    relation_type: str = "knows"
    note: Optional[str] = None


class ExtractionResult(BaseModel):
    companies: list[ExtractedCompany] = []
    people: list[ExtractedPerson] = []
    relationships: list[ExtractedRelationship] = []
