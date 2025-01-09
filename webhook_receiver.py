from fastapi import FastAPI, Request
import subprocess

app = FastAPI()

@app.post("/webhook")
async def webhook(request: Request):
    # 读取请求体（这里可以添加额外的检查，如分支名等）
    payload = await request.json()
    
    # 检查是否为push事件
    if request.headers.get("X-GitHub-Event") == "push":
        # 自动化部署脚本
        try:
            subprocess.run(["/bin/bash", "./deploy.sh"], check=True)
            return {"status": "success"}
        except subprocess.CalledProcessError as e:
            return {"status": "deployment failed", "error": str(e)}
    else:
        return {"status": "ignored", "message": "Not a push event"}
