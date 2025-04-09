import json
from api.schemas.standard import Standard
from fastapi import HTTPException
from api.utils.db import get_b_db_connection

# 检查 standard_id 是否已存在
def is_standard_id_exists(sanitized_standard_id: str) -> bool:
    try:
        conn = get_b_db_connection()
        cursor = conn.cursor()

        # 查询去除空格后的 standard_id 是否已存在
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM standards
            WHERE REPLACE(standard_id, ' ', '') = %s
            """,
            (sanitized_standard_id,)
        )
        result = cursor.fetchone()[0] > 0
    except Exception as e:
        raise e
    finally:
        cursor.close()
        conn.close()

    return result

# 插入标准信息
def insert_standard_data(standard: Standard):
    try:
        conn = get_b_db_connection()
        cursor = conn.cursor()

        # 插入标准信息
        cursor.execute(
            """
            INSERT INTO standards (standard_id, document_name, document_name_english, scope)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (standard.standardID, standard.documentName, standard.documentNameEnglish, standard.scope)
        )
        standard_id = cursor.fetchone()[0]

        # 插入术语信息
        term_values = [
            (
                standard_id,
                term.termID,
                term.term,
                term.termEnglish,
                term.definition,
                json.dumps([{"ID": note.ID, "content": note.content} for note in term.notes])  # 转换为 JSON 格式
            )
            for term in standard.terms
        ]

        # 批量插入术语信息
        cursor.executemany(
            """
            INSERT INTO terms (standard_id, term_id, term, term_english, definition, notes)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb)
            """,
            term_values
        )

        # 提交事务
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

# Function to get standards from the database
def get_standards_from_db(terms: int):
    try:
        conn = get_b_db_connection()
        cursor = conn.cursor()
        
        # Base query to get standards
        query = """
            SELECT standard_id, document_name, document_name_english, scope
            FROM standards
        """

        # Query for terms if terms == 1
        if terms == 1:
            query = """
                SELECT s.standard_id, s.document_name, s.document_name_english, s.scope, 
                       t.term_id, t.term, t.term_english, t.definition, t.notes
                FROM standards s
                LEFT JOIN terms t ON s.id = t.standard_id
            """
        
        cursor.execute(query)
        rows = cursor.fetchall()

        standards = {}

        for row in rows:
            standard_id = row['standard_id']
            
            if standard_id not in standards:
                standards[standard_id] = {
                    "standardID": row['standard_id'],
                    "documentName": row['document_name'],
                    "documentNameEnglish": row['document_name_english'],
                    "scope": row['scope'],
                    "terms": []
                }
            
            if terms == 1:
                # Add terms to standard
                if row['term_id']:
                    terms_data = {
                        "termID": row['term_id'],
                        "term": row['term'],
                        "termEnglish": row['term_english'],
                        "definition": row['definition'],
                        "notes": row['notes'] if row['notes'] else []
                    }
                    standards[standard_id]['terms'].append(terms_data)
        
        # Convert the standards dict to a list for the response
        result = list(standards.values())
        
        return result

    except Exception as e:
        print(f"Error: {e}")
        return []

    finally:
        # Ensure the connection is closed even if an error occurs
        if conn:
            conn.close()