from pydantic import BaseModel
from typing import List

class Note(BaseModel):
    ID: int
    content: str

class Term(BaseModel):
    termID: int
    term: str
    termEnglish: str
    definition: str
    notes: List[Note]

class Standard(BaseModel):
    standardID: str
    documentName: str
    documentNameEnglish: str
    scope: str
    terms: List[Term]
