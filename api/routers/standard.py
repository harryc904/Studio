from fastapi import APIRouter, HTTPException
from api.schemas.standard import Standard
from api.services.standard_service import is_standard_id_exists, insert_standard_data

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
