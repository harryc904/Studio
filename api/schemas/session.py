from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# 创建会话请求模型
class SessionCreateRequest(BaseModel):
    user_id: int
    session_name: Optional[str] = None

# 会话响应模型
class SessionResponse(BaseModel):
    session_id: int
    user_id: int
    session_name: str
    start_time: datetime
    end_time: Optional[datetime] = None

# 更新会话名称请求模型
class UpdateSessionNameRequest(BaseModel):
    session_id: int
    name: str
    user_id: int