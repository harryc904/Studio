from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional

from api.schemas.user import UserInDB
from api.schemas.auth import TokenData, UserRegisterRequest
from api.utils.security import verify_password, get_password_hash
from api.utils.db import get_db_connection
from api.config import JWT_SECRET_KEY, JWT_ALGORITHM
from api.utils.logger import get_logger

logger = get_logger(__name__)


# 创建OAuth2密码验证流，指定登录端点
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# 从数据库中获取用户信息
def get_user_from_db(identifier: str, is_email: bool = True):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            if is_email:
                # 使用邮箱查询用户
                cur.execute(
                    "SELECT user_id, user_name, email, password, phone_number FROM users WHERE email = %s",
                    (identifier,),
                )
            else:
                # 使用手机号查询用户
                cur.execute(
                    "SELECT user_id, user_name, email, password, phone_number FROM users WHERE phone_number = %s",
                    (identifier,),
                )

            result = cur.fetchone()

            if result:
                # 创建并返回用户对象
                return UserInDB(
                    user_id=result[0],
                    username=result[1],
                    email=result[2],
                    hashed_password=result[3],
                    phone_number=result[4],
                )

            return None
    except Exception as e:
        logger.error(f"Error fetching user from database: {e}")
        return None
    finally:
        if conn:
            conn.close()

# 根据手机号获取用户
def get_user_by_phone(phone_number: str):
    return get_user_from_db(phone_number, is_email=False)

# 验证用户并返回用户数据
def authenticate_user(username: str, password: str):
    # 判断输入的是邮箱还是手机号
    if "@" in username:
        # 如果包含 @，认为是邮箱
        user = get_user_from_db(username, is_email=True)
    else:
        # 否则，认为是手机号
        user = get_user_from_db(username, is_email=False)

    if not user:
        return False

    if not verify_password(password, user.hashed_password):
        return False

    return user

# 定义一个函数，用于解码 JWT 并获取当前用户信息
def get_current_user(token: str = Depends(oauth2_scheme)):
    # 定义 JWT 验证失败时的异常
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # 解码 JWT Token，获取当前用户的 email 信息
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        email: str = payload.get("sub")  # 通常 "sub" 存储的是用户身份信息（如 email 或 user_id）
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception

    # 从数据库中获取用户信息
    user = get_user_from_db(identifier=token_data.email, is_email=True)
    if user is None:
        raise credentials_exception

    return user  # 返回当前用户信息

# 用户注册服务
async def register_user_service(user: UserRegisterRequest):
    conn = None

    # 连接到数据库
    conn = get_db_connection()

    try:
        # 检查手机号是否已存在
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id FROM users WHERE phone_number = %s",
                (user.phone_number,),
            )
            if cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number already registered",
                )

        # 检查邮箱是否已存在
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM users WHERE email = %s", (user.email,))
            if cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered",
                )

        # 检查用户名是否已存在
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id FROM users WHERE user_name = %s", (user.username,)
            )
            if cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already registered",
                )

        # 哈希用户密码
        hashed_password = get_password_hash(user.password)

        # 创建新用户并插入数据库
        with conn.cursor() as cur:
            insert_query = """
            INSERT INTO users (user_name, email, password, phone_number)
            VALUES (%s, %s, %s, %s)
            RETURNING user_id, user_name, email, phone_number
            """
            cur.execute(
                insert_query,
                (user.username, user.email, hashed_password, user.phone_number),
            )
            new_user = cur.fetchone()
            conn.commit()

        # 返回新用户信息
        return {
            "user_id": new_user[0],
            "username": new_user[1],
            "email": new_user[2],
            "phone_number": new_user[3],
        }

    except HTTPException as e:
        # 捕获已定义的 HTTPException 并返回具体错误
        raise e

    except Exception as e:
        logger.error(f"Error during user registration: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        if conn:
            conn.close()