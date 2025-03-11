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

# 添加检查工具：用于检查format和Linter
```
uv add ruff
```

```
uv pip install tencentcloud-sdk-python
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