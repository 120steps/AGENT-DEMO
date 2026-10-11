# AGENT-DEMO

这是从原生工具调用逐步学习受控 Agent 工作流的独立 Python 工程。Phase 0、Phase 1 已验收并完成授权本地提交；Phase 1 包括手动 Tool Calling、两个本地工具、离线与真实模型验证。当前进度见路线图。尚未实现持续 Agent Loop、LangChain、LangGraph 或 Web API。

学习顺序和唯一进度入口见 [AGENT_LEARNING_ROADMAP.md](AGENT_LEARNING_ROADMAP.md)。旧 RAG 工程的静态接口调查见 [docs/rag_contract.md](docs/rag_contract.md)。

阶段学习总结从 [Phase 0 总结](docs/phase00_summary.md) 开始。每个 Phase 验收时必须新增 `docs/phaseNN_summary.md`，具体规则与模板见路线图第 15.1 节。

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

更新后用 `python -m pip list --format=freeze --exclude-editable` 导出固定版本清单，并在新的验证环境安装测试，不仅改文件内的版本号。Phase 0 在当时无提交的仓库中发现 `pip freeze` 会触发 VCS 警告，因此沿用 `pip list` 导出方式，避免记录本机源码路径。Phase 1 固定清单已在独立 `.venv-phase1-check` 环境安装验证。

安装命令使用显式 PyPI 地址和有限重试；本次默认 pip 安装曾长时间无进展，改用上述命令后成功。需要内部镜像的环境应根据实际网络设置替换地址，不在文档中保存带凭据的地址。

## 配置与隔离

配置只读取进程环境变量，不自动加载 `.env`。`.env.example` 是无密钥的配置说明；Phase 0 与 Phase 1 离线模式不需要 API Key。真实模型调用需要 `GEMINI_API_KEY`（或后备 `GOOGLE_API_KEY`），密钥不写入源码或日志。

```powershell
$env:AGENT_DEMO_ENV = "test"
$env:AGENT_DEMO_LOG_LEVEL = "DEBUG"
.\.venv\Scripts\python.exe examples\phase00_hello.py
```

允许的环境为 `development/test/production`；日志级别为 `DEBUG/INFO/WARNING/ERROR/CRITICAL`。未设置时使用 development 和 INFO；空值或无效值立即报错，避免悄悄使用错误配置。示例只输出非敏感环境和包信息，不打印其他环境变量。

`.venv` 存放本项目的解释器入口和依赖，不影响旧 RAG 工程。`src/agent_demo` 存放可导入的包；项目根目录放文档、示例和测试。可编辑安装把环境中的导入指向源码，改动源码后通常不用重新安装；改动依赖或包元数据后需要重新安装。

## Phase 1：原生 Tool Calling

```powershell
# 固定离线加法轨迹；不识别输入意图，不代表真实模型验收。
.\.venv\Scripts\python.exe examples\phase01_tool_calling.py --mock

# 先通过安全方式向当前进程设置 GEMINI_API_KEY，勿把密钥贴进文档。
$env:GEMINI_MODEL = "gemini-3.5-flash-lite"
.\.venv\Scripts\python.exe examples\phase01_tool_calling.py "What is 15 + 27?"
.\.venv\Scripts\python.exe examples\phase01_tool_calling.py "Please look up the specifications of MOCK-SW-48."
.\.venv\Scripts\python.exe examples\phase01_tool_calling.py "Hello!"
```

使用官方 `google-genai==2.29.0`，默认模型 `gemini-3.5-flash-lite`，已真实通过加法、模拟规格查询与问候验证。可通过 `GEMINI_MODEL` 覆盖，实际响应版本在 `MODEL_RESPONSE` 中记录。SDK 自动执行明确关闭，Dispatcher 仅允许 `add` 和 `lookup_product_spec`。规格都是 MOCK 数据，不能当成真实产品证据。

每次最多两次模型请求、一次工具调用轮次；同轮至多四个工具顺序执行。后续仍请求工具时返回 `additional_tool_call_required`，退出码 1；工具错误、API 错误和响应错误同样返回失败。SDK 单请求超时 30 秒、attempts=1，示例不会自动重试或进入持续循环。

原理、测试命令、真实验收记录见 [Phase 1 技术说明](docs/phase01_tool_calling.md)，框架快照见 [Phase 1 总结](docs/phase01_summary.md)。离线测试不会读取旧工程或调用网络；真实示例也不会自动读取旧工程凭据。

## Phase 3：LangChain 标准 Agent

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe examples\phase03_langchain_agent.py "Query MOCK-SW-48 and calculate total ports."
```

Phase 3 使用 `langchain==1.4.4`、`langchain-google-genai==4.4.0` 和官方 `create_agent`。真实运行需要进程环境中的 `GEMINI_API_KEY`；离线测试不调用网络。工具仍由 Phase 1 Dispatcher 校验，最终答案由 Pydantic `AgentAnswer` 验证。详见 [Phase 3 文档](docs/phase03_langchain_agent.md) 和 [阶段总结](docs/phase03_summary.md)。

## Phase 4：LangGraph 显式业务工作流

```powershell
.\.venv\Scripts\python.exe examples\phase04_langgraph_workflow.py
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

无需 API Key。StateGraph 顺序处理全部子要求，再汇总父条款；模型不参与最终判定。五类 MOCK 场景覆盖完全满足、数量不足、模块配置未知、证据缺失和冲突。原工具未提供电口类型，完整满足场景使用明确标注来源的额外 MOCK 假设；默认不补充时保留 PENDING。

详见 [Phase 4 技术说明](docs/phase04_langgraph_workflow.md) 和 [阶段总结](docs/phase04_summary.md)。CI 使用项目 dev extra 安装完整依赖；Windows 锁文件的版本说明不代表 Linux 已验证。

## Git

提交前检查 `git status --short`、`git ls-files` 和忽略规则。`.env`、虚拟环境、缓存、日志、runtime、outputs、数据库不提交。Phase 0 已经用户授权完成本地提交，尚未推送；后续提交和推送按用户授权执行。

初次远端检查默认 Schannel 后端遇到 `SEC_E_NO_CREDENTIALS`。以下只读命令改用单次 OpenSSL 后端并成功，不改变持久 Git 配置：

```powershell
$env:GIT_TERMINAL_PROMPT = "0"
git -c http.sslBackend=openssl ls-remote --symref origin HEAD "refs/heads/*"
```

该次查询退出码 0，没有返回 HEAD 或分支引用；不能把本地 `origin/main [gone]` 解读为 GitHub 仓库不存在。
