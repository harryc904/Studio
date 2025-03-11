import logging
import sys
from logging.handlers import RotatingFileHandler
import os

# 确保日志目录存在
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# 创建日志记录器
logger = logging.getLogger("studio_api")
logger.setLevel(logging.DEBUG)

# 创建控制台处理器
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# 创建文件处理器，使用 RotatingFileHandler 限制文件大小
file_handler = RotatingFileHandler(
    os.path.join(log_dir, "api.log"),
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setLevel(logging.DEBUG)

# 创建格式化器
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# 添加处理器到记录器
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# 提供获取日志记录器的函数
def get_logger(name=None):
    if name:
        return logging.getLogger(f"studio_api.{name}")
    return logger