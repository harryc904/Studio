from psycopg_pool import ConnectionPool
from fastapi import HTTPException
import logging

from ..config import DB_CONNECTION_STRING, DB_MIN_CONNECTIONS, DB_MAX_CONNECTIONS

# 初始化日志记录器
logger = logging.getLogger(__name__)

# 创建数据库连接池
db_pool = ConnectionPool(
    conninfo=DB_CONNECTION_STRING,
    min_size=DB_MIN_CONNECTIONS,
    max_size=DB_MAX_CONNECTIONS,
)

# 获取数据库连接
def get_db_connection():
    if db_pool:
        try:
            conn = db_pool.getconn()
            if conn.closed:
                conn = db_pool.getconn()
            return conn
        except Exception as e:
            logger.error(f"Error getting database connection: {e}")
            raise HTTPException(status_code=500, detail="Database connection error")
    else:
        raise HTTPException(
            status_code=500, detail="Database connection pool not initialized"
        )