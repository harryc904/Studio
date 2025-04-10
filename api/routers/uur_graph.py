from fastapi import APIRouter, Query, HTTPException
from typing import List
from api.services.uur_graph import fetch_graph_data, fetch_user_story_table

router = APIRouter()

@router.get("/uur_graph_query", response_model=dict)
async def uur_graph_query(type: List[str] = Query(None, enum=["usecase", "userstory", "requirement"])):
    try:
        return fetch_graph_data(type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get_us_table", response_model=list)
async def get_us_table():
    try:
        return fetch_user_story_table()
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")