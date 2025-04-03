from pydantic import BaseModel
from typing import List, Optional

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

class StandardResponse(BaseModel):
    standardID: str
    documentName: str
    documentNameEnglish: Optional[str] = None
    scope: Optional[str] = None  
    terms: Optional[List[Term]] = None
