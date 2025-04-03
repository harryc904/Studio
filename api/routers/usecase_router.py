from fastapi import APIRouter
from typing import List
from api.schemas.usecase import UseCase
from api.services.usecase_service import get_all_ucus

router = APIRouter()

@router.get("/ucus/", response_model=List[UseCase])
async def get_all_ucus_endpoint():
    return get_all_ucus()
