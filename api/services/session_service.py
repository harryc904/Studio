from fastapi import HTTPException, status
from typing import List
from datetime import datetime

from api.utils.db import get_db_connection
from api.schemas.session import SessionCreateRequest, SessionResponse, UpdateSessionNameRequest
from api.utils.logger import get_logger

logger = get_logger(__name__)


# 创建会话服务
async def create_session_service(request: SessionCreateRequest) -> SessionResponse:
    conn = None
    try:
        # 获取数据库连接
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 获取当前时间作为 start_time 和 end_time
            start_time = datetime.now()
            end_time = datetime.now()
            # 如果 session_name 没有传入，则生成默认的名称
            session_name = (
                request.session_name
                if request.session_name
                else start_time.strftime("%Y%m%d%H%M%S")
            )

            # 插入新的会话数据到 sessions 表
            insert_query = """
                INSERT INTO sessions (user_id, session_name, start_time, end_time)
                VALUES (%s, %s, %s, %s)
                RETURNING session_id, user_id, session_name, start_time, end_time;
            """
            cur.execute(insert_query, (request.user_id, session_name, start_time, end_time))

            # 提交事务
            conn.commit()

            # 获取插入的会话数据
            result = cur.fetchone()
            if result:
                return SessionResponse(
                    session_id=result[0],
                    user_id=result[1],
                    session_name=result[2],
                    start_time=result[3],
                    end_time=result[4]
                )
            else:
                raise HTTPException(status_code=500, detail="Failed to create session")

    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            conn.close()

# 获取用户所有会话服务
async def get_user_sessions_service(user_id: int) -> List[SessionResponse]:
    conn = None
    try:
        # 获取数据库连接
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 查询用户的所有会话
            query = """
                SELECT session_id, user_id, session_name, start_time, end_time
                FROM sessions
                WHERE user_id = %s
                ORDER BY start_time DESC;
            """
            cur.execute(query, (user_id,))
            
            # 获取查询结果
            results = cur.fetchall()
            
            # 转换为响应模型列表
            sessions = []
            for row in results:
                sessions.append(SessionResponse(
                    session_id=row[0],
                    user_id=row[1],
                    session_name=row[2],
                    start_time=row[3],
                    end_time=row[4]
                ))
            
            return sessions

    except Exception as e:
        logger.error(f"Error fetching sessions for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            conn.close()

# 更新会话名称服务
async def update_session_name_service(request: UpdateSessionNameRequest) -> SessionResponse:
    conn = None
    try:
        # 获取数据库连接
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 验证会话是否存在且属于该用户
            cur.execute(
                "SELECT session_id FROM sessions WHERE session_id = %s AND user_id = %s",
                (request.session_id, request.user_id)
            )
            if not cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found or does not belong to the user"
                )
            
            # 更新会话名称
            update_query = """
                UPDATE sessions
                SET session_name = %s
                WHERE session_id = %s
                RETURNING session_id, user_id, session_name, start_time, end_time;
            """
            cur.execute(update_query, (request.name, request.session_id))
            conn.commit()
            
            # 获取更新后的会话数据
            result = cur.fetchone()
            if result:
                return SessionResponse(
                    session_id=result[0],
                    user_id=result[1],
                    session_name=result[2],
                    start_time=result[3],
                    end_time=result[4]
                )
            else:
                raise HTTPException(status_code=500, detail="Failed to update session name")

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error updating session name: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            conn.close()

# 删除会话服务
async def delete_session_service(session_id: int, user_id: int):
    conn = None
    try:
        # 获取数据库连接
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 首先检查 session 是否存在，并且属于当前用户
            session_check_query = """
            SELECT user_id FROM sessions WHERE session_id = %s
            """
            cur.execute(session_check_query, (session_id,))
            result = cur.fetchone()

            if not result:
                logger.error(f"Session {session_id} not found.")
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

            # 确认 session 属于请求的 user_id
            session_user_id = result[0]
            if session_user_id != user_id:
                logger.error(f"User {user_id} does not have permission to delete session {session_id}.")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to delete this session."
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
            logger.info(f"Session {session_id} and its conversations, prd records deleted for user {user_id}")
            return {"message": "Session and its conversations, prd records deleted successfully"}

    except HTTPException as http_exc:
        # 捕获并抛出自定义的 HTTP 错误
        raise http_exc

    except Exception as e:
        logger.error(f"Error deleting session {session_id} for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        if conn:
            conn.close()  # 关闭连接