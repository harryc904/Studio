from fastapi import APIRouter, Depends, HTTPException
from typing import List
from api.schemas.usecase import UseCase, PRDData
from api.services.usecase_service import get_all_ucus, get_details, get_us_table_service, process_prd_data_service

router = APIRouter()

@router.get("/ucus/", response_model=List[UseCase])
async def get_all_ucus_endpoint():
    return get_all_ucus()

@router.get("/get_details", response_model=dict)
async def get_details_endpoint(id: str, uuid: str):
    return await get_details(id, uuid)

@router.get("/get_us_table", response_model=list)
async def get_us_table_endpoint(conn=Depends(get_us_table_service)):
    try:
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/achieve_data")
async def achieve_data_endpoint(data: PRDData):
    try:
        return await process_prd_data_service(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
