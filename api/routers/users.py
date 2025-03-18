from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from api.schemas.user import User, UserInDB
from api.services.auth_service import get_current_user
from api.services.user_service import get_user_by_id_service, update_password_service
from api.utils.logger import get_logger
from api.schemas.auth import UpdatePasswordRequest, UpdatePasswordResponse

logger = get_logger(__name__)


router = APIRouter(prefix="/users", tags=["用户管理"])

# 获取用户信息接口
@router.get("/{user_id}", response_model=User)
async def get_user(user_id: int, current_user: UserInDB = Depends(get_current_user)):
    # 验证请求的用户ID是否与当前登录用户一致
    if current_user.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User ID does not match the authenticated user's ID"
        )
    
    # 调用服务层获取用户信息
    try:
        user = await get_user_by_id_service(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/update_password", response_model=UpdatePasswordResponse)
async def update_password(
    request: UpdatePasswordRequest,
    current_user: UserInDB = Depends(get_current_user)
):
    return await update_password_service(request, current_user)
