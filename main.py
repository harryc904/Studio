from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel, OAuthFlowPassword
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.models import SecuritySchemeType, OAuth2
from pydantic import BaseModel, Field
from typing import Union, Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
import psycopg2
from psycopg2 import sql
from psycopg2 import pool  # 导入连接池模块
import uuid
import asyncpg
import logging
import json

# 初始化 logging 配置
logging.basicConfig(
    filename='/home/lighthouse/studio/debuglog/backend.log',  # 输出日志的文件
    level=logging.DEBUG,  # 日志级别为 DEBUG
    format='%(asctime)s - %(levelname)s - %(message)s'  # 日志格式
)

logger = logging.getLogger(__name__)  # 创建日志记录器

# 创建FastAPI应用实例
app = FastAPI()

# 连接 PostgreSQL 数据库
db_pool = pool.SimpleConnectionPool(
    minconn=1,  # 最小连接数
    maxconn=20,  # 最大连接数
    dbname="StudioAIDB",
    user="user_PpykNG",
    password="password_jY6MwW",
    host="43.129.162.15",
    port="5432"
)

# JWT 配置
SECRET_KEY = "aP6pUzRWg9ae9UojkDPFGXBcFvRqRv7UwTiTe3LMzKk"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 14400

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

class UserInDB(User):
    hashed_password: str

class SessionCreateRequest(BaseModel):
    user_id: int
    session_name: Optional[str] = None

# 定义模型，用于验证和处理请求数据
class ConversationCreateRequest(BaseModel):
    user_id: int
    session_id: int
    conversation_type: int  # 必填，0 代表 user_message，1 代表 response_from_model
    content: str
    version: int
    conversation_parent_id: Optional[uuid.UUID] = None  # 可选，父对话 ID，如果没有父对话可为空
    dify_id: Optional[str] = None  # 可选
    dify_func_def: Optional[str] = None
    dify_func_des: Optional[str] = None
    dify_mod_des: Optional[str] = None
    dify_code: Optional[str] = None
    preview_code: Optional[str] = None
    conversation_id: Optional[uuid.UUID] = None

# 用于返回会话数据的模型
class ConversationResponse(BaseModel):
    conversation_id: str
    session_id: int
    created_at: datetime
    user_message: str
    response_from_model: str
    dify_func_def: Optional[str] = None
    dify_func_des: Optional[str] = None
    dify_mod_des: Optional[str] = None
    dify_code: Optional[str] = None
    dify_id: Optional[str] = None
    preview_code: Optional[str] = None

# 定义请求体的数据模型
class UpdateSessionNameRequest(BaseModel):
    session_id: int
    name: str
    user_id: int

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
        raise HTTPException(status_code=500, detail="Database connection pool not initialized")

# 从数据库中获取用户信息
def get_user_from_db(email: str):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT user_id, user_name, email, password FROM users WHERE email = %s"),
                (email,)
            )
            result = cur.fetchone()
            if result:
                hashed_password = get_password_hash(result[3])
                return UserInDB(user_id=result[0], username=result[1], email=result[2], hashed_password=hashed_password)
            return None
    except Exception as e:
        logger.error(f"Error fetching user from database: {e}")
        return None
    finally:
        if conn:
            db_pool.putconn(conn)

# 验证用户并返回用户数据
def authenticate_user(email: str, password: str):
    user = get_user_from_db(email)
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
        email: str = payload.get("sub")  # 通常 "sub" 存储的是用户身份信息（如 email 或 user_id）
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception

    # 从数据库中获取用户信息
    user = get_user_from_db(email=token_data.email)
    if user is None:
        raise credentials_exception

    return user  # 返回当前用户信息

# 添加中间件来记录请求和响应
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response status code: {response.status_code}")
    return response

# 登录接口
@app.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
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
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
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
def create_session(request: SessionCreateRequest, current_user: UserInDB = Depends(get_current_user)):
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
            session_name = request.session_name if request.session_name else start_time.strftime("%Y%m%d%H%M%S")

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
                    "message": "Session created successfully"
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to create session")
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.putconn(conn)

# 创建对话接口
@app.post("/conversations")
async def create_conversation(request: ConversationCreateRequest, current_user: UserInDB = Depends(get_current_user)):
    logger.info("User %s is creating a conversation for session_id: %s", current_user.user_id, request.session_id)
    
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
        created_at = datetime.now()  # 获取当前时间

        # 处理可选字段的默认值
        conversation_id = request.conversation_id or str(uuid.uuid4())  # 生成UUID（如果为空）
        conversation_child_version = None

        # 如果有父对话 ID，则更新父级的 conversation_child_version 字段
        if request.conversation_parent_id:
            with conn.cursor() as cur:
                # 查询父级对话的当前 conversation_child_version
                cur.execute(
                    "SELECT conversation_child_version FROM conversations WHERE conversation_id = %s",
                    (str(request.conversation_parent_id),)
                )
                parent_record = cur.fetchone()
                if parent_record:
                    existing_child_version = parent_record[0]
                    if existing_child_version:
                        # 解析为字典形式
                        child_versions = json.loads(existing_child_version)
                    else:
                        child_versions = {}

                    # 更新子版本信息
                    child_versions[str(request.version)] = str(conversation_id)
                    conversation_child_version = json.dumps(child_versions)

                    # 更新父级 conversation 的 conversation_child_version
                    cur.execute(
                        "UPDATE conversations SET conversation_child_version = %s WHERE conversation_id = %s",
                        (conversation_child_version, str(request.conversation_parent_id))
                    )

        # 准备插入语句
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
                dify_func_def,
                dify_func_des,
                dify_mod_des,
                dify_code,
                dify_id,
                preview_code
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING conversation_id, session_id, created_at, conversation_type, content, version, conversation_parent_id, conversation_child_version, dify_func_def, dify_func_des, dify_mod_des, dify_code, dify_id, preview_code;
        """)

        # 插入数据
        with conn.cursor() as cur:
            cur.execute(
                insert_query,
                (
                    conversation_id,             # 处理后的 UUID
                    request.session_id,          # 会话ID
                    created_at,                  # 当前时间
                    request.conversation_type,   # 对话类型
                    request.content,             # 文本内容
                    request.version,             # 版本
                    request.conversation_parent_id,  # 父对话 ID（如果存在）
                    conversation_child_version,  # 更新后的子版本信息
                    request.dify_func_def,       # 可选字段 dify_func_def
                    request.dify_func_des,       # 可选字段 dify_func_des
                    request.dify_mod_des,        # 可选字段 dify_mod_des
                    request.dify_code,           # 可选字段 dify_code
                    request.dify_id,             # 可选字段 dify_id
                    request.preview_code         # 可选字段 preview_code
                )
            )

            # 提交事务
            conn.commit()
            result = cur.fetchone()  # 获取插入的返回结果

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
                "dify_func_def": result[8],
                "dify_func_des": result[9],
                "dify_mod_des": result[10],
                "dify_code": result[11],
                "dify_id": result[12],
                "preview_code": result[13],
                "conversation_para_version": conversation_child_version  # 新增字段，返回更新后的父级子版本信息
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create conversation")

    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.putconn(conn)

# # 查询会话的接口
# @app.get("/sessions", response_model=List[dict])
# def get_sessions_by_user_id(
#     user_id: int,
#     current_user: UserInDB = Depends(get_current_user)
# ):
#     # 验证 user_id 和当前用户是否一致
#     if current_user.user_id != user_id:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="User ID does not match the authenticated user's ID",
#         )
    
#     conn = None
#     try:
#         # 获取数据库连接
#         conn = get_db_connection()
#         with conn.cursor() as cur:
#             # 查询指定 user_id 的会话信息
#             query = """
#             SELECT session_id, session_name, start_time, end_time
#             FROM sessions
#             WHERE user_id = %s
#             ORDER BY session_id ASC
#             """
#             cur.execute(query, (user_id,))

#             # 获取查询结果
#             rows = cur.fetchall()
#             if not rows:
#                 return []

#             # 构造返回结果，并查找每个 session_id 对应的 session_desc
#             sessions = []
#             for row in rows:
#                 session_id = row[0]
#                 session_name = row[1]
#                 start_time = row[2]
#                 end_time = row[3]

#                 # 查找 conversations 表中该 session_id 最早的 response_from_model
#                 desc_query = """
#                 SELECT response_from_model
#                 FROM conversations
#                 WHERE session_id = %s
#                 ORDER BY created_at ASC
#                 LIMIT 1
#                 """
#                 cur.execute(desc_query, (session_id,))
#                 desc_result = cur.fetchone()

#                 # 如果存在最早的 response_from_model，则作为 session_desc
#                 session_desc = desc_result[0] if desc_result else None

#                 # 添加到结果列表
#                 sessions.append({
#                     "session_id": session_id,
#                     "session_name": session_name,
#                     "start_time": start_time,
#                     "end_time": end_time,
#                     "session_desc": session_desc
#                 })

#             return sessions

#     except Exception as e:
#         logger.error(f"Error querying sessions for user_id {user_id}: {e}")
#         raise HTTPException(status_code=500, detail="Internal server error")

#     finally:
#         if conn:
#             db_pool.putconn(conn)


# # 查询对话的接口
# @app.get("/conversations/{session_id}", response_model=List[ConversationResponse])
# async def get_conversations(
#     session_id: int,
#     user_id: int,
#     current_user: int = Depends(get_current_user),
#     db=Depends(get_db_connection)
# ):
#     logger.info("User %s is querying conversations for session_id: %s", user_id, session_id)
#     # 验证请求中的 user_id 是否与当前登录的用户一致
#     if current_user.user_id != user_id:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="User ID does not match the authenticated user's ID",
#         )

#     # 查询 session_id 对应的 user_id
#     session_check_query = """
#     SELECT user_id FROM sessions WHERE session_id = %s
#     """
#     conn = None
#     try:
#         conn = db  # 获取数据库连接
#         cur = conn.cursor()  # 创建游标对象

#         # 执行查询，检查 session_id 是否存在，以及它对应的 user_id
#         cur.execute(session_check_query, (session_id,))
#         result = cur.fetchone()

#         # 如果查询不到 session_id，返回空
#         if not result:
#             return []
#         session_user_id = result[0]  # 获取查询到的 user_id

#         # 比对 session_id 对应的 user_id 和 请求的 user_id 是否一致
#         if session_user_id != user_id:
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 detail="You do not have permission to access this session."
#             )

#         # 如果 session_id 和 user_id 匹配，查询会话内容
#         query = """
#         SELECT 
#             conversation_id::text, session_id, created_at, 
#             user_message, response_from_model,
#             dify_func_def, dify_func_des, dify_mod_des, 
#             dify_code, dify_id, preview_code
#         FROM conversations
#         WHERE session_id = %s
#         ORDER BY created_at ASC
#         """

#         cur.execute(query, (session_id,))  # 执行查询
#         rows = cur.fetchall()  # 获取所有查询结果

#         if not rows:
#             return []

#         # 转换查询结果为 Pydantic 模型列表
#         conversations = [
#             ConversationResponse(
#                 conversation_id=row[0],
#                 session_id=row[1],
#                 created_at=row[2],
#                 user_message=row[3],
#                 response_from_model=row[4],
#                 dify_func_def=row[5],
#                 dify_func_des=row[6], 
#                 dify_mod_des=row[7],  
#                 dify_code=row[8],   
#                 dify_id=row[9],      
#                 preview_code=row[10]
#             )
#             for row in rows
#         ]

#         return conversations
    
#     except HTTPException as http_exc:
#         # 捕获并抛出自定义的 HTTP 错误
#         raise http_exc

#     except Exception as e:
#         logger.error(f"Error querying conversations: {e}")
#         raise HTTPException(status_code=500, detail="Internal server error")

#     finally:
#         if cur:
#             cur.close()  # 关闭游标
#         if conn:
#             db_pool.putconn(conn)  # 将连接放回连接池

@app.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    user_id: int,
    current_user: UserInDB = Depends(get_current_user)
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
                detail="You do not have permission to delete this session."
            )

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
        logger.info(f"Session {session_id} and its conversations deleted for user {user_id}")
        return {"message": "Session and its conversations deleted successfully"}

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
    current_user: UserInDB = Depends(get_current_user)
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
                detail="You do not have permission to update this session."
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
        logger.info(f"Session {request.session_id} name updated to '{request.name}' by user {current_user.user_id}")
        return {"message": "Session name updated successfully"}

    except HTTPException as http_exc:
        # 捕获并抛出自定义的 HTTP 错误
        raise http_exc

    except Exception as e:
        logger.error(f"Error updating session name for session_id {request.session_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        if cur:
            cur.close()  # 关闭游标
        if conn:
            db_pool.putconn(conn)  # 将连接放回连接池