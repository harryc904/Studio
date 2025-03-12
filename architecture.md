# AI Agent 对话系统项目结构设计
根据您的需求和现有代码，我为您设计一个通用的 AI Agent 对话系统的 FastAPI 项目结构。这个结构将包含 AI Agent 对话模块、Agent 工具模块和知识库模块。

## 项目结构
```plaintext
Project：Studio
│
├── api/                           # API 主目录
│   ├── main.py                    # 主入口文件，包含 FastAPI 应用实例和基础路由
│   ├── config.py                  # 配置文件，包含数据库连接、JWT等配置
│   │
│   ├── routers/                   # 路由模块，按功能分类
│   │   ├── auth.py                # 认证相关路由（登录、注册、验证码等）
│   │   ├── sessions.py            # 会话管理路由
│   │   ├── conversations.py       # 对话管理路由
│   │   ├── users.py               # 用户管理路由
│   │   ├── agent.py               # AI Agent 对话路由（新增）
│   │   └── knowledge.py           # 知识库管理路由（新增）
│   │
│   ├── services/                  # 业务逻辑层
│   │   ├── auth_service.py        # 认证相关服务
│   │   ├── session_service.py     # 会话管理服务
│   │   ├── conversation_service.py # 对话管理服务
│   │   ├── user_service.py        # 用户管理服务
│   │   ├── agent_service.py       # AI Agent 服务（新增）
│   │   └── knowledge_service.py   # 知识库服务（新增）
│   │
│   ├── utils/                     # 工具函数
│   │   ├── db.py                  # 数据库连接工具
│   │   ├── security.py            # 安全相关工具（JWT、密码哈希等）
│   │   ├── sms.py                 # 短信服务工具
│   │   └── logger.py              # 日志工具
│   │
│   ├── schemas/                   # 数据模型定义
│   │   ├── auth.py                # 认证相关模型
│   │   ├── session.py             # 会话相关模型
│   │   ├── conversation.py        # 对话相关模型
│   │   ├── user.py                # 用户相关模型
│   │   ├── agent.py               # Agent 相关模型（新增）
│   │   └── knowledge.py           # 知识库相关模型（新增）
│   │
│   ├── agent/                     # AI Agent 模块（新增）
│   │   ├── intent_analyzer.py     # 意图分析器
│   │   ├── tool_caller.py         # 工具调用器
│   │   └── response_generator.py  # 响应生成器
│   │
│   ├── tools/                     # Agent 工具模块（新增）
│   │   ├── prd_editor.py          # PRD 编辑器工具
│   │   ├── code_generator.py      # 代码生成工具
│   │   └── knowledge_retriever.py # 知识检索工具
│   │
│   └── knowledge/                 # 知识库模块（新增）
│       ├── connector.py           # 外部知识库连接器
│       ├── indexer.py             # 知识索引器
│       └── retriever.py           # 知识检索器
│
├── tests/                         # 测试目录
│   ├── test_auth.py               # 认证测试
│   ├── test_sessions.py           # 会话测试
│   ├── test_conversations.py      # 对话测试
│   ├── test_agent.py              # Agent 测试（新增）
│   └── test_knowledge.py          # 知识库测试（新增）
│
├── scripts/                       # 脚本目录
│   ├── init_db.py                 # 数据库初始化脚本
│   └── seed_data.py               # 测试数据生成脚本
│
├── .env                           # 环境变量文件
├── requirements.txt               # 项目依赖
└── README.md                      # 项目说明
 ```



## 模块说明
### 1. API 主模块
- main.py : 应用入口，包含 FastAPI 实例和基础配置
- config.py : 集中管理配置信息，从环境变量加载
### 2. 路由模块 (routers/)
- 按功能分类的路由处理器
- 每个路由文件负责特定功能的 API 端点
- 新增 agent.py 和 knowledge.py 处理 AI Agent 对话和知识库管理
### 3. 服务模块 (services/)
- 包含业务逻辑，被路由调用
- 处理数据库操作和业务规则
- 新增 agent_service.py 和 knowledge_service.py 处理 AI 相关业务逻辑
### 4. 工具模块 (utils/)
- 通用工具函数
- 数据库连接、安全、日志等功能
### 5. 数据模型 (schemas/)
- 使用 Pydantic 模型定义请求和响应的数据结构
- 新增 agent.py 和 knowledge.py 定义 AI 相关数据模型
### 6. AI Agent 模块 (agent/)
- intent_analyzer.py : 分析用户输入的意图
- tool_caller.py : 根据意图调用相应的工具
- response_generator.py : 生成最终响应
### 7. 工具模块 (tools/)
- 内部工具，不直接暴露 API
- prd_editor.py : PRD 编辑工具
- code_generator.py : 代码生成工具
- knowledge_retriever.py : 知识检索工具
### 8. 知识库模块 (knowledge/)
- connector.py : 连接外部知识库
- indexer.py : 索引知识内容
- retriever.py : 检索相关知识
## 实现建议
1. 重构现有代码 :
   - 将 main.py 中的功能按模块拆分到相应的文件中
   - 保持数据库直接 SQL 操作的方式，不引入 ORM
2. API 设计 :
   - AI Agent 对话 API: /agent/chat
   - 知识库管理 API: /knowledge/search , /knowledge/upload 等
3. 数据库表设计 :
   - 新增 agent_tools 表存储工具信息
   - 新增 knowledge_items 表存储知识库内容
   - 新增 agent_logs 表记录 Agent 调用日志
4. 安全性考虑 :
   - 保持现有的 JWT 认证机制
   - 为知识库访问添加权限控制
   
这个结构设计保留了您现有项目的核心功能，同时扩展了 AI Agent 和知识库相关的功能模块，使项目更加模块化和可维护。

## 导入规范

我们在项目中采用绝对导入（absolute imports）而不是相对导入（relative imports），原因如下：

1. 代码更明确，易于理解
2. IDE 支持更好（特别是 VS Code 的 Pylance）
3. 避免导入路径混淆
4. 减少包结构变更带来的问题
5. mypy 类型检查更可靠

示例：
```python
# 推荐 (绝对导入)
from api.schemas.user import UserInDB
from api.services.auth_service import authenticate_user

# 不推荐 (相对导入)
from ..schemas.user import UserInDB
from ..services.auth_service import authenticate_user
```