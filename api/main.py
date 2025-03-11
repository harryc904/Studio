from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, EmailStr
from typing import Union, Optional, List
from jose import JWTError, jwt
from datetime import timedelta
from passlib.context import CryptContext
from datetime import datetime
from tencentcloud.sms.v20210111 import sms_client, models
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import (
    TencentCloudSDKException,
)
import random
from psycopg import sql
from psycopg_pool import ConnectionPool
import uuid
import logging
import json
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# from uuid import UUID
# import psycopg2.extras

# # 注册 UUID 类型适配器
# psycopg2.extras.register_uuid()

# 初始化 logging 配置
logging.basicConfig(level=logging.DEBUG)  # 日志基础配置

logger = logging.getLogger(__name__)  # 创建日志记录器

# 创建FastAPI应用实例，指定Swagger UI路径为 /swagger，Redoc路径为 /redoc
app = FastAPI(docs_url="/swagger", redoc_url="/redoc", openapi_url="/openapi.json")

# 连接 PostgreSQL 数据库
db_pool = ConnectionPool.SimpleConnectionPool(
    minconn=int(os.getenv("DB_MIN_CONNECTIONS")),
    maxconn=int(os.getenv("DB_MAX_CONNECTIONS")),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
)

# 配置腾讯云 API 密钥（SecretId 和 SecretKey）
SECRET_ID = os.getenv("TENCENT_SECRET_ID")
SECRET_KEY1 = os.getenv("TENCENT_SECRET_KEY")
SMS_SIGN = os.getenv("SMS_SIGN")  # 短信签名
REGISTER_TEMPLATE_ID = os.getenv("SMS_REGISTER_TEMPLATE_ID")  # 注册模板 ID
LOGIN_TEMPLATE_ID = os.getenv("SMS_LOGIN_TEMPLATE_ID")  # 登录模板 ID
REGION = os.getenv("SMS_REGION")  # 默认区域
SMS_APPID = os.getenv("SMS_APP_ID")  # 短信 SDK App ID


# JWT 配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES"))

# 加密上下文，用于密码加密和校验
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 密码验证流，指定登录端点
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# Pydantic 模型，用于数据验证和序列化
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Union[str, None] = None


class User(BaseModel):
    user_id: int
    username: str
    email: str
    phone_number: Optional[str] = None  # 允许为空


class UserRegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    phone_number: str  # 新增手机号字段
    verification_code: str  # 新增验证码字段


class UpdatePasswordRequest(BaseModel):
    new_password: str


class UserRegisterResponse(BaseModel):
    user_id: int
    username: str
    email: str
    phone_number: str
    access_token: str
    token_type: str = "bearer"


class UserInDB(User):
    hashed_password: str


class SessionCreateRequest(BaseModel):
    user_id: int
    session_name: Optional[str] = None


class LoginRequestForm(BaseModel):
    username: Optional[str] = None  # 邮箱或用户名
    password: Optional[str] = None  # 密码
    phone_number: Optional[str] = None  # 手机号
    verification_code: Optional[str] = None  # 验证码


# 定义模型，用于验证和处理请求数据
class ConversationCreateRequest(BaseModel):
    user_id: int
    session_id: int
    conversation_type: int  # 必填，0 代表 user_message，1 代表 response_from_model
    content: str
    version: Optional[int] = None
    conversation_parent_id: Optional[uuid.UUID] = (
        None  # 可选，父对话 ID，如果没有父对话可为空
    )
    dify_id: Optional[str] = None  # 可选
    knowledge_graph: Optional[str] = None
    dify_func_des: Optional[str] = None
    prd_content: Optional[str] = None
    prd_version: Optional[int] = None
    knowledge_id: Optional[str] = None
    preview_code: Optional[str] = None
    conversation_id: Optional[uuid.UUID] = None
    restore_version: Optional[int] = None


class ConversationUpdateRequest(BaseModel):
    user_id: int  # 用户 ID，用于验证当前登录用户
    session_id: int  # 会话 ID，用于验证该会话是否存在
    knowledge_graph: Optional[str] = None  # 可选字段：knowledge_graph
    dify_func_des: Optional[str] = None  # 可选字段：dify_func_des
    prd_content: Optional[str] = None  # 可选字段：prd_content
    prd_version: Optional[int] = None
    knowledge_id: Optional[str] = None  # 可选字段：knowledge_id


# 用于返回会话数据的模型
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


# 定义请求体的数据模型
class UpdateSessionNameRequest(BaseModel):
    session_id: int
    name: str
    user_id: int


class PrdResponse(BaseModel):
    prd_content: str  # 返回的 prd_content 字段


# 用于校验用户的密码
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


# 用于生成密码的哈希值
def get_password_hash(password):
    return pwd_context.hash(password)


# 获取数据库连接
def get_db_connection():
    if db_pool:
        try:
            conn = db_pool.getconn()
            if conn.closed:
                conn = db_pool.getconn()
            return conn
        except Exception as e:
            logger.error(f"Error getting database connection: {e}")
            raise HTTPException(status_code=500, detail="Database connection error")
    else:
        raise HTTPException(
            status_code=500, detail="Database connection pool not initialized"
        )


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
            db_pool.putconn(conn)


def get_user_by_phone(phone_number: str):
    conn = None
    try:
        # 获取数据库连接
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 执行 SQL 查询，查找手机号对应的用户
            cur.execute(
                sql.SQL(
                    "SELECT user_id, user_name, email, phone_number, password FROM users WHERE phone_number = %s"
                ),
                (phone_number,),
            )
            result = cur.fetchone()  # 获取查询结果

            # 如果找到了该手机号的用户，返回 UserInDB 对象
            if result:
                return UserInDB(
                    user_id=result[0],
                    username=result[1],
                    email=result[2],
                    phone_number=result[3],
                    hashed_password=result[4],
                )
            return None  # 没有找到用户则返回 None
    except Exception as e:
        # 记录错误日志
        logger.error(f"Error fetching user by phone from database: {e}")
        return None
    finally:
        if conn:
            conn.close()  # 确保连接关闭


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

    if not pwd_context.verify(password, user.hashed_password):
        return False

    return user


# 创建 JWT 令牌
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


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
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get(
            "sub"
        )  # 通常 "sub" 存储的是用户身份信息（如 email 或 user_id）
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


async def send_verification_code(phone_number: str, purpose: int):
    if purpose == 1:  # 登录
        user = get_user_by_phone(phone_number)
        if not user:
            raise HTTPException(
                status_code=400,
                detail="Phone number is not registered. Please register first.",
            )

    # 设置腾讯云 SMS 服务的证书
    cred = credential.Credential(SECRET_ID, SECRET_KEY1)
    client = sms_client.SmsClient(cred, REGION)
    # 生成验证码
    verification_code = str(random.randint(100000, 999999))

    # 选择适当的模板 ID 和 Purpose
    if purpose == 0:  # 注册
        TEMPLATE_ID = REGISTER_TEMPLATE_ID
    elif purpose == 1:  # 登录
        TEMPLATE_ID = LOGIN_TEMPLATE_ID
    else:
        raise HTTPException(status_code=400, detail="Invalid purpose value")

    # 构建发送请求的消息
    req = models.SendSmsRequest()
    params = {
        "PhoneNumberSet": [phone_number],
        "SmsSdkAppId": SMS_APPID,
        "TemplateId": TEMPLATE_ID,
        "SignName": SMS_SIGN,
        "TemplateParamSet": [verification_code, "5"],
    }
    req.from_json_string(json.dumps(params))

    try:
        # 发送短信验证码
        response = client.SendSms(req)
        print(response.to_json_string())

        # 储存验证码到数据库，并记录用途
        store_verification_code(phone_number, verification_code, purpose)
        return {"message": "Verification code sent successfully"}

    except TencentCloudSDKException as err:
        print(f"Error sending SMS: {err}")
        raise HTTPException(status_code=500, detail=f"Error sending SMS: {err}")

    except Exception as e:
        print(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Unexpected error occurred")


# 函数：存储验证码
def store_verification_code(phone_number: str, verification_code: str, purpose: int):
    # 获取当前时间和过期时间（5分钟后）
    expiration_time = datetime.now() + timedelta(minutes=5)

    conn = None
    try:
        # 连接到数据库
        conn = get_db_connection()  # 替换为你的数据库连接方式
        cursor = conn.cursor()

        # 检查是否已存在相同手机号和用途的验证码记录
        cursor.execute(
            """
            SELECT COUNT(*) FROM verification_codes
            WHERE phone_number = %s AND purpose = %s;
        """,
            (phone_number, purpose),
        )

        existing_record = cursor.fetchone()[0]

        if existing_record > 0:
            # 如果记录存在，更新验证码和过期时间
            cursor.execute(
                """
                UPDATE verification_codes
                SET verification_code = %s, expiration_time = %s
                WHERE phone_number = %s AND purpose = %s;
            """,
                (verification_code, expiration_time, phone_number, purpose),
            )
            conn.commit()
            print(
                f"Updated verification code for {phone_number} with purpose {purpose}"
            )
        else:
            # 如果记录不存在，插入新的验证码记录
            cursor.execute(
                """
                INSERT INTO verification_codes (phone_number, verification_code, expiration_time, purpose)
                VALUES (%s, %s, %s, %s);
            """,
                (phone_number, verification_code, expiration_time, purpose),
            )
            conn.commit()
            print(
                f"Inserted new verification code for {phone_number} with purpose {purpose}"
            )

    except Exception as e:
        print(f"Error storing verification code: {e}")
        raise HTTPException(status_code=500, detail="Error storing verification code")
    finally:
        if conn:
            conn.close()


# 从数据库中获取有效验证码
def get_verification_code(phone_number: str, purpose: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 查询指定手机号和用途的验证码
            cur.execute(
                """
                SELECT verification_code, expiration_time
                FROM verification_codes
                WHERE phone_number = %s AND purpose = %s
                ORDER BY expiration_time DESC
                LIMIT 1
            """,
                (phone_number, purpose),
            )

            result = cur.fetchone()
            if result:
                stored_code, expiration_time = result
                # 如果验证码过期，返回 None
                if expiration_time < datetime.utcnow():
                    return None
                return stored_code
            return None
    except Exception as e:
        logger.error(f"Error fetching verification code: {e}")
        return None
    finally:
        if conn:
            db_pool.putconn(conn)


# 添加中间件来记录请求和响应
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response status code: {response.status_code}")
    return response


# 请求验证码接口
@app.post("/request_verification_code")
async def request_verification_code(phone_number: str, purpose: int):
    # 通过腾讯云接口发送验证码
    return await send_verification_code(phone_number, purpose)


@app.post("/register", response_model=UserRegisterResponse)
async def register_user(user: UserRegisterRequest):
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

        # 验证手机号验证码
        stored_code = get_verification_code(user.phone_number, purpose=0)  # 0: 注册用途
        if not stored_code:
            raise HTTPException(
                status_code=400, detail="Verification code expired or not sent"
            )

        if stored_code != user.verification_code:
            raise HTTPException(status_code=400, detail="Invalid verification code")

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

        # 生成 JWT 访问令牌
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": new_user[2]}, expires_delta=access_token_expires
        )

        return UserRegisterResponse(
            user_id=new_user[0],
            username=new_user[1],
            email=new_user[2],
            phone_number=new_user[3],
            access_token=access_token,
        )

    except HTTPException as e:
        # 捕获已定义的 HTTPException 并返回具体错误
        raise e

    except Exception as e:
        logger.error(f"Error during user registration: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        if conn:
            db_pool.putconn(conn)


# 登录接口
@app.post("/login", response_model=Token)
async def login(form_data: LoginRequestForm):
    # 情况 1：手机号或邮箱加密码登录
    if form_data.username and form_data.password:
        user = authenticate_user(form_data.username, form_data.password)

        if not user:
            logger.warning("Login failed for user: %s", form_data.username)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        logger.info("User %s logged in successfully", user.email)
        return {"access_token": access_token, "token_type": "bearer"}

    # 情况 2：手机号加验证码登录
    elif form_data.phone_number and form_data.verification_code:
        # 从数据库获取用户信息，检查手机号是否存在
        user = get_user_by_phone(form_data.phone_number)
        print(user)
        if not user:
            logger.warning("Login failed for phone: %s", form_data.phone_number)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Phone number not registered",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 获取数据库中存储的验证码
        stored_code = get_verification_code(
            form_data.phone_number, purpose=1
        )  # 1: 登录用途
        if not stored_code:
            raise HTTPException(
                status_code=400, detail="Verification code expired or not sent"
            )

        # 对比验证码
        if stored_code != form_data.verification_code:
            raise HTTPException(status_code=400, detail="Invalid verification code")

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        logger.info("User %s logged in successfully with phone number", user.email)
        return {"access_token": access_token, "token_type": "bearer"}

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid login data provided",
        )


# 获取当前用户信息的接口
@app.get("/users/me", response_model=User)
async def read_users_me(current_user: UserInDB = Depends(get_current_user)):
    # 直接返回当前用户信息
    return current_user


# 自定义 OpenAPI 配置，让 Swagger UI 使用 Bearer Token
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Your API Title",
        version="1.0.0",
        description="Your API description",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    }
    openapi_schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


# 将自定义 OpenAPI 配置应用到 FastAPI 实例中
app.openapi = custom_openapi


# 登出接口（仅用于前端指示，JWT 无状态无法在后端登出）
@app.post("/logout")
async def logout():
    return {"msg": "User logged out successfully"}


# 创建会话接口
@app.post("/sessions")
def create_session(
    request: SessionCreateRequest, current_user: UserInDB = Depends(get_current_user)
):
    logger.info("Creating a session for user_id: %s", request.user_id)

    # 验证请求中的 user_id 是否与当前登录的用户一致
    if current_user.user_id != request.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User ID does not match the authenticated user's ID",
        )

    conn = None
    try:
        # 获取数据库连接
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 获取当前时间作为 start_time
            start_time = datetime.now()
            # 如果 session_name 没有传入，则生成默认的名称
            session_name = (
                request.session_name
                if request.session_name
                else start_time.strftime("%Y%m%d%H%M%S")
            )

            # 插入新的会话数据到 sessions 表
            insert_query = sql.SQL("""
                INSERT INTO sessions (user_id, session_name, start_time)
                VALUES (%s, %s, %s)
                RETURNING session_id, user_id, session_name, start_time;
            """)
            cur.execute(insert_query, (request.user_id, session_name, start_time))

            # 提交事务
            conn.commit()

            # 获取插入的会话数据
            result = cur.fetchone()
            if result:
                return {
                    "session_id": result[0],
                    "user_id": result[1],
                    "session_name": result[2],
                    "start_time": result[3],
                    "message": "Session created successfully",
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to create session")

    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.putconn(conn)


@app.post("/conversations")
async def create_conversation(
    request: ConversationCreateRequest,
    current_user: UserInDB = Depends(get_current_user),
):
    logger.info(
        "User %s is creating a conversation for session_id: %s",
        current_user.user_id,
        request.session_id,
    )

    # 验证请求中的 user_id 是否与当前登录的用户一致
    if current_user.user_id != request.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User ID does not match the authenticated user's ID",
        )

    conn = None
    created_at = datetime.now()  # 获取当前时间
    try:
        # 获取数据库连接
        conn = get_db_connection()
        cur = conn.cursor()  # 创建一个游标

        # 处理可选字段的默认值
        conversation_id = str(
            request.conversation_id or uuid.uuid4()
        )  # 转换 UUID 为字符串
        conversation_child_version = None
        version = 1  # 默认版本号为 1，如果没有父对话

        # 如果有父对话 ID，则更新父级的 conversation_child_version 字段
        if request.conversation_parent_id:
            # 查询父级对话的当前 conversation_child_version
            cur.execute(
                "SELECT conversation_child_version FROM conversations WHERE conversation_id = %s",
                (str(request.conversation_parent_id),),  # 转换 UUID 为字符串
            )
            parent_record = cur.fetchone()
            logger.info("Fetched parent_record: %s", parent_record)

            if parent_record:
                existing_child_version = parent_record[0]
                logger.info(
                    "Existing child version type: %s, value: %s",
                    type(existing_child_version),
                    existing_child_version,
                )

                if existing_child_version:
                    # 如果已经是字符串形式的 JSON，先进行解析
                    if isinstance(existing_child_version, str):
                        child_versions = json.loads(existing_child_version)
                    else:
                        child_versions = existing_child_version
                else:
                    child_versions = {}

                # 自动生成版本号：找到最高版本号并加一
                if child_versions:
                    max_version = max(int(ver) for ver in child_versions.keys())
                    version = max_version + 1
                else:
                    version = 1

                # 更新子版本信息
                child_versions[str(version)] = conversation_id
                conversation_child_version = json.dumps(
                    child_versions
                )  # 将字典转换回 JSON 字符串
                logger.info(
                    "Updated conversation_child_version: %s", conversation_child_version
                )

                # 更新父级 conversation 的 conversation_child_version
                cur.execute(
                    "UPDATE conversations SET conversation_child_version = %s WHERE conversation_id = %s",
                    (
                        conversation_child_version,
                        str(request.conversation_parent_id),
                    ),  # 转换 UUID 为字符串
                )
                logger.info(
                    "Updated parent conversation's child version in the database"
                )

        # 插入对话内容到 conversations 表
        insert_query = sql.SQL(""" 
            INSERT INTO conversations (
                conversation_id,
                session_id,
                created_at,
                conversation_type,
                content,
                version,
                conversation_parent_id,
                conversation_child_version,
                knowledge_graph,
                dify_func_des,
                knowledge_id,
                dify_id,
                preview_code
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING conversation_id, session_id, created_at, conversation_type, content, version, conversation_parent_id, conversation_child_version, knowledge_graph, dify_func_des, knowledge_id, dify_id, preview_code;
        """)

        # 插入数据
        cur.execute(
            insert_query,
            (
                conversation_id,  # 处理后的 UUID（字符串形式）
                request.session_id,  # 会话ID
                created_at,  # 当前时间
                request.conversation_type,  # 对话类型
                request.content,  # 文本内容
                version,  # 版本
                str(request.conversation_parent_id)
                if request.conversation_parent_id
                else None,  # 转换 UUID 为字符串
                None,  # 更新后的子版本信息
                request.knowledge_graph,  # 可选字段 knowledge_graph
                request.dify_func_des,  # 可选字段 dify_func_des
                request.knowledge_id,  # 可选字段 knowledge_id
                request.dify_id,  # 可选字段 dify_id
                request.preview_code,  # 可选字段 preview_code
            ),
        )

        # 提交事务
        conn.commit()
        result = cur.fetchone()  # 获取插入的返回结果

        # 更新 sessions 表的 end_time 字段
        cur.execute(
            "UPDATE sessions SET end_time = %s WHERE session_id = %s",
            (created_at, request.session_id),
        )
        conn.commit()

        # 初始化 prd_version 和 prd_content 为 None
        prd_version = None
        prd_content = None
        latest = None
        restore_version = None

        # 如果插入成功且提供了 prd_content
        if request.prd_content:
            # 查询 session_id 下现有的 prd_version（最大版本号）
            cur.execute(
                "SELECT MAX(prd_version) FROM prd WHERE session_id = %s",
                (request.session_id,),
            )
            max_prd_version = cur.fetchone()[0]

            # 如果没有版本记录，设置为 1
            if max_prd_version is None:
                new_prd_version = 1
            else:
                new_prd_version = max_prd_version + 1

            # 插入到 prd 表
            insert_prd_query = sql.SQL(""" 
                INSERT INTO prd (
                    prd_version,
                    conversation_id,
                    session_id,
                    prd_content,
                    created_by,
                    latest,
                    restore_version
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING prd_content, prd_version, latest, restore_version;
            """)

            # 如果前端传入 restore_version，使用传入值，否则为 NULL
            restore_version_value = (
                request.restore_version if request.restore_version is not None else None
            )

            # 插入数据到 prd 表
            cur.execute(
                insert_prd_query,
                (
                    new_prd_version,  # 计算出的新版本号
                    conversation_id,  # 关联的conversation_id
                    request.session_id,  # 关联的session_id
                    request.prd_content,  # PRD的内容
                    current_user.username,  # 创建人（假设current_user包含username字段）
                    1,  # 最新版本设置为 1
                    restore_version_value,  # restore_version 如果提供，则存储，否则为 null
                ),
            )

            # 获取 prd_content 和 prd_version
            prd_content, prd_version, latest, restore_version = cur.fetchone()

            # 提交PRD插入事务
            conn.commit()

            # 更新上一版本的 prd 表格，将其 latest 字段设置为 0
            if max_prd_version is not None:
                cur.execute(
                    "UPDATE prd SET latest = 0 WHERE session_id = %s AND prd_version = %s",
                    (request.session_id, max_prd_version),
                )
                conn.commit()

        if result:
            # 将结果返回给前端，包括更新后的父级 conversation_child_version 信息
            return {
                "conversation_id": result[0],
                "session_id": result[1],
                "created_at": result[2],
                "conversation_type": result[3],
                "content": result[4],
                "version": result[5],
                "conversation_parent_id": result[6],
                "conversation_child_version": result[7],
                "knowledge_graph": result[8],
                "dify_func_des": result[9],
                "knowledge_id": result[10],
                "dify_id": result[11],
                "preview_code": result[12],
                "conversation_para_version": conversation_child_version,  # 返回更新后的父级子版本信息
                "prd_version": prd_version,  # 返回 PRD 的版本号
                "prd_content": prd_content,  # 返回 PRD 的内容
                "latest": latest,
                "restore_version": restore_version,
            }
        else:
            logger.error("Failed to fetch insert result")
            raise HTTPException(status_code=500, detail="Failed to create conversation")

    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.putconn(conn)


# 查询会话的接口
@app.get("/sessions", response_model=List[dict])
def get_sessions_by_user_id(
    user_id: int, current_user: UserInDB = Depends(get_current_user)
):
    # 验证 user_id 和当前用户是否一致
    if current_user.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User ID does not match the authenticated user's ID",
        )

    conn = None
    try:
        # 获取数据库连接
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 查询指定 user_id 的会话信息
            query = """
            SELECT session_id, session_name, start_time, end_time
            FROM sessions
            WHERE user_id = %s
            ORDER BY session_id ASC
            """
            cur.execute(query, (user_id,))

            # 获取查询结果
            rows = cur.fetchall()
            if not rows:
                return []

            # 构造返回结果，并查找每个 session_id 对应的 session_desc
            sessions = []
            for row in rows:
                session_id = row[0]
                session_name = row[1]
                start_time = row[2]
                end_time = row[3]

                # 查找 conversations 表中该 session_id 最早的 conversation_type 为 1 的 content
                desc_query = """
                SELECT content
                FROM conversations
                WHERE session_id = %s AND conversation_type = 1
                ORDER BY created_at ASC
                LIMIT 1
                """
                cur.execute(desc_query, (session_id,))
                desc_result = cur.fetchone()

                # 如果存在最早的 response_from_model，则作为 session_desc
                session_desc = desc_result[0] if desc_result else None

                # 添加到结果列表
                sessions.append(
                    {
                        "session_id": session_id,
                        "session_name": session_name,
                        "start_time": start_time,
                        "end_time": end_time,
                        "session_desc": session_desc,
                    }
                )

            return sessions

    except Exception as e:
        logger.error(f"Error querying sessions for user_id {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        if conn:
            db_pool.putconn(conn)


# 查询对话的接口
@app.get("/conversations/{session_id}", response_model=List[ConversationResponse])
async def get_conversations(
    session_id: int,
    user_id: int,
    conversation_id: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_user),
):
    logger.info(
        "User %s is querying conversations for session_id: %s", user_id, session_id
    )
    # 验证请求中的 user_id 是否与当前登录的用户一致
    if current_user.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User ID does not match the authenticated user's ID",
        )

    conn = None

    try:
        # 获取数据库连接
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 查询 session_id 对应的 user_id
            logger.info("Checking session_id %s for user_id %s", session_id, user_id)
            cur.execute(
                "SELECT user_id FROM sessions WHERE session_id = %s", (session_id,)
            )
            result = cur.fetchone()

            # 如果查询不到 session_id，返回空
            if not result:
                logger.warning("Session ID %s not found", session_id)
                return []
            session_user_id = result[0]  # 获取查询到的 user_id

            # 比对 session_id 对应的 user_id 和 请求的 user_id 是否一致
            if session_user_id != user_id:
                logger.warning(
                    "Session user_id %s does not match request user_id %s",
                    session_user_id,
                    user_id,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to access this session.",
                )

            # 如果传递了 conversation_id，通过 conversation_child_version 找到链路的起始点
            if conversation_id:
                while True:
                    cur.execute(
                        """
                        SELECT conversation_id
                        FROM conversations
                        WHERE conversation_parent_id = %s
                        ORDER BY version DESC
                        LIMIT 1
                    """,
                        (conversation_id,),
                    )
                    next_conversation = cur.fetchone()
                    if next_conversation:
                        # 如果找到下一个版本，继续查找
                        conversation_id = next_conversation[0]
                    else:
                        # 没有下一个版本，则停止
                        break
            else:
                # 如果没有传递 conversation_id，查询 session_id 下最新的 conversation_id
                cur.execute(
                    """
                    SELECT conversation_id
                    FROM conversations
                    WHERE session_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """,
                    (session_id,),
                )
                latest_conversation = cur.fetchone()
                if latest_conversation:
                    conversation_id = latest_conversation[0]
                    logger.info(
                        "Latest conversation_id for session_id %s is %s",
                        session_id,
                        conversation_id,
                    )
                else:
                    return []

            logger.info("Initial conversation id is %s", conversation_id)
            # 递归查找链路上的所有对话
            conversations = []
            visited_ids = set()
            stack = [conversation_id]

            while stack:
                current_id = stack.pop()
                if current_id in visited_ids:
                    continue
                visited_ids.add(current_id)
                logger.info("Processing conversation_id %s", current_id)

                # 查询当前对话信息
                cur.execute(
                    """
                    SELECT conversation_id, session_id, created_at, conversation_type, content, version,
                           conversation_parent_id, conversation_child_version, knowledge_graph, dify_func_des,
                           knowledge_id, dify_id, preview_code
                    FROM conversations
                    WHERE conversation_id = %s
                """,
                    (current_id,),
                )
                conversation_data = cur.fetchone()

                if conversation_data:
                    # 查询 prd_content 和 prd_version（如果有的话）
                    prd_content = None
                    prd_version = None
                    latest = None
                    restore_version = None
                    cur.execute(
                        """ 
                        SELECT prd_content, prd_version, latest, restore_version
                        FROM prd
                        WHERE session_id = %s AND conversation_id = %s
                        ORDER BY prd_version DESC
                        LIMIT 1
                    """,
                        (session_id, current_id),
                    )
                    prd_result = cur.fetchone()

                    if prd_result:
                        prd_content, prd_version, latest, restore_version = prd_result

                    # 如果存在父级对话，获取父级的conversation_child_version
                    conversation_para_version = None
                    if conversation_data[6]:  # conversation_parent_id
                        parent_id = conversation_data[6]
                        cur.execute(
                            """
                            SELECT conversation_child_version
                            FROM conversations
                            WHERE conversation_id = %s
                        """,
                            (parent_id,),
                        )
                        parent_data = cur.fetchone()
                        if parent_data and parent_data[0]:
                            # 确保父级的conversation_child_version是字典类型
                            if isinstance(parent_data[0], str):
                                try:
                                    conversation_para_version = json.loads(
                                        parent_data[0]
                                    )
                                except json.JSONDecodeError:
                                    logger.warning(
                                        "Failed to decode JSON for parent_id %s",
                                        parent_id,
                                    )
                                    conversation_para_version = None
                            elif isinstance(parent_data[0], dict):
                                conversation_para_version = parent_data[0]

                    # 使用字典解包来创建 Pydantic 模型
                    conversation = ConversationResponse(
                        conversation_id=conversation_data[0],
                        session_id=conversation_data[1],
                        created_at=conversation_data[2],
                        conversation_type=conversation_data[3],
                        content=conversation_data[4],
                        version=conversation_data[5],
                        conversation_parent_id=conversation_data[6],
                        conversation_para_version=conversation_para_version,
                        knowledge_graph=conversation_data[8],
                        dify_func_des=conversation_data[9],
                        prd_content=prd_content,  # 添加prd_content
                        prd_version=prd_version,  # 添加prd_version
                        latest=latest,  # 返回最新的标记
                        restore_version=restore_version,  # 返回恢复版本号
                        knowledge_id=conversation_data[10],
                        dify_id=conversation_data[11],
                        preview_code=conversation_data[12],
                    )
                    conversations.append(conversation)

                    # 如果存在父级对话，继续向上查找
                    if conversation_data[6]:
                        stack.append(str(conversation_data[6]))
            # 根据 created_at 对 conversations 进行排序
            conversations.sort(key=lambda x: x.created_at)

        # 返回查询结果
        return conversations

    except Exception as e:
        logger.error(f"Error querying conversations: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        if conn:
            db_pool.putconn(conn)  # 将连接放回连接池


@app.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int, user_id: int, current_user: UserInDB = Depends(get_current_user)
):
    # 验证请求中的 user_id 是否与当前登录的用户一致
    if current_user.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User ID does not match the authenticated user's ID",
        )
    conn = None
    try:
        # 获取数据库连接
        conn = get_db_connection()
        cur = conn.cursor()

        # 首先检查 session 是否存在，并且属于当前用户
        session_check_query = """
        SELECT user_id FROM sessions WHERE session_id = %s
        """
        cur.execute(session_check_query, (session_id,))
        result = cur.fetchone()

        if not result:
            return []

        # 确认 session 属于请求的 user_id
        session_user_id = result[0]
        if session_user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this session.",
            )

        # 删除 prd 表中与 session_id 相关的记录
        delete_prd_query = """
        DELETE FROM prd WHERE session_id = %s
        """
        cur.execute(delete_prd_query, (session_id,))

        # 开始删除操作，删除 conversations 表中对应的记录
        delete_conversations_query = """
        DELETE FROM conversations WHERE session_id = %s
        """
        cur.execute(delete_conversations_query, (session_id,))

        # 删除 sessions 表中对应的记录
        delete_session_query = """
        DELETE FROM sessions WHERE session_id = %s
        """
        cur.execute(delete_session_query, (session_id,))

        # 提交事务
        conn.commit()

        # 返回删除成功的消息
        logger.info(
            f"Session {session_id} and its conversations, prd records deleted for user {user_id}"
        )
        return {
            "message": "Session and its conversations, prd records deleted successfully"
        }

    except HTTPException as http_exc:
        # 捕获并抛出自定义的 HTTP 错误
        raise http_exc

    except Exception as e:
        logger.error(f"Error deleting session {session_id} for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        if cur:
            cur.close()  # 关闭游标
        if conn:
            db_pool.putconn(conn)  # 将连接放回连接池


@app.put("/sessions/update_name")
async def update_session_name(
    request: UpdateSessionNameRequest,
    current_user: UserInDB = Depends(get_current_user),
):
    # 验证请求中的 user_id 是否与当前登录的用户一致
    if current_user.user_id != request.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User ID does not match the authenticated user's ID",
        )

    conn = None
    try:
        # 获取数据库连接
        conn = get_db_connection()
        cur = conn.cursor()

        # 检查 session 是否存在，并且属于请求的 user_id
        session_check_query = """
        SELECT user_id FROM sessions WHERE session_id = %s
        """
        cur.execute(session_check_query, (request.session_id,))
        result = cur.fetchone()

        if not result:
            return []

        # 确认 session 属于请求的 user_id
        session_user_id = result[0]
        if session_user_id != request.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update this session.",
            )

        # 更新 session_name
        update_query = """
        UPDATE sessions
        SET session_name = %s
        WHERE session_id = %s
        """
        cur.execute(update_query, (request.name, request.session_id))

        # 提交事务
        conn.commit()

        # 返回成功消息
        logger.info(
            f"Session {request.session_id} name updated to '{request.name}' by user {current_user.user_id}"
        )
        return {"message": "Session name updated successfully"}

    except HTTPException as http_exc:
        # 捕获并抛出自定义的 HTTP 错误
        raise http_exc

    except Exception as e:
        logger.error(
            f"Error updating session name for session_id {request.session_id}: {e}"
        )
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        if cur:
            cur.close()  # 关闭游标
        if conn:
            db_pool.putconn(conn)  # 将连接放回连接池


@app.put("/users/update_password")
async def update_password(
    request: UpdatePasswordRequest, current_user: UserInDB = Depends(get_current_user)
):
    new_password = request.new_password
    conn = None
    try:
        # 获取数据库连接
        conn = get_db_connection()
        cur = conn.cursor()

        # 将新密码进行哈希处理
        hashed_password = get_password_hash(new_password)

        # 更新数据库中的密码字段
        update_query = """
        UPDATE users
        SET password = %s
        WHERE user_id = %s
        """
        cur.execute(update_query, (hashed_password, current_user.user_id))

        # 提交事务
        conn.commit()

        # 返回成功消息
        logger.info(f"Password updated successfully for user {current_user.user_id}")
        return {"message": "Password updated successfully"}

    except Exception as e:
        logger.error(f"Error updating password for user {current_user.user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        if conn:
            db_pool.putconn(conn)  # 将连接放回连接池


@app.put("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: uuid.UUID,  # 通过 URL 参数传递 conversation_id
    request: ConversationUpdateRequest,  # 请求体使用新的结构体
    current_user: UserInDB = Depends(get_current_user),  # 当前登录的用户
):
    logger.info(
        "User %s is updating conversation %s for session_id: %s",
        current_user.user_id,
        conversation_id,
        request.session_id,
    )

    # 验证请求中的 user_id 是否与当前登录的用户一致
    if current_user.user_id != request.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User ID does not match the authenticated user's ID",
        )

    conn = None
    try:
        # 获取数据库连接
        conn = get_db_connection()
        cur = conn.cursor()

        # 查询是否存在该 conversation_id 和 session_id 对应的对话
        cur.execute(
            "SELECT conversation_id, session_id FROM conversations WHERE conversation_id = %s AND session_id = %s",
            (
                str(conversation_id),
                str(request.session_id),
            ),  # 确保 UUID 转换为字符串传递
        )
        conversation_record = cur.fetchone()

        if not conversation_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found for the given session_id",
            )

        # 1. 构建更新字段，分别更新每个字段
        if request.knowledge_graph is not None:
            cur.execute(
                """
                UPDATE conversations
                SET knowledge_graph = %s
                WHERE conversation_id = %s
            """,
                (request.knowledge_graph, str(conversation_id)),
            )  # 使用字符串形式的 UUID

        if request.dify_func_des is not None:
            cur.execute(
                """
                UPDATE conversations
                SET dify_func_des = %s
                WHERE conversation_id = %s
            """,
                (request.dify_func_des, str(conversation_id)),
            )  # 使用字符串形式的 UUID

        if request.knowledge_id is not None:
            cur.execute(
                """
                UPDATE conversations
                SET knowledge_id = %s
                WHERE conversation_id = %s
            """,
                (request.knowledge_id, str(conversation_id)),
            )  # 使用字符串形式的 UUID

        # 2. 更新 prd 表的 prd_content（如果有更新）
        if request.prd_content is not None:
            cur.execute(
                """
                UPDATE prd
                SET prd_content = %s
                WHERE conversation_id = %s
            """,
                (request.prd_content, str(conversation_id)),
            )  # 使用字符串形式的 UUID

        # 提交事务
        conn.commit()

        return {"message": "Conversation and prd content updated successfully"}

    except HTTPException as e:
        # 捕获并抛出 HTTP 异常
        raise e

    except Exception as e:
        logger.error(f"Error updating conversation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        if conn:
            db_pool.putconn(conn)  # 将连接放回连接池


@app.get("/get_prd", response_model=PrdResponse)
async def get_prd(user_id: int):
    conn = None
    try:
        # 获取数据库连接
        conn = get_db_connection()

        # 查询该 user_id 最新的 session_id
        with conn.cursor() as cur:
            # 获取 end_time 最新的 session_id (按用户筛选)
            cur.execute(
                """
                SELECT session_id
                FROM sessions
                WHERE user_id = %s
                ORDER BY end_time DESC
                LIMIT 1
            """,
                (user_id,),
            )
            session_id_record = cur.fetchone()

            if not session_id_record:
                raise HTTPException(
                    status_code=404, detail="No sessions found for the user"
                )

            session_id = session_id_record[0]
            print
            # 查询该 session_id 下 prd_version 最大的 prd_content
            cur.execute(
                """
                SELECT prd_content
                FROM prd
                WHERE session_id = %s
                ORDER BY prd_version DESC
                LIMIT 1
            """,
                (session_id,),
            )
            prd_content_record = cur.fetchone()

            if not prd_content_record:
                raise HTTPException(
                    status_code=404, detail="No PRD content found for the session"
                )

            # 返回 prd_content
            return {"prd_content": prd_content_record[0]}

    except HTTPException as e:
        # 捕获并抛出 HTTP 异常
        raise e

    except Exception as e:
        logger.error(f"Error retrieving PRD: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        if conn:
            db_pool.putconn(conn)  # 将连接放回连接池
