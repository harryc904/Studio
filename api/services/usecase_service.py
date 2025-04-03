from api.schemas.usecase import UseCase, UserStory
from api.utils.db import get_b_db_connection
from fastapi import HTTPException

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
