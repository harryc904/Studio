from api.schemas.usecase import UseCase, UserStory
from api.utils.db import get_b_db_connection
from fastapi import HTTPException
import psycopg2
from psycopg2.extras import RealDictCursor
from api.schemas.usecase import PRDData
import logging

logger = logging.getLogger(__name__)

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

async def get_us_table_service():
    conn = get_b_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT 
                us.us_id, 
                us.description, 
                s.status_name, 
                uj.name AS user_journey_name, 
                us.valid_vehicle, 
                us.uuid
            FROM userstory us
            LEFT JOIN status s ON us.status_id = s.status_id
            LEFT JOIN userjourney uj ON us.user_journey_id = uj.user_journey_id
        """)
        userstories = cur.fetchall()

        result = [
            {
                "us_id": f"US-{str(us['us_id']).zfill(6)}",
                "description": us["description"],
                "status_name": us["status_name"],
                "user_journey_name": us["user_journey_name"],
                "valid_vehicle": us["valid_vehicle"],
                "uuid": us["uuid"]
            }
            for us in userstories
        ]

        return result

    except Exception as e:
        raise e

    finally:
        cur.close()
        conn.close()
# 校验并获取或创建 user_journey_id
def get_or_create_user_journey(cur, name: str):
    query = "SELECT user_journey_id FROM userjourney WHERE name = %s"
    cur.execute(query, (name,))
    result = cur.fetchone()
    if result:
        return result["user_journey_id"]
    else:
        query = "INSERT INTO userjourney (name) VALUES (%s) RETURNING user_journey_id"
        cur.execute(query, (name,))
        return cur.fetchone()["user_journey_id"]

# 校验并获取或创建 status_id
def get_or_create_status(cur, status_name: str):
    query = "SELECT status_id FROM status WHERE status_name = %s"
    cur.execute(query, (status_name,))
    result = cur.fetchone()
    if result:
        return result["status_id"]
    else:
        query = "INSERT INTO status (status_name) VALUES (%s) RETURNING status_id"
        cur.execute(query, (status_name,))
        return cur.fetchone()["status_id"]

# 校验并获取或创建 stakeholder_id
def get_or_create_stakeholder(cur, name: str):
    query = "SELECT stakeholder_id FROM stakeholder WHERE name = %s"
    cur.execute(query, (name,))
    result = cur.fetchone()
    if result:
        return result["stakeholder_id"]
    else:
        query = "INSERT INTO stakeholder (name) VALUES (%s) RETURNING stakeholder_id"
        cur.execute(query, (name,))
        return cur.fetchone()["stakeholder_id"]

# 校验并获取或创建 interest_id
def get_or_create_interest(cur, description: str):
    query = "SELECT interest_id FROM interest WHERE description = %s"
    cur.execute(query, (description,))
    result = cur.fetchone()
    if result:
        return result["interest_id"]
    else:
        query = "INSERT INTO interest (description) VALUES (%s) RETURNING interest_id"
        cur.execute(query, (description,))
        return cur.fetchone()["interest_id"]

def get_or_create_standard(cur, standard_id: str, document_name: str):
    # 检查是否已存在
    query = "SELECT id FROM standards WHERE standard_id = %s"
    cur.execute(query, (standard_id,))
    result = cur.fetchone()
    
    if result:
        return result["id"]
    else:
        # 插入新记录
        query = "INSERT INTO standards (standard_id, document_name) VALUES (%s, %s) RETURNING id"
        cur.execute(query, (standard_id, document_name))
        return cur.fetchone()["id"]

async def process_prd_data_service(data: PRDData):
    conn = get_b_db_connection()
    cur = conn.cursor()

    try:
        # Step 1: Get or create user_journey_id
        user_journey_name = data.chapters[0]["sections"][0]["subsections"][0]["verticalHeaderTable"][0]["userJourney"]
        user_journey_id = get_or_create_user_journey(cur, user_journey_name)
        logger.debug(f"Step 1 - User Journey ID: {user_journey_id}")

        # Step 2: Get or create status_id
        status_name = None
        for item in data.chapters[0]["sections"][0]["subsections"][0]["verticalHeaderTable"]:
            if isinstance(item, dict) and "status" in item:
                status_name = item["status"]
                break
        
        if not status_name:
            raise HTTPException(status_code=400, detail="'status' field is missing in verticalHeaderTable")
        
        status_id = get_or_create_status(cur, status_name)
        logger.debug(f"Step 2 - Status ID: {status_id}")

        # Step 3: Insert Appendix data into uc_appendix
        appendix_data = data.chapters[3]["sections"][0]["subsections"][0]["horizontalHeaderTable"]
        
        # Convert to a string (e.g., JSON format) for table_txt
        appendix_table_txt = str(appendix_data)  # You could also use JSON.stringify() or other formatting methods
        
        # Insert into uc_appendix
        query = """
        INSERT INTO uc_appendix (table_txt)
        VALUES (%s) RETURNING id
        """
        cur.execute(query, (appendix_table_txt,))
        uc_appendix_id = cur.fetchone()["id"]
        logger.debug(f"Step 3 - uc_appendix ID: {uc_appendix_id}")

        # Step 4: Process UseCase related data
        use_case_description = data.chapters[1]["sections"][1]["subsections"][0]["description"]
        use_case_overview = data.chapters[1]["sections"][1]["subsections"][0]["verticalHeaderTable"][0]["overview"]
        primary_actor = data.chapters[1]["sections"][1]["subsections"][0]["verticalHeaderTable"][3]["primaryActor"]
        secondary_actors = "\n".join(data.chapters[1]["sections"][1]["subsections"][0]["verticalHeaderTable"][4]["secondaryActors"])
        preconditions = "\n".join(data.chapters[1]["sections"][1]["subsections"][0]["verticalHeaderTable"][5]["preconditions"])
        success_end_conditions = "\n".join(data.chapters[1]["sections"][1]["subsections"][0]["verticalHeaderTable"][6]["successEndConditions"])
        fail_protection_conditions = "\n".join(data.chapters[1]["sections"][1]["subsections"][0]["verticalHeaderTable"][7]["failProtectionConditions"])
        main_success_scenario = data.chapters[1]["sections"][2]["subsections"][0]["horizontalHeaderTable"]
        main_success_scenario_str = str(main_success_scenario)  # Store as string, you can format it better if needed
        extensions_data = data.chapters[1]["sections"][3]["subsections"]
        extensions_str = str(extensions_data)  # Store as string, format as needed
        io_variations_data = data.chapters[1]["sections"][4]["subsections"]
        io_variations_str = str(io_variations_data)  # Store as string, format as needed

        # Insert into usecase table
        query = """
        INSERT INTO usecase (name, description, system, primary_actor, secondary_actor, precondition, success_end_condition, failed_end_condition, uc_appendix_id, main_success_scenario, extensions, io_variations)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING uc_id, uuid
        """
        cur.execute(query, (
            use_case_description, use_case_overview, "All_Vehicle", primary_actor, 
            secondary_actors, preconditions, success_end_conditions, fail_protection_conditions, uc_appendix_id, main_success_scenario_str, extensions_str, io_variations_str
        ))
        use_case = cur.fetchone()
        use_case_id = use_case["uc_id"]
        use_case_uuid = use_case["uuid"]
        logger.debug(f"Step 4 - Use Case ID: {use_case_id}; Use Case UUID: {use_case_uuid}")

        # Step 5: 提取 regulations 字段
        regulations = data.chapters[1]["sections"][1]["subsections"][0]["verticalHeaderTable"][2]["regulations"]
        # 解析 regulations
        for regulation in regulations:
            standard_id, document_name = regulation.split(" - ", 1)
            
            # 调用函数获取或创建 standard_id
            id = get_or_create_standard(cur, standard_id, document_name)

            # Insert into std_uc_relations
            query = """
            INSERT INTO std_uc_relations (standards_id, uc_id)
            VALUES (%s, %s)                
            """
            cur.execute(query, (id, use_case_id))
        logger.debug(f"Step 5 - std_uc_relations updated")

        # Step 6: Store UserStory data
        user_story_description = data.chapters[0]["sections"][0]["subsections"][0]["description"]
        
        # Ensure 'validVehicles' exists and handle the list properly
        valid_vehicles = []
        for item in data.chapters[0]["sections"][0]["subsections"][0]["verticalHeaderTable"]:
            if isinstance(item, dict) and "validVehicles" in item:
                valid_vehicles = item["validVehicles"]
                break
        
        if not valid_vehicles:
            raise HTTPException(status_code=400, detail="'validVehicles' field is missing or empty")

        valid_vehicles = "\n".join(valid_vehicles)  # Join valid vehicles if present

        # Process acceptance criteria
        acceptance_criteria = []
        for item in data.chapters[0]["sections"][0]["subsections"][0]["verticalHeaderTable"]:
            if isinstance(item, dict) and "acceptanceCriteria" in item:
                acceptance_criteria = item["acceptanceCriteria"]
                break
        
        if acceptance_criteria:
            # Modify this line to handle both strings and dictionaries in acceptanceCriteria
            acceptance_criteria = "\n".join([ac if isinstance(ac, str) else ac.get("description", "") for ac in acceptance_criteria])

        # Insert into userstory
        query = """
        INSERT INTO userstory (uc_id, uuid_uc, description, valid_vehicle, acceptance_criteria, status_id, user_journey_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING us_id
        """
        cur.execute(query, (use_case_id, use_case_uuid, user_story_description, valid_vehicles, acceptance_criteria, status_id, user_journey_id))
        user_story_id = cur.fetchone()["us_id"]
        logger.debug(f"Step 6 - User Story ID: {user_story_id}")

        # Step 7: Process Stakeholders and Interests
        stakeholders_and_interests = data.chapters[0]["sections"][0]["subsections"][0]["verticalHeaderTable"][1].get("stakeholders&Interests", [])

        for stakeholder_info in stakeholders_and_interests:
            if isinstance(stakeholder_info, str):  # Ensure it's a string
                stakeholder_name, interest_desc = stakeholder_info.split(" : ")
                # Get or create stakeholder and interest
                stakeholder_id = get_or_create_stakeholder(cur, stakeholder_name)
                interest_id = get_or_create_interest(cur, interest_desc)
                
                # Insert into sta_int_us_relations
                query = """
                INSERT INTO sta_int_us_relations (stakeholder_id, interest_id, us_id)
                VALUES (%s, %s, %s)
                """
                cur.execute(query, (stakeholder_id, interest_id, user_story_id))
        logger.debug(f"Step 7 - Stakeholders and Interests saved")  # Add debugging output

        # Step 8: Process Function Design Requirements
        function_design_requirements = data.chapters[2]["sections"][0]["subsections"][0]["horizontalHeaderTable"]

        for req in function_design_requirements:
            requirement_name = req["requirementName"]
            description = req["description"]
            requirement_type = req["requirementType"]
            asil = req["ASIL"]
            source = req["source"]

            # Insert into requirement table
            query = """
            INSERT INTO requirement (name, description, requirement_type, asil, source)
            VALUES (%s, %s, %s, %s, %s) RETURNING requirement_id
            """
            cur.execute(query, (requirement_name, description, requirement_type, asil, source))
            requirement_id = cur.fetchone()["requirement_id"]

            query = """
            INSERT INTO req_uc_relations (requirement_id, uc_id)
            VALUES (%s, %s)
            """
            cur.execute(query, (requirement_id, use_case_id))  # use_case_id from Step 4
        logger.debug(f"Step 8 - req_uc_relations updated")

        # Step 9: Commit all changes to the database
        conn.commit()  # Commit after all operations
        logger.debug("Step 9 - Data committed to the database.")

        return {"message": "Data successfully stored!"}

    except Exception as e:
        conn.rollback()  # Rollback on error
        logger.error(f"Error: {str(e)}")  # Print the error message
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cur.close()  # Close the cursor
        conn.close()  # Close the connection
        logger.debug("Database connection closed.")
