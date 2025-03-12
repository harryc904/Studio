from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone  # 添加 timezone 导入
from fastapi.security import OAuth2PasswordBearer
from typing import Optional, Union

from api.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_ACCESS_TOKEN_EXPIRE_MINUTES, logger
from api.schemas.auth import TokenData
from api.schemas.user import UserInDB

# 创建密码上下文，用于密码哈希和验证
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 创建OAuth2密码验证流，指定登录端点
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# 验证密码
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# 生成密码哈希
def get_password_hash(password):
    return pwd_context.hash(password)

# 创建访问令牌
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt