from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

# 创建对话请求模型
class ConversationCreateRequest(BaseModel):
    user_id: int
    session_id: int
    conversation_type: int  # 必填，0 代表 user_message，1 代表 response_from_model
    content: str
    version: Optional[int] = None
    conversation_parent_id: Optional[uuid.UUID] = None  # 可选，父对话 ID
    dify_id: Optional[str] = None  # 可选
    knowledge_graph: Optional[str] = None
    dify_func_des: Optional[str] = None
    prd_content: Optional[str] = None
    prd_version: Optional[int] = None
    knowledge_id: Optional[str] = None
    preview_code: Optional[str] = None
    conversation_id: Optional[uuid.UUID] = None
    restore_version: Optional[int] = None

# 创建对话响应模型
class ConversationResponse(BaseModel):
    conversation_id: str
    session_id: int
    created_at: datetime
    conversation_type: int
    content: str
    version: int
    conversation_parent_id: Optional[uuid.UUID] = None
    conversation_para_version: Optional[dict] = None
    knowledge_graph: Optional[str] = None
    dify_func_des: Optional[str] = None
    prd_content: Optional[str] = None
    prd_version: Optional[int] = None
    knowledge_id: Optional[str] = None
    dify_id: Optional[str] = None
    preview_code: Optional[str] = None
    latest: Optional[int]  # PRD是否为最新版本
    restore_version: Optional[int]  # 恢复的版本号

# PRD响应模型
class PrdResponse(BaseModel):
    prd_content: str  # 返回的 prd_content 字段