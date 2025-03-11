from pydantic import BaseModel, EmailStr
from typing import Optional, Union

# Token模型，用于返回JWT令牌
class Token(BaseModel):
    access_token: str
    token_type: str

# Token数据模型，用于JWT令牌的payload
class TokenData(BaseModel):
    email: Union[str, None] = None

# 用户注册请求模型
class UserRegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    phone_number: str  # 手机号字段
    verification_code: str  # 验证码字段

# 用户注册响应模型
class UserRegisterResponse(BaseModel):
    user_id: int
    username: str
    email: str
    phone_number: str
    access_token: str
    token_type: str = "bearer"

# 登录请求表单模型
class LoginRequestForm(BaseModel):
    username: Optional[str] = None  # 邮箱或用户名
    password: Optional[str] = None  # 密码
    phone_number: Optional[str] = None  # 手机号
    verification_code: Optional[str] = None  # 验证码

# 更新密码请求模型
class UpdatePasswordRequest(BaseModel):
    new_password: str