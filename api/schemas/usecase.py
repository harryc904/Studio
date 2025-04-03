from pydantic import BaseModel
from typing import List, Dict

class UserStory(BaseModel):
    id: str
    description: str

class UseCase(BaseModel):
    id: str
    name: str
    description: str
    userstories: List[UserStory]

class PRDData(BaseModel):
    chapters: List[Dict]
