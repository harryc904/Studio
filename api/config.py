import os

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 主数据库配置
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_MIN_CONNECTIONS = int(os.getenv("DB_MIN_CONNECTIONS", 1))
DB_MAX_CONNECTIONS = int(os.getenv("DB_MAX_CONNECTIONS", 10))

# 主数据库连接字符串
DB_CONNECTION_STRING = f"dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD} host={DB_HOST} port={DB_PORT}"

# 业务数据库配置
B_DB_NAME = os.getenv("B_DB_NAME")
B_DB_USER = os.getenv("B_DB_USER")
B_DB_PASSWORD = os.getenv("B_DB_PASSWORD")
B_DB_HOST = os.getenv("B_DB_HOST")
B_DB_PORT = os.getenv("B_DB_PORT")
B_DB_MIN_CONNECTIONS = int(os.getenv("B_DB_MIN_CONNECTIONS", 1))
B_DB_MAX_CONNECTIONS = int(os.getenv("B_DB_MAX_CONNECTIONS", 10))

# 业务数据库连接字符串
B_DB_CONNECTION_STRING = f"dbname={B_DB_NAME} user={B_DB_USER} password={B_DB_PASSWORD} host={B_DB_HOST} port={B_DB_PORT}"

# JWT 配置
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 30))

# 腾讯云短信配置
TENCENT_SECRET_ID = os.getenv("TENCENT_SECRET_ID")
TENCENT_SECRET_KEY = os.getenv("TENCENT_SECRET_KEY")
SMS_SIGN = os.getenv("SMS_SIGN")  # 短信签名
REGISTER_TEMPLATE_ID = os.getenv("SMS_REGISTER_TEMPLATE_ID")  # 注册模板 ID
LOGIN_TEMPLATE_ID = os.getenv("SMS_LOGIN_TEMPLATE_ID")  # 登录模板 ID
SMS_REGION = os.getenv("SMS_REGION")  # 默认区域
SMS_APPID = os.getenv("SMS_APP_ID")  # 短信 SDK App ID

# 应用配置
APP_TITLE = "Studio API"
APP_DESCRIPTION = "AI Agent 对话系统 API"
APP_VERSION = "1.0.0"
APP_DOCS_URL = "/swagger"
APP_REDOC_URL = "/redoc"
