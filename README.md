# Studio

Studio python backend

本项目使用 uv 进行包管理。

# 安装 uv
```
pip install uv
```

# 初始化项目
```
uv init
```

## 依赖管理

使用 uv 进行依赖管理：

```bash
# 添加生产依赖
uv add package_name

# 添加开发依赖
uv add --dev package_name
```

依赖配置位于 `pyproject.toml` 中，分为生产依赖和开发依赖两部分。


# 添加检查工具作为开发依赖：用于检查format和Linter
```
uv add --dev ruff
```

```
```
uv pip freeze > requirements.txt
```


运行检查：
```bash
# 运行 ruff 检查
ruff check .

# 运行 mypy 类型检查
mypy api/

# 运行测试
pytest
```


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

