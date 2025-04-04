import psycopg2
import json
from psycopg2.extras import execute_values
from api.schemas.standard import Standard
from fastapi import HTTPException
from api.utils.db import get_b_db_connection
from typing import List
from psycopg2.extras import RealDictCursor
from api.schemas.standard import StandardResponse

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

        execute_values(
            cursor,
            """
            INSERT INTO terms (standard_id, term_id, term, term_english, definition, notes)
            VALUES %s
            """,
            term_values,
            template="(%s, %s, %s, %s, %s, %s::jsonb)"  # 确保使用 JSONB 类型
        )

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()
