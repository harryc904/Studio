from fastapi import HTTPException, status
from typing import List
from datetime import datetime

from api.utils.db import get_db_connection
from api.schemas.session import SessionCreateRequest, SessionResponse, UpdateSessionNameRequest
from api.config import logger

# 创建会话服务
async def create_session_service(request: SessionCreateRequest) -> SessionResponse:
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
            insert_query = """
                INSERT INTO sessions (user_id, session_name, start_time)
                VALUES (%s, %s, %s)
                RETURNING session_id, user_id, session_name, start_time, end_time;
            """
            cur.execute(insert_query, (request.user_id, session_name, start_time))

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