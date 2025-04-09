from typing import List
from api.utils.db import get_b_db_connection
from psycopg.rows import dict_row

def fetch_graph_data(type: List[str]) -> dict:
    conn = get_b_db_connection()
    cur = conn.cursor(row_factory=dict_row)
    
    try:
        nodes = []
        edges = []

        if not type:
            type = ["usecase", "userstory", "requirement"]

        if "usecase" in type:
            cur.execute("SELECT uc_id, uuid, name, description FROM usecase")
            usecases = cur.fetchall()
            for usecase in usecases:
                nodes.append({
                    "id": f"UC-{str(usecase['uc_id']).zfill(6)}",
                    "uuid": usecase['uuid'],
                    "label": usecase['name'],
                    "type": "node",
                    "name": usecase['name'],
                    "description": usecase['description'],
                    "tags": []
                })

        if "userstory" in type:
            cur.execute("SELECT us_id, uuid, uuid_uc, description FROM userstory")
            userstories = cur.fetchall()
            for userstory in userstories:
                nodes.append({
                    "id": f"US-{str(userstory['us_id']).zfill(6)}",
                    "uuid": userstory['uuid'],
                    "label": f"US-{str(userstory['us_id']).zfill(6)}",
                    "type": "node",
                    "name": f"US-{str(userstory['us_id']).zfill(6)}",
                    "description": userstory['description'],
                    "tags": []
                })
            if "usecase" in type and "userstory" in type:
                for userstory in userstories:
                    if userstory['uuid_uc']:
                        edges.append({
                            "uuid": f"{userstory['uuid']}+{userstory['uuid_uc']}",
                            "source": userstory['uuid_uc'],
                            "target": userstory['uuid'],
                            "type": "edges",
                            "label": "Aggregation"
                        })

        if "requirement" in type:
            cur.execute(""" 
                SELECT 
                    r.requirement_id,
                    r.uuid AS requirement_uuid,
                    r.name AS requirement_name,
                    r.description AS requirement_description,
                    uc.uuid AS uuid_uc
                FROM requirement r
                LEFT JOIN req_uc_relations ruc ON r.requirement_id = ruc.requirement_id
                LEFT JOIN usecase uc ON ruc.uc_id = uc.uc_id
            """)
            requirements = cur.fetchall()
            for requirement in requirements:
                nodes.append({
                    "id": f"REQ-{str(requirement['requirement_id']).zfill(6)}",
                    "uuid": requirement['requirement_uuid'],
                    "label": requirement['requirement_name'],
                    "type": "node",
                    "name": requirement['requirement_name'],
                    "description": requirement['requirement_description'],
                    "tags": []
                })
            if "usecase" in type and "requirement" in type:
                for requirement in requirements:
                    if requirement['uuid_uc']:
                        edges.append({
                            "uuid": f"{requirement['uuid_uc']}+{requirement['requirement_uuid']}",
                            "source": requirement['requirement_uuid'],
                            "target": requirement['uuid_uc'],
                            "type": "edges",
                            "label": "Aggregation"
                        })

        return {"nodes": nodes, "edges": edges}

    finally:
        cur.close()
        conn.close()
