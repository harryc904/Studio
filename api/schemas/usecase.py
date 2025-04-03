from pydantic import BaseModel
from typing import List

class UserStory(BaseModel):
    id: str
    description: str

class UseCase(BaseModel):
    id: str
    name: str
    description: str
    userstories: List[UserStory]
