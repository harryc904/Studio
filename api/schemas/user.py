from pydantic import BaseModel, EmailStr
from typing import Optional

# 基础用户模型
class User(BaseModel):
    user_id: int
    username: str
    email: str
    phone_number: Optional[str] = None  # 允许为空

# 数据库中的用户模型，包含密码哈希
class UserInDB(User):
    hashed_password: str