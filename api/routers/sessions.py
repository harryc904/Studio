from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from typing import List

from api.schemas.session import SessionCreateRequest, SessionResponse, UpdateSessionNameRequest
from api.schemas.user import UserInDB
from api.services.auth_service import get_current_user
from api.services.session_service import create_session_service, get_user_sessions_service, update_session_name_service
from api.config import logger

router = APIRouter(prefix="/sessions", tags=["会话管理"])

# 创建会话接口
@router.post("", response_model=SessionResponse)
async def create_session(request: SessionCreateRequest, current_user: UserInDB = Depends(get_current_user)):
    logger.info(f"Creating a session for user_id: {request.user_id}")
    
    # 验证请求中的 user_id 是否与当前登录的用户一致
    if current_user.user_id != request.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User ID does not match the authenticated user's ID"
        )
    
    # 调用服务层创建会话
    try:
        session = await create_session_service(request)
        return session
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# 获取用户所有会话接口
@router.get("/user/{user_id}", response_model=List[SessionResponse])
async def get_user_sessions(user_id: int, current_user: UserInDB = Depends(get_current_user)):
    # 验证请求的用户ID是否与当前登录用户一致
    if current_user.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User ID does not match the authenticated user's ID"
        )
    
    # 调用服务层获取用户会话
    try:
        sessions = await get_user_sessions_service(user_id)
        return sessions
    except Exception as e:
        logger.error(f"Error fetching sessions for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# 更新会话名称接口
@router.put("/name", response_model=SessionResponse)
async def update_session_name(request: UpdateSessionNameRequest, current_user: UserInDB = Depends(get_current_user)):
    # 验证请求的用户ID是否与当前登录用户一致
    if current_user.user_id != request.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User ID does not match the authenticated user's ID"
        )
    
    # 调用服务层更新会话名称
    try:
        updated_session = await update_session_name_service(request)
        return updated_session
    except Exception as e:
        logger.error(f"Error updating session name: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")