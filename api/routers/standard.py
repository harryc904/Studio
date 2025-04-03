from fastapi import APIRouter, Query, HTTPException
from typing import List
from api.schemas.standard import Standard, StandardResponse
from api.services.standard_service import is_standard_id_exists, insert_standard_data, get_standards_from_db

router = APIRouter()

@router.post("/store-standard/")
async def store_standard(standard: Standard):
    # 验证时移除输入 standard_id 的空格
    sanitized_standard_id = standard.standardID.replace(" ", "")

    # 检查 standard_id 是否已存在
    if is_standard_id_exists(sanitized_standard_id):
        # 如果存在，返回 200 状态码和提示信息
        return {"message": "Standard already exists"}

    # 插入数据（存储时保留原始 standard_id）
    try:
        insert_standard_data(standard)
        return {"message": "Standard data stored successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/standards", response_model=List[StandardResponse])
async def get_standards(terms: int = Query(..., ge=0, le=1, description="Set 0 for standards only, 1 for standards with terms")):
    # Check if terms is either 0 or 1, otherwise raise HTTPException
    if terms not in [0, 1]:
        raise HTTPException(
            status_code=422,
            detail="Invalid value for 'terms'. It must be either 0 or 1."
        )
    standards = get_standards_from_db(terms)
    return standards
