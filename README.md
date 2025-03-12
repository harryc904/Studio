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


# 添加依赖包
```
uv add <package>
```

# 添加检查工具作为开发依赖：用于检查format和Linter
```
uv add --dev ruff
```

```
```
uv pip freeze > requirements.txt
```

```
uv.lock
uv.lock is a cross-platform lockfile that contains exact information about your project's dependencies. Unlike the pyproject.toml which is used to specify the broad requirements of your project, the lockfile contains the exact resolved versions that are installed in the project environment. This file should be checked into version control, allowing for consistent and reproducible installations across machines.
uv.lock 是一个跨平台的锁文件，其中包含关于您的项目依赖的确切信息。与用于指定项目广泛需求的 pyproject.toml 不同，锁文件包含在项目环境中安装的确切解决版本。此文件应纳入版本控制，以便在机器之间实现一致和可重复的安装。

uv.lock is a human-readable TOML file but is managed by uv and should not be edited manually.
uv.lock 是一个可读的 TOML 文件，但由 uv 管理，不应手动编辑。
```


```
To remove a package, you can use uv remove:
删除软件包，您可以使用 uv remove :


uv remove requests
```

```
Dependencies of the project are defined in several tables:
项目依赖关系定义在多个表中：

project.dependencies: Published dependencies.
project.dependencies : 已发布依赖项。
project.optional-dependencies: Published optional dependencies, or "extras".
project.optional-dependencies : 发布可选依赖项，或“额外内容”。
dependency-groups: Local dependencies for development.
dependency-groups : 开发所需的本地依赖项。
tool.uv.sources: Alternative sources for dependencies during development.
tool.uv.sources : 开发期间依赖项的替代来源。
```


# 测试配置
项目使用 pytest 进行测试。测试配置文件位于项目根目录的 `pytest.ini`。

## 安装测试依赖
```bash
uv add --dev pytest pytest-asyncio pytest-cov httpx
```

## 运行测试
```bash
pytest
```

## 测试配置说明
- `testpaths`: 指定测试文件所在目录为 `tests`
- `python_files`: 指定测试文件命名格式为 `test_*.py`
- `addopts`: 
  - `-v`: 显示详细测试信息
  - `--cov=api`: 对 api 目录进行覆盖率统计
  - `--cov-report=html`: 生成 HTML 格式的覆盖率报告
- `asyncio_mode = auto`: 自动处理异步测试