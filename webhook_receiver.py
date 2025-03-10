from fastapi import FastAPI, Request, HTTPException
import subprocess
import logging

app = FastAPI()

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="/home/lighthouse/studio/debuglog/backend.log",  # 将日志输出到指定文件
)
logger = logging.getLogger(__name__)


@app.post("/webhook")
async def webhook(request: Request):
    # 读取请求体
    try:
        payload = await request.json()
        logger.info("Received payload: %s", payload)
    except Exception as e:
        logger.error("Failed to parse JSON payload: %s", str(e))
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # 检查是否为push事件
    event_type = request.headers.get("X-GitHub-Event")
    logger.info("Received GitHub event: %s", event_type)

    if event_type == "push":
        # 自动化部署脚本
        try:
            logger.info("Executing deployment script: ./deploy.sh")
            subprocess.run(["/bin/bash", "./deploy.sh"], check=True)
            logger.info("Deployment script executed successfully")
            return {"status": "success"}
        except subprocess.CalledProcessError as e:
            logger.error("Deployment failed: %s", str(e))
            return {"status": "deployment failed", "error": str(e)}
    else:
        logger.info("Ignored event: Not a push event")
        return {"status": "ignored", "message": "Not a push event"}
