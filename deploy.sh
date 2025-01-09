#!/bin/bash

# 部署脚本 - deploy.sh

# 设置项目目录
PROJECT_DIR="/home/lighthouse/studio/backend"

# 导航到项目目录
cd $PROJECT_DIR

# 打印当前操作的时间和信息
echo "[$(date)] - 开始自动部署..."

# 从Git仓库拉取最新代码
echo "拉取最新代码..."
git pull origin main

# 安装或更新Python依赖项
echo "安装或更新依赖项..."
pip install -r requirements.txt

# 检查uvicorn进程是否在运行，如果是，则停止它
echo "检查并停止正在运行的FastAPI服务..."
if pgrep -f "uvicorn main:app" > /dev/null
then
    pkill -f "uvicorn main:app"
    echo "FastAPI服务已停止。"
else
    echo "FastAPI服务未在运行。"
fi

# 启动FastAPI应用，使用nohup命令在后台运行
echo "使用uvicorn启动FastAPI应用..."
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &

# 打印部署完成的消息
echo "[$(date)] - 自动部署完成。"
