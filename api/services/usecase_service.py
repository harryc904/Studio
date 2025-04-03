from api.schemas.usecase import UseCase, UserStory
from api.utils.db import get_b_db_connection
from fastapi import HTTPException
import psycopg2
from psycopg2.extras import RealDictCursor
from api.config import DATABASE_CONFIG

def get_all_ucus():
    try:
        conn = get_b_db_connection()
        cursor = conn.cursor()

        # 查询所有用例（usecase）和用户故事（userstory）
        cursor.execute("""
            SELECT uc.uc_id, uc.name AS usecase_name, uc.description AS usecase_description,
                   us.us_id, us.description AS userstory_description
            FROM usecase uc
            LEFT JOIN userstory us ON us.uc_id = uc.uc_id
            ORDER BY uc.uc_id, us.us_id
        """)

        result = cursor.fetchall()

        # 将查询结果按照 UseCase 和 UserStory 的层级结构组织
        usecases = {}
        for row in result:
            uc_id = row[0]

            if uc_id not in usecases:
                # 格式化 uc_id 为 UC + 六位数字
                formatted_uc_id = f"UC-{uc_id:06}"
                usecases[uc_id] = {
                    "id": formatted_uc_id,  # 使用格式化后的 id
                    "name": row[1],
                    "description": row[2],
                    "userstories": []
                }

            # 如果有 userstory，添加到对应的 usecase 中
            if row[3] is not None:  # 如果存在 userstory
                # 格式化 us_id 为 US + 六位数字
                formatted_us_id = f"US-{row[3]:06}"
                usecases[uc_id]["userstories"].append({
                    "id": formatted_us_id,  # 使用格式化后的 id
                    "description": row[4]
                })

        # 将结构转换为对应的 Pydantic 模型格式并返回
        return [
            UseCase(
                id=uc["id"],
                name=uc["name"],
                description=uc["description"],
                userstories=[
                    UserStory(
                        id=us["id"],
                        description=us["description"]
                    ) for us in uc["userstories"]
                ]
            ) for uc in usecases.values()
        ]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

async def get_details(id: str, uuid: str):
    conn = get_b_db_connection()  # 使用 get_b_db_connection
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 判断查询的是哪个表，通过id前缀判断
        if id.startswith("UC-"):
            # 查询 usecase 表
            cur.execute("""
                SELECT 
                    uc_id, name, description, system, primary_actor, secondary_actor, 
                    precondition, success_end_condition, failed_end_condition, 
                    main_success_scenario, extensions AS extension_scenario, 
                    io_variations AS IO_variations,
                    uc_appendix_id, uuid, created_time, created_by, modified_time, modified_by 
                FROM usecase 
                WHERE uuid = %s
            """, (uuid,))
            data = cur.fetchone()

            if data is None:
                raise HTTPException(status_code=404, detail="Usecase not found")

            # 返回查询到的数据
            return {
                "uc_id": f"UC-{str(data['uc_id']).zfill(6)}",
                "name": data['name'],
                "description": data['description'],
                "system": data['system'],
                "primary_actor": data['primary_actor'],
                "secondary_actor": data['secondary_actor'],
                "precondition": data['precondition'],
                "success_end_condition": data['success_end_condition'],
                "failed_end_condition": data['failed_end_condition'],
                "uc_appendix_id": data['uc_appendix_id'],
                "uuid": data['uuid'],
                "created_time": data['created_time'],
                "created_by": data['created_by'],
                "modified_time": data['modified_time'],
                "modified_by": data['modified_by']
            }

        elif id.startswith("US-"):
            # 查询 userstory 表
            cur.execute("""
                SELECT 
                    us_id, description, uc_id, status_id, user_journey_id, 
                    acceptance_criteria, valid_vehicle, uuid, uuid_uc, 
                    created_time, created_by, modified_time, modified_by
                FROM userstory 
                WHERE uuid = %s
            """, (uuid,))
            data = cur.fetchone()

            if data is None:
                raise HTTPException(status_code=404, detail="Userstory not found")

            # 查询 status 表，获取 status_name
            cur.execute("SELECT status_name FROM status WHERE status_id = %s", (data['status_id'],))
            status = cur.fetchone()
            status_name = status['status_name'] if status else None

            # 查询 userjourney 表，获取 user_journey_name
            cur.execute("SELECT name AS user_journey_name FROM userjourney WHERE user_journey_id = %s", (data['user_journey_id'],))
            user_journey = cur.fetchone()
            user_journey_name = user_journey['user_journey_name'] if user_journey else None

            # 返回查询到的数据
            return {
                "us_id": f"US-{str(data['us_id']).zfill(6)}", 
                "description": data['description'],
                "uc_id": f"UC-{str(data['uc_id']).zfill(6)}" if data['uc_id'] else None, 
                "status_id": data['status_id'],
                "status_name": status_name,
                "user_journey_id": data['user_journey_id'],
                "user_journey_name": user_journey_name,
                "acceptance_criteria": data['acceptance_criteria'],
                "valid_vehicle": data['valid_vehicle'],
                "uuid": data['uuid'],
                "uuid_uc": data['uuid_uc'],
                "created_time": data['created_time'],
                "created_by": data['created_by'],
                "modified_time": data['modified_time'],
                "modified_by": data['modified_by']
            }

        elif id.startswith("REQ-"):
            # 查询 requirement 表
            cur.execute("""
                SELECT 
                    requirement_id, name, description, requirement_type, standard_id, source, 
                    purpose, verification_method, uuid, asil, created_time, created_by, 
                    modified_time, modified_by 
                FROM requirement 
                WHERE uuid = %s
            """, (uuid,))
            data = cur.fetchone()

            if data is None:
                raise HTTPException(status_code=404, detail="Requirement not found")

            # 查询 req_uc_relations 表，获取 uc_id
            cur.execute("SELECT uc_id FROM req_uc_relations WHERE requirement_id = %s", (data['requirement_id'],))
            uc_relation = cur.fetchone()
            uc_id = uc_relation['uc_id'] if uc_relation else None

            # 返回查询到的数据
            return {
                "requirement_id": f"REQ-{str(data['requirement_id']).zfill(6)}",
                "name": data['name'],
                "description": data['description'],
                "requirement_type": data['requirement_type'],
                "ASIL": data['asil'],
                "uc_id": f"UC-{str(uc_id).zfill(6)}" if uc_id else None,
                "standard_id": data['standard_id'],
                "source": data['source'],
                "purpose": data['purpose'],
                "verification_method": data['verification_method'],
                "uuid": data['uuid'],
                "created_time": data['created_time'],
                "created_by": data['created_by'],
                "modified_time": data['modified_time'],
                "modified_by": data['modified_by']
            }

        else:
            raise HTTPException(status_code=400, detail="Invalid ID format")

    except HTTPException as e:
        # 捕获 HTTP 异常并返回对应的错误信息
        raise e
    except Exception as e:
        # 捕获所有其他类型的异常，返回 500 错误
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        cur.close()
        conn.close()
