from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
import logging

# 导入路由模块
from api.routers import auth, sessions, conversations, users

# 导入配置
from api.config import (
    APP_TITLE,
    APP_DESCRIPTION,
    APP_VERSION,
    APP_DOCS_URL,
    APP_REDOC_URL
)

# 初始化 logging 配置
logging.basicConfig(level=logging.DEBUG)  # 日志基础配置
logger = logging.getLogger(__name__)  # 创建日志记录器

# 创建FastAPI应用实例，指定Swagger UI路径和Redoc路径
app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    docs_url=APP_DOCS_URL,
    redoc_url=APP_REDOC_URL,
    openapi_url="/openapi.json"
)


# 注册路由
app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(conversations.router)
app.include_router(users.router)

# 添加中间件来记录请求和响应
@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response status code: {response.status_code}")
    return response

# 自定义 OpenAPI 配置，让 Swagger UI 使用 Bearer Token
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=APP_TITLE,
        version=APP_VERSION,
        description=APP_DESCRIPTION,
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    }
    openapi_schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# 将自定义 OpenAPI 配置应用到 FastAPI 实例中
app.openapi = custom_openapi
