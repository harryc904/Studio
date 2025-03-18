from fastapi import HTTPException, status
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import json

from api.utils.db import get_db_connection
from api.schemas.conversation import ConversationCreateRequest, ConversationResponse, PrdResponse
from api.schemas.user import UserInDB
from api.utils.logger import get_logger

logger = get_logger(__name__)


# 创建对话服务
async def create_conversation_service(request: ConversationCreateRequest, current_user: UserInDB) -> ConversationResponse:
    conn = None
    created_at = datetime.now()  # 获取当前时间
    try:
        # 获取数据库连接
        conn = get_db_connection()
        cur = conn.cursor()  # 创建一个游标

        # 处理可选字段的默认值
        conversation_id = str(request.conversation_id or uuid.uuid4())  # 转换 UUID 为字符串
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
                conversation_child_version = json.dumps(child_versions)  # 将字典转换回 JSON 字符串
                logger.info("Updated conversation_child_version: %s", conversation_child_version)

                # 更新父级 conversation 的 conversation_child_version
                cur.execute(
                    "UPDATE conversations SET conversation_child_version = %s WHERE conversation_id = %s",
                    (conversation_child_version, str(request.conversation_parent_id)),  # 转换 UUID 为字符串
                )
                logger.info("Updated parent conversation's child version in the database")

        # 插入对话内容到 conversations 表
        insert_query = """ 
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
        """

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
                str(request.conversation_parent_id) if request.conversation_parent_id else None,  # 转换 UUID 为字符串
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
            insert_prd_query = """ 
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
            """

            # 如果前端传入 restore_version，使用传入值，否则为 NULL
            restore_version_value = request.restore_version if request.restore_version is not None else None

            # 插入数据到 prd 表
            cur.execute(
                insert_prd_query,
                (
                    new_prd_version,  # 计算出的新版本号
                    conversation_id,  # 关联的conversation_id
                    request.session_id,  # 关联的session_id
                    request.prd_content,  # PRD的内容
                    current_user.username,  # 创建人
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
            # 构建响应对象
            return ConversationResponse(
                conversation_id=str(result[0]),  # 转换 UUID 为字符串
                session_id=result[1],
                created_at=result[2],
                conversation_type=result[3],
                content=result[4],
                version=result[5],
                conversation_parent_id=result[6],
                conversation_para_version=json.loads(conversation_child_version) if conversation_child_version else None,  # 将字符串转换为字典
                knowledge_graph=result[8],
                dify_func_des=result[9],
                knowledge_id=result[10],
                dify_id=result[11],
                preview_code=result[12],
                prd_version=prd_version,  # 返回 PRD 的版本号
                prd_content=prd_content,  # 返回 PRD 的内容
                latest=latest,
                restore_version=restore_version,
            )
        else:
            logger.error("Failed to fetch insert result")
            raise HTTPException(status_code=500, detail="Failed to create conversation")

    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            conn.close()

# 获取对话服务
async def get_conversations_service(
    session_id: int,
    user_id: int,
    conversation_id: Optional[str],
    current_user: UserInDB
) -> List[ConversationResponse]:
    conn = None

    try:
        # 获取数据库连接
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 查询 session_id 对应的 user_id
            logger.info("Checking session_id %s for user_id %s", session_id, user_id)
            cur.execute("SELECT user_id FROM sessions WHERE session_id = %s", (session_id,))
            result = cur.fetchone()

            # 如果查询不到 session_id，返回空
            if not result:
                logger.warning("Session ID %s not found", session_id)
                return []
            session_user_id = result[0]  # 获取查询到的 user_id

            # 比对 session_id 对应的 user_id 和 请求的 user_id 是否一致
            if session_user_id != user_id:
                logger.warning("Session user_id %s does not match request user_id %s", session_user_id, user_id)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to access this session."
                )
    
            # 如果传递了 conversation_id，通过 conversation_child_version 找到链路的起始点
            if conversation_id:
                while True:
                    cur.execute("""
                        SELECT conversation_id
                        FROM conversations
                        WHERE conversation_parent_id = %s
                        ORDER BY version DESC
                        LIMIT 1
                    """, (conversation_id,))
                    next_conversation = cur.fetchone()
                    if next_conversation:
                        # 如果找到下一个版本，继续查找
                        conversation_id = next_conversation[0]
                    else:
                        # 没有下一个版本，则停止
                        break
            else:
                # 如果没有传递 conversation_id，查询 session_id 下最新的 conversation_id
                cur.execute("""
                    SELECT conversation_id
                    FROM conversations
                    WHERE session_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (session_id,))
                latest_conversation = cur.fetchone()
                if latest_conversation:
                    conversation_id = latest_conversation[0]
                    logger.info("Latest conversation_id for session_id %s is %s", session_id, conversation_id)
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
                cur.execute("""
                    SELECT conversation_id, session_id, created_at, conversation_type, content, version,
                           conversation_parent_id, conversation_child_version, knowledge_graph, dify_func_des,
                           knowledge_id, dify_id, preview_code
                    FROM conversations
                    WHERE conversation_id = %s
                """, (current_id,))
                conversation_data = cur.fetchone()

                if conversation_data:
                    # 查询 prd_content 和 prd_version（如果有的话）
                    prd_content = None
                    prd_version = None
                    latest = None
                    restore_version = None                    
                    cur.execute(""" 
                        SELECT prd_content, prd_version, latest, restore_version
                        FROM prd
                        WHERE session_id = %s AND conversation_id = %s
                        ORDER BY prd_version DESC
                        LIMIT 1
                    """, (session_id, current_id))
                    prd_result = cur.fetchone()

                    if prd_result:
                        prd_content, prd_version, latest, restore_version = prd_result     
                                       
                    # 如果存在父级对话，获取父级的conversation_child_version
                    conversation_para_version = None
                    if conversation_data[6]:  # conversation_parent_id
                        parent_id = conversation_data[6]
                        cur.execute("""
                            SELECT conversation_child_version
                            FROM conversations
                            WHERE conversation_id = %s
                        """, (parent_id,))
                        parent_data = cur.fetchone()
                        if parent_data and parent_data[0]:
                            # 确保父级的conversation_child_version是字典类型
                            if isinstance(parent_data[0], str):
                                try:
                                    conversation_para_version = json.loads(parent_data[0])
                                except json.JSONDecodeError:
                                    logger.warning("Failed to decode JSON for parent_id %s", parent_id)
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
                        preview_code=conversation_data[12]
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
            conn.close()

# 获取PRD
async def get_prd_service(user_id: int) -> PrdResponse:
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
            return PrdResponse(prd_content=prd_content_record[0])

    except HTTPException as e:
        # 捕获并抛出 HTTP 异常
        raise e

    except Exception as e:
        logger.error(f"Error retrieving PRD: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        if conn:
            conn.close()