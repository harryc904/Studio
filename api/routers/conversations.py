from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime
import uuid

from api.schemas.conversation import ConversationCreateRequest, ConversationResponse, ConversationUpdateRequest, PrdResponse
from api.schemas.user import UserInDB
from api.services.auth_service import get_current_user
from api.services.conversation_service import create_conversation_service, get_conversations_service, get_session_conversations_service, update_conversation_service
from api.utils.logger import get_logger

logger = get_logger(__name__)


router = APIRouter(prefix="/conversations", tags=["对话管理"])

# 创建对话接口
@router.post("", response_model=ConversationResponse)
async def create_conversation(request: ConversationCreateRequest, current_user: UserInDB = Depends(get_current_user)):
    logger.info(f"Creating a conversation for session_id: {request.session_id} by user_id: {current_user.user_id}")
    
    # 验证请求中的 user_id 是否与当前登录的用户一致
    if current_user.user_id != request.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User ID does not match the authenticated user's ID"
        )
    
    # 调用服务层创建对话
    try:
        conversation = await create_conversation_service(request, current_user)
        return conversation
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# 查询对话接口
@router.get("/conversations/{session_id}", response_model=List[ConversationResponse])
async def get_conversations(
    session_id: int,
    user_id: int,
    conversation_id: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_user)
):
    logger.info("User %s is querying conversations for session_id: %s", user_id, session_id)
    return await get_conversations_service(session_id, user_id, conversation_id, current_user)