from fastapi import APIRouter
from typing import List
from api.schemas.usecase import UseCase
from api.services.usecase_service import get_all_ucus, get_details

router = APIRouter()

@router.get("/ucus/", response_model=List[UseCase])
async def get_all_ucus_endpoint():
    return get_all_ucus()

@router.get("/get_details", response_model=dict)
async def get_details_endpoint(id: str, uuid: str):
    return await get_details(id, uuid)
