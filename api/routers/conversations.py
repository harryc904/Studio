from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime
import uuid

from api.schemas.conversation import ConversationCreateRequest, ConversationResponse, ConversationUpdateRequest, PrdResponse
from api.schemas.user import UserInDB
from api.services.auth_service import get_current_user
from api.services.conversation_service import create_conversation_service, get_conversations_service, update_conversation_service, get_prd_service
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
@router.get("/{session_id}", response_model=List[ConversationResponse])
async def get_conversations(
    session_id: int,
    user_id: int,
    conversation_id: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_user)
):
    logger.info("User %s is querying conversations for session_id: %s", user_id, session_id)
    
    # 验证请求中的 user_id 是否与当前登录的用户一致
    if current_user.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User ID does not match the authenticated user's ID"
        )
    
    # 调用服务层获取对话
    try:
        conversations = await get_conversations_service(session_id, user_id, conversation_id, current_user)
        return conversations
    except Exception as e:
        logger.error(f"Error querying conversations: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# 更新会话内容接口
@router.put("/{conversation_id}")
async def update_conversation(
    conversation_id: uuid.UUID,  # 通过 URL 参数传递 conversation_id
    request: ConversationUpdateRequest,  # 请求体使用新的结构体
    current_user: UserInDB = Depends(get_current_user)  # 当前登录的用户
):
    logger.info("User %s is updating conversation %s for session_id: %s", current_user.user_id, conversation_id, request.session_id)

    # 验证请求中的 user_id 是否与当前登录的用户一致
    if current_user.user_id != request.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User ID does not match the authenticated user's ID",
        )

    try:
        # 调用服务层更新对话
        await update_conversation_service(conversation_id, request)
        return {"message": "Conversation and prd content updated successfully"}

    except HTTPException as e:
        # 捕获并抛出 HTTP 异常
        raise e

    except Exception as e:
        logger.error(f"Error updating conversation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# 获取 PRD 接口 (是后端直接用的，不需要验证用户，是否需要包装成API接口）
@router.get("/prd", response_model=PrdResponse)
async def get_prd(user_id: int):
    return await get_prd_service(user_id)