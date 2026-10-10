# AGENT-DEMO

这是从原生工具调用逐步学习受控 Agent 工作流的独立 Python 工程。当前仅实施 Phase 0：包安装、配置与离线验证；尚未实现 LLM、Tool Calling、LangChain、LangGraph 或 API。

学习顺序和唯一进度入口见 [AGENT_LEARNING_ROADMAP.md](AGENT_LEARNING_ROADMAP.md)。旧 RAG 工程的静态接口调查见 [docs/rag_contract.md](docs/rag_contract.md)。

## 环境

当前选择 CPython 3.11（本机为 3.11.0）、Windows 10 x64。本机只有这一套真实解释器；`py -0p` 未发现注册版本，因此使用 `python`，不依赖 `py` 启动器。

已查询 PyPI 发布元数据：FastAPI 0.143.0、LangChain 1.4.4、LangGraph 1.2.14、Pydantic 2.14.0、pytest 9.1.1 的 Python 要求均包含 3.11。这里只证明解释器版本满足声明；这些框架尚未安装，后续阶段仍需验证依赖组合。元数据查询日期为 2026-10-10。

3.11.0 是较早补丁版本；当前不改动全局 Python。以后升级到新的 3.11 补丁版本时应重建独立环境并重跑检查。`pyproject.toml` 暂限定 3.11 系列，其他系列未验证。

## PowerShell 快速启动

在工程根目录执行。已有 `.venv` 时先检查 `.venv\pyvenv.cfg` 和解释器路径，不覆盖或清空现有环境。

```powershell
python --version
python -m venv .venv

# 使用已经实际安装验证的外部依赖版本，包括构建工具。
.\.venv\Scripts\python.exe -m pip --isolated install --index-url https://pypi.org/simple --timeout 15 --retries 1 --disable-pip-version-check --no-cache-dir -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip --isolated install --disable-pip-version-check --no-cache-dir --no-build-isolation --no-deps -e .

.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe examples\phase00_hello.py
```

`requirements-lock.txt` 只记录外部包的固定版本，项目本身由下一条 editable install 安装；避免把本机绝对路径写入依赖清单。它适用于已验证的 Windows x64 / CPython 3.11 环境，不包含跨平台解析或文件哈希保证；Linux 在部署阶段单独验证。

首次解析开发依赖或更新版本时使用下面的命令；不是每次启动都升级：

```powershell
.\.venv\Scripts\python.exe -m pip --isolated install --index-url https://pypi.org/simple --timeout 15 --retries 1 --disable-pip-version-check --no-cache-dir --upgrade pip "setuptools>=77" wheel
.\.venv\Scripts\python.exe -m pip --isolated install --index-url https://pypi.org/simple --timeout 15 --retries 1 --disable-pip-version-check --no-cache-dir --no-build-isolation -e ".[dev]"
```

更新后用 `python -m pip list --format=freeze --exclude-editable` 导出固定版本清单，并在新的验证环境安装测试，不仅改文件内的版本号。当前无提交仓库中，`pip freeze` 即便排除 editable 项仍会尝试 VCS 检测并警告，因此使用 `pip list` 导出外部依赖，避免记录本机源码路径。

安装命令使用显式 PyPI 地址和有限重试；本次默认 pip 安装曾长时间无进展，改用上述命令后成功。需要内部镜像的环境应根据实际网络设置替换地址，不在文档中保存带凭据的地址。

## 配置与隔离

Phase 0 只读取进程环境变量，不自动加载 `.env`。`.env.example` 是无密钥的配置说明；当前不需要 API Key。

```powershell
$env:AGENT_DEMO_ENV = "test"
$env:AGENT_DEMO_LOG_LEVEL = "DEBUG"
.\.venv\Scripts\python.exe examples\phase00_hello.py
```

允许的环境为 `development/test/production`；日志级别为 `DEBUG/INFO/WARNING/ERROR/CRITICAL`。未设置时使用 development 和 INFO；空值或无效值立即报错，避免悄悄使用错误配置。示例只输出非敏感环境和包信息，不打印其他环境变量。

`.venv` 存放本项目的解释器入口和依赖，不影响旧 RAG 工程。`src/agent_demo` 存放可导入的包；项目根目录放文档、示例和测试。可编辑安装把环境中的导入指向源码，改动源码后通常不用重新安装；改动依赖或包元数据后需要重新安装。

## Git

提交前检查 `git status --short`、`git ls-files` 和忽略规则。`.env`、虚拟环境、缓存、日志、runtime、outputs、数据库不提交。当前未提交或推送；需要用户确认后才执行这些动作。

初次远端检查默认 Schannel 后端遇到 `SEC_E_NO_CREDENTIALS`。以下只读命令改用单次 OpenSSL 后端并成功，不改变持久 Git 配置：

```powershell
$env:GIT_TERMINAL_PROMPT = "0"
git -c http.sslBackend=openssl ls-remote --symref origin HEAD "refs/heads/*"
```

该次查询退出码 0，没有返回 HEAD 或分支引用；不能把本地 `origin/main [gone]` 解读为 GitHub 仓库不存在。
