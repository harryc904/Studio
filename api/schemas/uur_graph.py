from pydantic import BaseModel
from typing import List

class Node(BaseModel):
    id: str
    uuid: str
    label: str
    type: str
    name: str
    description: str
    tags: List[str]

class Edge(BaseModel):
    uuid: str
    source: str
    target: str
    type: str
    label: str
