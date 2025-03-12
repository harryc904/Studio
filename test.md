# 测试配置
项目使用 pytest 进行测试。测试配置文件位于项目根目录的 `pytest.ini`。

## 安装测试依赖
```bash
uv add --dev pytest pytest-asyncio pytest-cov httpx
```


这样设置后，您就可以开始编写和运行测试了。安装的组件包括：

pytest: 测试框架本身
pytest-asyncio: 用于测试异步代码
pytest-cov: 用于生成测试覆盖率报告
httpx: 用于测试 FastAPI 端点

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