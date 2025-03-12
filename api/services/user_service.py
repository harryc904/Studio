from fastapi import HTTPException, status
from typing import Optional

from api.utils.db import get_db_connection
from api.schemas.user import User
from api.config import logger

# 根据用户ID获取用户信息
async def get_user_by_id_service(user_id: int) -> Optional[User]:
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id, user_name, email, phone_number FROM users WHERE user_id = %s",
                (user_id,),
            )
            result = cur.fetchone()
            
            if result:
                return User(
                    user_id=result[0],
                    username=result[1],
                    email=result[2],
                    phone_number=result[3],
                )
            return None
    except Exception as e:
        logger.error(f"Error fetching user by ID {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        if conn:
            conn.close()

# 更新用户信息
async def update_user_service(user_id: int, update_data: dict) -> User:
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 构建更新语句
            update_fields = []
            params = []
            
            if 'username' in update_data:
                update_fields.append("user_name = %s")
                params.append(update_data['username'])
                
            if 'email' in update_data:
                update_fields.append("email = %s")
                params.append(update_data['email'])
                
            if 'phone_number' in update_data:
                update_fields.append("phone_number = %s")
                params.append(update_data['phone_number'])
            
            if not update_fields:
                raise HTTPException(status_code=400, detail="No fields to update")
            
            # 添加用户ID到参数列表
            params.append(user_id)
            
            # 执行更新
            query = f"UPDATE users SET {', '.join(update_fields)} WHERE user_id = %s RETURNING user_id, user_name, email, phone_number"
            cur.execute(query, params)
            conn.commit()
            
            result = cur.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="User not found")
                
            return User(
                user_id=result[0],
                username=result[1],
                email=result[2],
                phone_number=result[3],
            )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        if conn:
            conn.close()