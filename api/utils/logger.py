import logging

# 创建根记录器
logger = logging.getLogger("studio_api")

# 配置日志格式和级别
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)  # 生产环境建议使用 INFO 级别

def get_logger(name=None):
    if name:
        return logging.getLogger(f"studio_api.{name}")
    return logger