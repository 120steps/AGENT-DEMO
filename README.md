# AGENT-DEMO

这是从原生工具调用逐步学习受控 Agent 工作流的独立 Python 工程。现有原生 Agent Loop、LangChain Agent、LangGraph 业务判断、持久化恢复与人工审核，以及 HTTP Agentic RAG 适配。Phase 6 开发与离线验证完成，真实 RAG/PDF/模型评测保持 BLOCKED；Phase 2/3 的既有验收缺口保留，当前准确进度见路线图。Web API、MCP 和正式 SOC Excel 尚未实现。

第一次接触本项目，建议先读 [工程入门：整体框架、重要模块与逐步实现过程](docs/project_guide.md)，其中包含业务例子、源码阅读顺序、常用模板和无需密钥的运行命令。

学习顺序和唯一进度入口见 [AGENT_LEARNING_ROADMAP.md](AGENT_LEARNING_ROADMAP.md)。旧 RAG 工程的静态接口调查见 [docs/rag_contract.md](docs/rag_contract.md)。

阶段学习总结从 [Phase 0 总结](docs/phase00_summary.md) 开始。每个 Phase 验收时必须新增 `docs/phaseNN_summary.md`，具体规则与模板见路线图第 15.1 节。

## 环境

当前选择 CPython 3.11（本机为 3.11.0）、Windows 10 x64。本机只有这一套真实解释器；`py -0p` 未发现注册版本，因此使用 `python`，不依赖 `py` 启动器。

Phase 0 于 2026-10-10 查询过 FastAPI、LangChain、LangGraph、Pydantic 和 pytest 的发布元数据，其 Python 要求包含 3.11。后续阶段已经实际安装并验证 LangChain、LangGraph、Pydantic、模型 SDK、SQLite Checkpointer 和 RAG 客户端依赖；当前声明见 `pyproject.toml`，实际固定版本见 `requirements-lock.txt`。FastAPI 服务仍属于后续阶段。

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

## Phase 5：Checkpoint、恢复与人工审核

```powershell
$phase05Thread = 'learn-' + [guid]::NewGuid().ToString('N')
.\.venv\Scripts\python.exe examples\phase05_checkpoint_hitl.py start --thread-id $phase05Thread
$phase05State = .\.venv\Scripts\python.exe examples\phase05_checkpoint_hitl.py status --thread-id $phase05Thread | ConvertFrom-Json
$phase05State.review_snapshot | ConvertTo-Json -Depth 30
```

`start` 保存 SQLite Checkpoint 并退出；重新启动后用相同 thread_id 查看和恢复。查看快照后，使用其当前审核 ID、版本和内容摘要批准：

```powershell
$phase05Review = $phase05State.review_snapshot
.\.venv\Scripts\python.exe examples\phase05_checkpoint_hitl.py resume --thread-id $phase05Thread `
  --action approve --review-id $phase05Review.review_id `
  --review-version $phase05Review.review_version --snapshot-digest $phase05Review.snapshot_digest
.\.venv\Scripts\python.exe examples\phase05_checkpoint_hitl.py store-demo
```

也支持 reject，以及通过 `--action modify --modification-json 文件路径` 替换要求、证据或配置；修改后重新判断、生成新审核版本并等待再次批准。不能直接修改最终 FC/PC/NC。无 API Key 或真实资料需求。

Checkpoint 和操作账本分别位于 `runtime/phase05/`；仅批准后在 `outputs/phase05/` 生成一个可核查的 MOCK JSON 草稿。重复执行核查 operation_id、路径和内容 SHA-256，不覆盖未知文件；完成产物被删改时拒绝自动重建。CLI 是受信本地学习入口，thread_id 不提供身份认证。

实际版本 `langgraph-checkpoint-sqlite==3.1.2`；完整命令、跨进程证据、限制见 [Phase 5 技术说明](docs/phase05_checkpoint_hitl.md) 和 [阶段总结](docs/phase05_summary.md)。

## Phase 6：Agentic RAG（真实验收 BLOCKED）

不启动或修改 RAG-DEMO；不在新工程创建向量库。离线演示使用 HTTP MockTransport 与脚本模型，输出明确标注 `offline_mock`：

```powershell
.\.venv\Scripts\python.exe examples\phase06_agentic_rag.py --offline --scenario greeting --chat
.\.venv\Scripts\python.exe examples\phase06_agentic_rag.py --offline --scenario supplement
.\.venv\Scripts\python.exe examples\phase06_agentic_rag.py --offline --mode benchmark
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

真实调用前，须先准备可安全查询的独立 V3 服务，确认不会修改旧项目，然后在当前进程设置：

- `AGENT_DEMO_RAG_BASE_URL`：固定 HTTPS origin，或已核实的本机 HTTP 服务 origin。
- `AGENT_DEMO_RAG_TOKEN`：有效 Bearer，仅安全配置到环境；不贴到源码、聊天或日志。
- `AGENT_DEMO_RAG_KB`：获授权知识库，默认 default。
- `AGENT_DEMO_RAG_PAGE_SEMANTICS`：默认 unknown；V3 来源及物理页约定核实后可设置 pdf_physical_1_based。
- `AGENT_DEMO_LIVE_RAG_CONFIRM_READONLY=1`：操作者对上述安全服务的确认，不能用于授权旧工程写入。
- `GEMINI_API_KEY` 或 `GOOGLE_API_KEY`：Agent 模型凭据；纯 retrieve 不需要。模型名复用 `GEMINI_MODEL`。

```powershell
# 只调用已配置的 /retrieve，不登录、下载、索引或重建旧服务。
.\.venv\Scripts\python.exe examples\phase06_agentic_rag.py --mode retrieve --query "实际资料问题"
.\.venv\Scripts\python.exe examples\phase06_agentic_rag.py --query "实际设备问题" `
  --document-id "已确认文档ID" --version-id "已确认版本ID" `
  --requirements data\private\requirements.json --bindings data\private\bindings.json
.\.venv\Scripts\python.exe examples\phase06_agentic_rag.py --mode benchmark --case-file data\private\live-cases.json
```

人工 bindings 明确型号、文档/版本、SHA-256、授权 PDF 路径和适用条件。实际核查 PDF 哈希、物理页及原文后，只提取有限的明确规格行；不支持的自然语言或表格保留 PENDING。不能从文件名或关键词确认型号，也不能把 LLM 候选解释当成业务结论。真实路径不会回退到 MOCK；Phase 5 审核仍可使用 real_rag 模式，输出始终为草稿。

真实 opt-in 测试还需要 `AGENT_DEMO_RAG_BINDINGS_JSON`（新工程下 JSON 路径）和 `AGENT_DEMO_RAG_TEST_QUERY`；当前缺安全服务及资料，该验收明确跳过为 BLOCKED。401/403 返回 auth_failed，连接/超时错误有独立错误码，空或不充分证据保留 PENDING。不要用启动或重建旧库解决配置阻碍。

详见 [当前契约](docs/rag_contract.md)、[Phase 6 技术说明](docs/phase06_agentic_rag.md)、[总结](docs/phase06_summary.md)和[对比报告](eval/reports/phase06_baseline.md)。私有 PDF/绑定/用例放入已忽略的 `data/private/`，运行证据和数据库继续保持忽略。

## Git

提交前检查 `git status --short`、`git ls-files` 和忽略规则。`.env`、虚拟环境、缓存、日志、runtime、outputs、数据库不提交。Phase 0 已经用户授权完成本地提交，尚未推送；后续提交和推送按用户授权执行。

初次远端检查默认 Schannel 后端遇到 `SEC_E_NO_CREDENTIALS`。以下只读命令改用单次 OpenSSL 后端并成功，不改变持久 Git 配置：

```powershell
$env:GIT_TERMINAL_PROMPT = "0"
git -c http.sslBackend=openssl ls-remote --symref origin HEAD "refs/heads/*"
```

该次查询退出码 0，没有返回 HEAD 或分支引用；不能把本地 `origin/main [gone]` 解读为 GitHub 仓库不存在。
