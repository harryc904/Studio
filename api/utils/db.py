from psycopg_pool import ConnectionPool
from fastapi import HTTPException
from api.utils.logger import get_logger
from api.config import (
    DB_CONNECTION_STRING, DB_MIN_CONNECTIONS, DB_MAX_CONNECTIONS,
    B_DB_CONNECTION_STRING, B_DB_MIN_CONNECTIONS, B_DB_MAX_CONNECTIONS
)

logger = get_logger(__name__)


# 创建主数据库连接池
db_pool = ConnectionPool(
    conninfo=DB_CONNECTION_STRING,
    min_size=DB_MIN_CONNECTIONS,
    max_size=DB_MAX_CONNECTIONS,
)

# 创建业务数据库连接池
b_db_pool = ConnectionPool(
    conninfo=B_DB_CONNECTION_STRING,
    min_size=B_DB_MIN_CONNECTIONS,
    max_size=B_DB_MAX_CONNECTIONS,
)

# 获取主数据库连接
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

# 释放主数据库连接
def put_db_connection(conn):
    if db_pool:
        db_pool.putconn(conn)

# 获取业务数据库连接
def get_b_db_connection():
    if b_db_pool:
        try:
            conn = b_db_pool.getconn()
            if conn.closed:
                conn = b_db_pool.getconn()
            return conn
        except Exception as e:
            logger.error(f"Error getting business database connection: {e}")
            raise HTTPException(status_code=500, detail="Business database connection error")
    else:
        raise HTTPException(
            status_code=500, detail="Business database connection pool not initialized"
        )

# 释放业务数据库连接
def put_b_db_connection(conn):
    if b_db_pool:
        b_db_pool.putconn(conn)