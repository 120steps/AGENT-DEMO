# AGENT-DEMO — Agent 学习与工程实施路线图

> 版本：v2.0，实施版<br>
> 更新日期：2026-10-10<br>
> 当前状态：**Phase 3 DOING — LangChain 技术验收完成，待本地提交授权**<br>
> 当前阶段：**Phase 0、Phase 1 DONE；Phase 2 与 Phase 3 技术实现已验证，提交状态分别按记录维护**<br>
> 下一任务：**完成 Phase 3 本地提交授权后，进入 Phase 4 显式 LangGraph 工作流。推送未授权。**<br>
> 唯一进度入口：本文件。后续按本文任务与验收证据推进。<br>
> 边界：AGENT-DEMO 独立开发；RAG-DEMO 只读检查，未经明确授权不修改。

## 0. 使用方式与当前事实

本文是学习和实施计划，不代表功能已经实现。任务完成后必须记录验证证据，不能仅凭代码生成或文件存在标记 DONE。

### 0.1 已确认的工程事实

截至 2026-10-10 的本地只读检查：

- 工程目录：`D:\workspace\AI\AGENT-DEMO`。
- 已存在 `.git`，当前分支为 `phase-1`；Phase 1 实现提交为 `7a67a36`，完成记录另提交。Phase 0 的 `08dc5b4`、`f87ec8d` 与后续 `c3e5f2e` 历史保留。
- 已配置远端：`https://github.com/120steps/AGENT-DEMO.git`。
- Phase 1 重新只读查询远端成功，HEAD 指向 `main`，`main` / `phase-1` 均存在并指向 `c3e5f2e`。当前分支跟踪 `origin/phase-1`；早期 `[gone]` 与空引用属于历史记录。
- 已建立 src 工程、主 `.venv` 和全新 `.venv-phase0-check`，均为 Windows x64 / Python 3.11.0；安装、6 项测试、Ruff、示例和依赖检查通过。
- RAG-DEMO 已定位于 `D:\workspace\AI\rag-demo`，V1/V3 静态接口调查完成；真实请求、授权和业务资料尚未验证。
- 技术证据见 `docs/phase00_validation.md`，接口调查见 `docs/rag_contract.md`。本地提交已完成；未推送。Phase 0 已验收，真实 RAG 集成留待 Phase 6。
- Phase 1 使用 google-genai 2.29.0 / gemini-3.5-flash-lite，主环境和独立新环境各 42 项离线测试通过；真实加法、MOCK 规格和问候验证通过。已授权本地提交为 7a67a36，本次未推送，详见 docs/phase01_tool_calling.md。

### 0.2 每次继续时的流程

1. 阅读顶部状态和[进度总览](#1-进度总览)。
2. 对照代码、运行结果和日志核实实际进度，发现差异先修正文档。
3. 从当前阶段第一个未完成的必做任务开始，每次推进一个可验证的小目标。
4. 先解释本次要学习的概念，再实现最小功能，运行检查并讨论结果。
5. 更新任务复选框；在[学习日志](#16-学习日志)记录命令、结果、限制和下一任务。
6. 阶段验收时，按第 15.1 节生成 `docs/phaseNN_summary.md`，核对内容后更新顶部、总览表和完成日期。
7. 设计发生变化时，在[决策记录](#17-架构决策记录adr)说明原因，再调整后续任务。

后续可以直接提出：

> 请按照 AGENT_LEARNING_ROADMAP.md 继续。先核实当前任务与验收证据，再带我完成下一个最小任务。解释关键原理，完成后更新路线图和学习日志。不要修改 RAG-DEMO。

状态：`TODO` 未开始；`DOING` 进行中；`BLOCKED` 依赖未满足；`DONE` 已验收；`DEFERRED` 明确延期并记录理由。

## 1. 进度总览

| Phase | 主题 | 状态 | 核心交付物 | 完成日期 |
|---|---|---|---|---|
| 0 | 仓库、环境、RAG 契约摸底 | DONE | 可安装工程、离线测试、接口调查及本地提交已完成 | 2026-10-10 |
| 1 | 原生 Tool Calling | DONE | 单轮闭环、42 项测试、真实验证及授权本地提交完成 | 2026-10-10 |
| 2 | 原生 Agent Loop | DOING | 有预算和终止控制的多步执行、CI 与真实多步验证完成；待本地提交 | — |
| 3 | LangChain 标准 Agent | DOING | create_agent、共享工具、Pydantic 输出、真实验证完成；待本地提交 | — |
| 4 | LangGraph 显式工作流 | TODO | 要求、证据、判断的分支流程 | — |
| 5 | Checkpoint、恢复、人工审核 | TODO | 重启恢复和重复执行保护 | — |
| 6 | 真实 Agentic RAG | TODO | 真实接口集成及引用评测 | — |
| 7 | MCP 独立实验 | TODO | 本地 MCP Server / Client | — |
| 8 | 评测、安全、可观测性汇总 | TODO | 回归报告和错误诊断 | — |
| 9 | 最小 API 与部署完善 | TODO | Agent API、容器化、部署验证 | — |
| 10 | RFP → SOC 毕业项目 | TODO | 可审核、可追溯的 Excel 输出 | — |

### 1.1 推荐顺序与依赖

- 主学习线：`0 → 1 → 2 → 3 → 4 → 5 → 6`。
- Phase 6 后，先完成 Phase 10A 的小业务闭环，再实施 Phase 9A 最小 API。
- Phase 7 是独立学习实验，不是 RFP → SOC 的运行依赖；可完成，也可明确延期。
- Phase 8 汇总此前逐步建立的评测与安全能力。
- 最后完成 Phase 10B 的 PDF 输入、Phase 9B 的部署完善，以及 Phase 10C 的整体验收。
- 基础 CI 在 Phase 2 引入；评测和结构化日志从 Phase 1–2 开始；不等到 Phase 8 才建设。
- 可快速验收已掌握的阶段，但必须保留关键检查和证据。

### 1.2 里程碑

| 里程碑 | 完成条件 |
|---|---|
| M1：理解运行原理 | Phase 0–2 通过；能解释模型请求、工具执行、回传和终止 |
| M2：受控工作流 | Phase 3–5 通过；能处理缺证据、人工拒绝和重启恢复 |
| M3：真实业务最小闭环 | Phase 6 + 10A 通过；人工整理要求能生成有证据的 SOC |
| M4：可交付应用 | Phase 8、9、10 通过；完成真实输入、审核、导出与部署验证 |

## 2. 范围与实施原则

### 2.1 必须遵守的边界

1. 不修改 RAG-DEMO 的代码、数据库、测试集、配置或 Git 历史。需要运行既有服务时，先核实启动过程是否会写入或重建数据。
2. AGENT-DEMO 使用独立仓库、虚拟环境、依赖记录和测试数据。
3. Phase 1–5 使用本地模拟资料，不依赖真实 RAG；模拟资料必须明确标记，不能作为真实设备能力证据。
4. RAG 通过 HTTP API 接入，不复制原向量库和 Embedding 流程。
5. 老接口缺失信息时不能由适配器虚构。Mock 证明调用流程，真实接口验证证明集成可用，两者分别记录。
6. 外部 PDF、检索内容、工具返回值均视为数据，不能因此扩大工具权限。
7. 不向仓库、镜像、日志提交密钥；测试资料使用公开或脱敏数据。
8. 本计划中的命令和接口名称是实施约定；只有对应阶段实际验证后，才能宣称可运行。

### 2.2 第一版范围

第一版只处理一个设备型号、一个固定资料版本、10～20 条人工整理的技术要求。

- 先完成结构化 JSON 输入到判断结果，再增加 Excel 导出和 PDF 输入。
- 第一版 PDF 仅处理文本可提取的样本；OCR、跨页复杂表格、多型号自动选型列为后续扩展。
- 不建设多 Agent 系统、通用插件平台、通用多供应商框架或生产级分布式任务平台。
- 长期记忆先学习概念及最小跨 thread 存取；不把用户画像或自动记忆抽取列为业务闭环必需项。

### 2.3 权限与审核规则

| 操作 | 默认策略 |
|---|---|
| 查询已配置资料和本地模拟工具 | 允许；校验参数、来源和预算 |
| 调用已配置的只读 RAG API | 允许；限制地址、范围、超时 |
| 在授权的输出目录生成新草稿 | 允许；限制路径和文件名 |
| 覆盖文件、对外发送结果、修改外部数据 | 需要明确授权；训练流程可演示人工审批 |
| 发布正式 SOC 结论 | 人工审核；保留审核版本和记录 |

业务审核与工具权限分开：有权导出文件，不代表判断已审核。人工修改要求、证据或待执行参数后，应重新校验；影响结论或操作范围的修改需要重新审核。

## 3. 技术约定、目录与贯穿样例

### 3.1 初始技术约定

- Python：Phase 0 选择一个受所需依赖支持的版本，在 `pyproject.toml` 和 README 中记录。
- 初始环境：`python -m venv .venv`，使用虚拟环境内的 Python 与 pip；Windows 命令优先直接使用 `.venv\Scripts\python.exe`，不依赖激活脚本。
- 项目配置：`pyproject.toml`，采用 `src` 布局和可编辑安装；测试使用 pytest，静态检查使用 Ruff。
- 依赖：每次阶段验收记录解析后的确切版本到 `requirements-lock.txt`。这是已验证环境的固定版本清单；Windows 和 Linux 的兼容性分别验证，不宣称天然跨平台。
- 模型：Phase 1 选定一款实际可用、支持工具调用的模型及官方 SDK。模型名、地址和凭据通过配置注入。
- 原生实现与框架实现共用业务函数、Pydantic 数据模型和用例；分别维护模型协议适配与执行控制。
- LangChain 使用 `create_agent`；LangGraph 使用显式图；API 和版本以实际安装验证为准。
- HTTP 使用 httpx；服务使用 FastAPI；本地持久化 checkpoint 优先采用 SQLite 方案并验证兼容性。
- Excel 导出在 Phase 10A 决定库；PDF 解析在 Phase 10B 决定库，均以样本实测为依据。
- Docker 与完整部署在业务闭环稳定后完善。

### 3.2 逐步建立的目录

```text
AGENT-DEMO/
├── AGENT_LEARNING_ROADMAP.md
├── README.md
├── pyproject.toml
├── requirements-lock.txt
├── .env.example
├── .gitignore
├── src/agent_demo/
│   ├── config.py
│   ├── domain/          # 要求、证据、判断及确定性规则
│   ├── agents/          # 原生和 LangChain 控制层
│   ├── tools/           # 共用业务工具与参数校验
│   ├── graphs/          # 显式工作流、审核、恢复
│   ├── integrations/    # RAG 客户端、协议适配
│   ├── mcp/             # 独立 MCP 实验
│   ├── evaluation/      # 评测代码
│   ├── api/             # FastAPI
│   └── soc/             # RFP 解析、审核、Excel 导出
├── examples/            # 各阶段入口
├── tests/               # 离线测试和集成测试
├── eval/                # 用例、基线和报告
├── data/fixtures/       # 可提交的公开/模拟/脱敏样本
├── docs/                # 契约、学习笔记、架构图
├── outputs/             # 生成文件，默认忽略
├── runtime/             # checkpoint 等运行数据，默认忽略
├── Dockerfile
├── compose.yaml
└── .github/workflows/
```

只创建当前阶段实际需要的文件和目录。大文件、私有资料、生成文件和运行数据库不提交。

### 3.3 贯穿样例

示例要求：设备至少提供 48 个千兆电口和 4 个万兆上联口。

模拟数据至少覆盖：全部满足、数量不足、可选模块才能满足、证据缺失、来源冲突。型号使用明确的模拟标识；真实型号只在获得对应文档后引入。

整个学习过程围绕同一任务增加能力：原生调用 → 多步执行 → 框架对照 → 条件工作流 → 审核恢复 → 真实证据 → Excel → PDF → 部署。

## 4. Phase 0 — 仓库、环境与 RAG 契约摸底

**目标：** 建立可安装、可测试的最小工程，同时尽早识别真实集成的阻碍。

**必做任务**

- [x] 核对当前 Git 状态、远端可访问性及远端内容；沿用现有工程，不重复创建或克隆。
- [x] 确认 Python 版本，创建独立 `.venv`。
- [x] 建立 README、`.gitignore`、`.env.example`、`pyproject.toml` 和最小目录。
- [x] 配置可编辑安装、pytest、Ruff；记录依赖版本和安装步骤。
- [x] 实现不调用 LLM 的 `examples/phase00_hello.py`，验证包可以正确导入。
- [x] 使用一个有意义的离线检查验证安装与配置；不堆积仅验证常量的测试。
- [x] 确认 RAG-DEMO 所在位置；只读检查 API 定义、运行说明或可获得的响应样本。
- [x] 写入 `docs/rag_contract.md`：实际端点、认证、请求、响应、错误，以及待确认项。
- [x] 重点确认原文片段、文档标识、型号、版本、页码语义、筛选能力；区分检索 API 与问答 API。
- [x] 已定位旧工程；明确记录仅静态核实及真实契约未验证项，不猜测接口，Phase 6 真实验收保持待办。
- [x] 核实 `.env`、`.venv`、运行数据已忽略；全新环境安装和验证通过。
- [x] 经明确授权创建首个本地提交 `08dc5b4`；推送未授权，未执行。

**计划验证入口：** 可编辑安装、`python -m pytest`、`python -m ruff check .`、运行 `examples/phase00_hello.py`。实际 Windows 命令写入 README。

**验收：** 在新的虚拟环境按 README 安装并运行成功；契约调查有明确结论或未解决项；未修改 RAG-DEMO。

**2026-10-10 实际结果：** 上述技术验收通过；主环境 6 passed，全新验证环境 6 passed，Ruff 与依赖检查通过。复查仍为 6 passed；用户明确授权本地提交及完成记录，已完成首个提交 `08dc5b4`，Phase 0 标记 DONE。推送不属于本次授权，也不是本地验收前提。详见 `docs/phase00_validation.md`。

**不能忽略的结果：** 若旧接口无法提供证据，记录缺口及可选方案：使用现有更底层检索接口、独立只读服务包装已有能力，或另行提出旧项目变更申请。包装不得虚构不存在的数据。

### 4.1 Phase 0 完成标准核查

- [x] 本阶段必做任务完成；真实 RAG 请求和部署明确属于后续阶段。
- [x] README 有实际安装、运行和排错步骤，示例可重复执行。
- [x] 离线测试通过，并在第二个全新虚拟环境按固定版本清单复现。
- [x] README 已解释 venv、src 布局和 editable install；验证记录解释安装等待、VCS 检测等失败案例。
- [x] 学习日志和验证记录保存结果、已知限制及下一任务。
- [x] 补齐阶段总结 `docs/phase00_summary.md`，说明实际工作、核心概念、当前框架及限制。
- [x] 交付范围和忽略规则已核查；旧工程只读状态前后保持一致。
- [x] 实现已形成可追踪的本地提交；完成状态另提交留痕。没有推送。

## 5. Phase 1 — 原生 Tool Calling

**学习问题：** 模型为什么只提出调用请求？应用如何安全执行并返回结果？

**必做任务**

- [x] 选定模型、SDK 和实际 API 协议，验证一次最小真实请求；不假设各供应商消息结构相同。
- [x] 实现 `add(a, b)` 和 `lookup_product_spec(model)` 两个只读业务函数。
- [x] 定义工具参数 schema、允许列表和分发器；拒绝未知工具及无效参数。
- [x] 完成模型请求 → 工具调用 → 校验 → 执行 → 结果回传 → 最终回答。
- [x] 正确保留调用 ID 和工具结果对应关系；处理普通回答、工具异常、无效 JSON。
- [x] 建立固定用例和脚本化模型响应，区分离线测试与真实模型验证。
- [x] 记录最小事件：运行 ID、调用 ID、工具名、参数、结果状态、耗时；敏感字段脱敏。

**交付：** `examples/phase01_tool_calling.py`、共用工具、离线用例、真实请求验证记录。

**验收：** 计算任务能够完成工具闭环；问候不强制调用；非法调用不执行；模型请求和应用执行可分别解释。至少一次真实模型闭环成功，不能只以 mock 验收。

**2026-10-10 实际结果：** 技术验收通过。两套环境各 42 passed（含 Phase 0 的 6 项），Ruff / pip check / 原示例 / Mock 示例通过；真实加法、MOCK 规格查询及问候均退出 0。google-genai 2.29.0，gemini-3.5-flash-lite，SDK 自动执行关闭，结果以 user 角色回传，保留实际 ID 和原始 Content。第二次响应再请求工具明确停止。证据见[技术说明](docs/phase01_tool_calling.md)和[总结](docs/phase01_summary.md)。

### 5.1 Phase 1 完成标准核查

- [x] 必做任务与十个学习问题说明完成。
- [x] 可运行入口与依赖清单在新环境验证通过。
- [x] 离线安全、故障及协议测试通过，Phase 0 正常。
- [x] 真实模型触发两种工具并完成闭环，问候直接回答。
- [x] 日志与阶段总结保存结果、失败修复及限制。
- [x] 敏感文件与旧工程只读状态已检查。
- [x] 本阶段代码形成经用户授权的本地提交 7a67a36；完成记录另提交，不推送。

本阶段用户另行明确授权本地提交及完成记录，版本交付完成，标记 DONE。

## 6. Phase 2 — 原生 Agent Loop

**学习问题：** 如何执行多步任务，并在成功、故障和预算耗尽时正确结束？

**必做任务**

- [x] 实现模型与工具循环；支持一轮多个工具调用及多轮连续调用。
- [x] 第一版同轮工具顺序执行；不把多工具调用等同于必须并发。
- [x] 完成查询规格 → 计算或比较 → 生成答复的贯穿样例。
- [x] 明确 `max_model_rounds`、`max_tool_calls`、单次调用超时、总任务期限与重试次数。
- [x] 设置输出 token 限制；记录实际 usage。无可靠价格信息时成本标记不可估算。
- [x] 定义终止状态：完成、预算耗尽、超时、失败；不得将中断伪装成成功答案。
- [x] 覆盖无工具、单工具、多工具、无效参数、工具故障和循环终止用例。
- [x] 记录 action/observation 事件、模型耗时、工具耗时和 usage；不依赖模型内部推理文本。
- [x] 增加基础 CI，运行离线测试和静态检查；默认不依赖真实模型密钥。

**交付：** `examples/phase02_agent_loop.py`、轨迹样本、初始评测用例和 CI。

**验收：** 多步任务成功；循环与重试均有上限；故障可定位；至少一次真实模型多步验证。超时还应确认工具是否实际终止，不能仅停止等待后声称副作用已取消。

**2026-10-10 实际结果：** 主环境 46 passed，Ruff check/format 通过，Phase 2 Mock 三轮通过；真实 Gemini 多步任务完成 `lookup_product_spec → add → final`，退出码 0，最终回答 52。CI 文件已建立，GitHub runner 尚未单独执行。技术细节见 [Phase 2 文档](docs/phase02_agent_loop.md)，阶段总结见 [docs/phase02_summary.md](docs/phase02_summary.md)。

## 7. Phase 3 — LangChain 标准 Agent

**学习问题：** 框架负责哪些控制逻辑，哪些仍由应用负责？

**必做任务**

- [x] 安装并锁定经验证的 LangChain 与模型集成包，核实 `create_agent`。
- [x] 将共用业务函数封装为框架工具，避免复制规格查询与判断逻辑。
- [x] 完成与 Phase 2 等价的任务，添加 Pydantic 结构化输出与工具错误处理。
- [x] 保留执行次数、超时和预算约束，核实框架内相关限制的含义。
- [x] 使用同一批业务用例比较答案、必要动作、禁止动作、调用次数和延迟。
- [x] 记录原生实现与框架实现的消息、工具执行、middleware 和终止机制对照。

**交付：** `examples/phase03_langchain_agent.py`、对照笔记及验证记录。

**验收：** 两种实现均完成核心任务；非法工具和错误参数不会绕过业务边界；不要求真实模型输出逐字相同或轨迹顺序完全一致。

**2026-10-10 实际结果：** `langchain==1.4.4`、`langchain-google-genai==4.4.0` 已安装并锁定；主环境 49 passed，Ruff/format/pip check 通过。真实 Gemini LangChain Agent 完成 MOCK-SW-48 查询与总端口计算，Pydantic 输出为 52，退出码 0。阶段总结见 [docs/phase03_summary.md](docs/phase03_summary.md)，技术说明见 [docs/phase03_langchain_agent.md](docs/phase03_langchain_agent.md)。仅剩本地提交授权，暂不标记 DONE。

## 8. Phase 4 — LangGraph 显式工作流与业务模型

**学习问题：** 哪些决策交给模型，哪些流程和规则应由代码固定？

**必做任务**

- [ ] 定义 Requirement、Evidence、Decision 三类 Pydantic 数据模型。
- [ ] 将复合条款拆成可分别核验的子要求；保留父条款 ID、原文及位置。
- [ ] 建立提取或读取要求 → 查询证据 → 校验 → 判断 → 输出的显式图。
- [ ] 设置有证据、缺证据、冲突、工具失败路径；判断前执行确定性校验。
- [ ] 将数值、单位、比较运算和字段完整性检查交给代码。
- [ ] 理解 State 更新、消息合并及 reducer，避免重试造成重复追加。
- [ ] 画出流程图，离线覆盖每条关键分支。

**交付：** `examples/phase04_langgraph_workflow.py`、共用业务模型、条件分支测试。

**验收：** 缺证据不生成肯定结论；工具失败不等同于设备不满足；冲突进入待确认；数值规则可独立验证。

## 9. Phase 5 — Checkpoint、重启恢复与人工审核

**学习问题：** 如何恢复任务，并避免恢复、重试或重复审批导致再次写入？

**必做任务**

- [ ] 区分消息上下文、checkpoint、跨 thread store 和业务数据库。
- [ ] 先演示内存 checkpoint，再接入本地持久化 checkpoint。
- [ ] 验证同一 thread 连续性、新 thread 隔离，以及停止进程后的恢复。
- [ ] 将待审核内容明确保存为具体要求、证据、判断及拟执行动作。
- [ ] 拆分准备、审核和执行节点；理解 interrupt 恢复可能重跑节点。
- [ ] 对写入动作使用操作 ID 和重复执行保护；设计输出文件重复生成策略。
- [ ] 测试批准、拒绝、修改后重新校验；影响范围改变时重新审核。
- [ ] 测试重复恢复、重复提交审批，以及执行后重试不会重复产生业务结果。
- [ ] 用最小例子展示跨 thread store 的存取；记录其与业务状态的区别。
- [ ] 明确 thread_id 不是授权凭据，服务化时必须检查任务归属。

**交付：** `examples/phase05_checkpoint_hitl.py`、持久化恢复与审核测试。

**验收：** 关闭程序后恢复成功；拒绝后无受保护写入；重复审批/恢复不重复执行；新 thread 无上下文串线。

## 10. Phase 6 — 真实 Agentic RAG 集成

**学习问题：** 如何让模型决定检索，同时让证据和权限保持可核验？

**进入条件：** Phase 0 的契约已核实，真实服务可以返回足够的证据信息。无法满足时，明确阻碍；可以完成客户端离线开发，但不得标记真实集成 DONE。

**必做任务**

- [ ] 更新 `docs/rag_contract.md`，保存脱敏响应样本和实际错误场景。
- [ ] 编写 RAGClient 与 `search_knowledge_base` 工具，限定服务地址、参数范围、超时及重试。
- [ ] 将真实响应映射到 Evidence；缺失字段显式标注，不自行补造页码或原文。
- [ ] 保留文档 ID、版本/哈希（可获得时）、原文片段、chunk_id、页码语义和适用型号/条件。
- [ ] 对一般问候允许直接回答；设备合规判断必须经过证据流程。
- [ ] 支持有限次数的查询改写和补充检索；证据不足后停止并返回待确认。
- [ ] 测试空结果、接口故障、字段缺失、来源冲突和引用不匹配。
- [ ] 加入检索内容中的提示注入样本，验证其不能改变工具权限。
- [ ] 比较一次固定检索基线与 Agentic RAG 的任务效果、调用数和延迟。
- [ ] 分别记录 Mock API 测试与真实服务端到端结果。

**交付：** RAGClient、真实引用样例、Agentic RAG 评测用例与报告。

**验收：** 真实 PDF 引用可回查且页码解释明确；服务不可用时返回可诊断状态；无证据不生成 FC；旧项目未被修改。

## 11. Phase 7 — MCP 独立实验

**定位：** 学习标准化工具发现与调用；不强制用 MCP 改造已稳定的 HTTP 集成。

**必做任务（选择实施本阶段时）**

- [ ] 理解 Host、Client、Server 及工具发现。
- [ ] 核实 SDK 版本；先使用本地 stdio，暴露现有规格查询或计算业务函数。
- [ ] 完成初始化、发现、调用、结果解析与进程退出清理。
- [ ] 校验工具名称、参数和返回值；发现到工具不代表自动允许执行。
- [ ] 测试启动失败、调用超时、无效返回和服务断开。
- [ ] 对比 Python 函数、HTTP API 与 MCP 的职责及开销。

**扩展任务：** 远程 HTTP 传输及认证单独实施，不阻塞本地实验。

**验收：** Agent 能通过 MCP 调用共用工具，失败可诊断，子进程可清理。若延期，标记 DEFERRED 并记录原因；不把延期实验写成已实现。

## 12. Phase 8 — 评测、安全与可观测性汇总

**定位：** 汇总此前的测试和事件，不重新从零建设。

**必做任务**

- [ ] 汇总 `eval/agent_test_cases.json`；每条记录 ID、输入、预期事实/状态、必要与禁止动作、证据和数据来源。
- [ ] 分开报告离线确定性测试、真实模型评测、真实 RAG 集成。
- [ ] 记录模型标识、可用版本信息、SDK/依赖、提示版本、资料版本、参数、日期和代码版本。
- [ ] 汇总任务成功率、工具成功率、误判、引用准确性、平均调用数、延迟和 token；成本按可核实价格估算。
- [ ] 对关键真实模型样例重复运行，记录波动和样本规模；不声称完全确定性。
- [ ] 扩展未知工具、错误参数、路径越界、注入、服务故障、重试耗尽和重复审批用例。
- [ ] 保留敏感字段脱敏后的轨迹，能定位到模型请求、工具调用和节点。
- [ ] 输出基线报告、失败案例和下一步改进项。

**硬性验收：** 离线控制逻辑测试全部通过；选定测试集中未授权写入、无证据 FC、伪造引用为 0；所有这些结果必须标注测试范围，不能推广成对任意输入的绝对保证。

真实模型成功率等质量指标先测基线，再在扩展前制定明确门槛；不得通过降低门槛掩盖回归。

## 13. Phase 9 — 最小 API 与部署完善

### 9A：最小 API（Phase 10A 后）

- [ ] 定义健康检查、任务提交、任务状态、审核/恢复和结果获取接口。
- [ ] 使用 Pydantic 定义请求、响应、错误和任务状态。
- [ ] 状态至少区分 pending、running、awaiting_review、completed、failed、cancelled。
- [ ] 明确第一版执行模式；本地单进程原型不得宣称具备分布式可靠任务能力。
- [ ] 检查任务归属；用户不能通过猜测 thread_id 或 task_id 读取、恢复其他任务。
- [ ] 验证提交、等待审核、拒绝、恢复、导出和错误路径。

**验收：** 一个调用方能通过接口完成小业务闭环；长任务状态可查询；敏感动作经过权限和审核检查。

### 9B：部署完善（业务流程稳定后）

- [ ] 完善认证、限流、并发限制、任务期限和取消语义。
- [ ] 明确取消是否只能阻止后续步骤；已完成副作用不能自动假装撤销。
- [ ] 制作 Dockerfile 和 Compose，配置持久化卷及 RAG 地址。
- [ ] CI 增加构建检查；验证 Linux 环境依赖与 Windows 环境差异。
- [ ] 验证容器重启后任务和审批状态可恢复，输出文件仍可访问。
- [ ] 补充日志、配置说明、启动停止步骤和常见错误排查。

**验收：** 干净环境按 README 可启动；核心 API 流程通过；密钥不进入镜像和日志；容器重启恢复成功。若未实现自动发布，交付称为 CI 与本地部署，不宣称完整 CD。

## 14. Phase 10 — RFP → SOC 毕业项目

### 10A：人工整理要求 → 有证据的 SOC（Phase 6 后优先）

- [ ] 准备一个真实型号、固定资料版本、10～20 条人工整理要求，以及人工核验答案。
- [ ] 包含满足、不满足、复合条款、缺证据、配置限制和冲突样例。
- [ ] 从 JSON 读取要求，完成检索、规则比较、拟议判断和人工审核。
- [ ] 实现 Excel 导出，保留原文、子要求、结论、理由、证据摘录、来源、页码及审核状态。
- [ ] 导出文件回读，核对条款 ID、行数、结论、链接及中文内容。
- [ ] 未审核结果明确标记为草稿；审核记录保存于应用，不能仅依靠 Excel 手工编辑。

**验收：** 全部样例逐条核查；无证据不 FC；未检索到不 NC；每个自动判断均能追溯适用证据；审核后导出与审核结果一致。

### 10B：增加 RFP PDF 输入

- [ ] 选择一份公开或脱敏、文本可提取的 RFP，先人工标注条款与页码。
- [ ] 实现 PDF 文本读取、条款编号与原文定位；保留原文和结构化内容两份表示。
- [ ] 型号允许由用户明确指定；不假设每条 RFP 自带设备型号。
- [ ] 将复合条款拆分，并记录父子关系；解析不确定时进入人工修正。
- [ ] 记录漏抽、错抽、单位变化和页码错误；修正后再进入判断流程。
- [ ] 用完整工作流生成 Excel，并与人工标注逐条对照。

**验收：** 条款提取覆盖率和错误有记录；关键要求没有静默遗漏；原文和位置可回查；扫描件与不支持布局明确返回限制。

### 10C：整体交付

- [ ] 用同一份资料通过 API 完成输入 → 判断 → 审核 → Excel。
- [ ] 中途暂停并重启恢复；重复审核或重试不会重复执行。
- [ ] 跑完整回归，保存环境、资料和评测版本。
- [ ] 提供演示输入、运行步骤、结果样例、限制和失败案例。
- [ ] 完成 Phase 9B 的部署验证后，才宣称应用可部署。

**验收：** 业务判断、证据、审核和运行轨迹能相互关联；他人能按文档复现；无证据和故障不会变成肯定结论。

### 14.1 最小数据契约

| 对象 | 最小字段 |
|---|---|
| Requirement | id、parent_id、原文、来源位置、对象/型号、属性、运算符、目标值、单位、适用条件 |
| Evidence | id、原文片段、文档标识、资料版本（未知则明示）、位置/页码语义、chunk_id（若有）、适用型号与条件、获取时间 |
| Decision | requirement_id、拟议状态、理由、evidence_ids、规则结果、缺失/冲突项、审核状态、审核版本 |
| Run / Review | run_id、task_id、thread_id、操作 ID、状态、配置版本、审核者、时间、修改内容 |

字段类型和必填规则在 Phase 4 实现。工具和模型输出须经过验证；不把自由文本说明当作已经执行了确定性规则的证明。

### 14.2 判定规则

| 状态 | 判定条件 |
|---|---|
| FC：完全满足 | 全部必要子要求有匹配证据，条件适用，规则确认满足，无未解决冲突 |
| PC：部分满足 | 子要求部分明确满足，部分明确不满足或存在已知限制；理由列明缺口 |
| NC：不满足 | 有适用证据明确证明必要要求不满足 |
| 待确认 | 证据缺失/冲突、要求含糊、型号/版本/配置不明，或工具故障导致无法核验 |

复合条款的汇总策略必须显式实现：全部子要求满足才 FC；若包含未解决的关键未知项，父条款先待确认并保留已知子项结果。PC 与 NC 的汇总还需结合该 RFP 的强制要求及业务口径，在正式使用前确认。

“支持”不等于“标配”；“最大能力”不等于“当前配置”；整机容量不直接替代特定测试条件下的性能。检索分数和模型自报置信度不能单独决定 FC/PC/NC。

## 15. 统一完成标准与证据管理

阶段标记 DONE 前必须满足：

- [ ] 必做任务完成；删减或延期有明确原因和影响。
- [ ] 存在可运行入口、依赖说明和实际验证命令。
- [ ] 相关离线测试通过；依赖真实模型、RAG 或部署的阶段另有真实验证。
- [ ] 能用自己的话说明核心机制，并解释一个失败案例。
- [ ] 日志记录结果、限制、待解决项和下一任务。
- [ ] 已生成本阶段 `docs/phaseNN_summary.md`，覆盖实际工作、核心概念、当前框架、验收、问题限制及下一步。
- [ ] 检查变更范围、敏感信息和旧工程未修改。
- [ ] 代码形成可追踪版本；提交/推送按用户授权执行，并如实记录未提交状态。

证据优先记录命令、结果摘要和文件路径；避免把长日志全部贴入本路线图。评测报告放 `eval/reports/`，技术说明放 `docs/`；本文只保留进度与关键结论。

后续优化或质量门槛改变必须记录原因，不覆盖或删除不利的历史评测结果。

### 15.1 每阶段必须生成的学习总结

这是固定实施规则：**每个 Phase 验收结束时，都必须在 docs 下生成一份独立 MD 总结；缺少总结时，不完成该阶段收尾。** 已完成的 Phase 0 已补齐。

- 命名为 `docs/phaseNN_summary.md`，使用两位编号，例如 `phase00_summary.md`、`phase01_summary.md`、`phase10_summary.md`。
- 按 [总结模板](docs/phase_summary_template.md) 编写，至少包含六项：做了什么、最重要的概念、当前框架、验收证据、问题与限制、下一步。
- 重点解释原理与代码的关系，面向学习者；包含关键文件链接和实际数据流/模块图，不仅列文件或命令。
- 内容必须基于实际实现，明确区分 mock、静态调查与真实运行；未知项不能省略或冒充成功。
- 总结保留阶段结束时的快照；后续能力写入后续阶段总结，当前进度只在本路线图维护。
- 9A/9B、10A/10B/10C 等子阶段可先记录部分成果，整个 Phase 验收时汇总成正式总结；延期或中断不标 DONE。
- 总结不替代验证报告、接口契约、学习日志或提交授权；已有详情通过链接引用。
- 生成文档后核查引用、图与代码一致性、验证结果和敏感信息，再按用户授权处理提交。

当前阶段总结：[Phase 0](docs/phase00_summary.md)、[Phase 1](docs/phase01_summary.md)。后续完成阶段时在此追加链接。

## 16. 学习日志

### 日志模板

```md
### YYYY-MM-DD — Phase X / 任务
- 状态：DOING / DONE / BLOCKED
- 学习目标与核心理解：
- 本次实现：
- 修改文件：
- 验证命令：
- 验证结果及证据路径：
- 真实依赖是否验证：模型 / RAG / 部署 / 不适用
- 已知限制或阻碍：
- Git 分支 / commit / 未提交：
- 下一任务：
```

### 2026-10-10 — 实施路线图建立

- 状态：规划完成；阶段实施未开始。
- 本次完成：根据原路线审阅结果建立 v2.0 实施版。
- 核心调整：提前调查 RAG 契约、贯穿业务样例、逐阶段评测、重启恢复、重复执行保护、明确判定规则、拆分业务闭环与部署。
- 已确认：本地已有 Git 初始化及远端配置，尚无提交。
- 未验证：远端实际状态、Python 环境、模型、RAG-DEMO 接口。
- 修改文件：`AGENT_LEARNING_ROADMAP.md`。
- Git：未提交。
- 下一任务：Phase 0，核对现有仓库及环境，定位 RAG-DEMO。

### 2026-10-10 — Phase 0 / 实际初始化与静态契约调查

- 状态：本地技术验证 DONE；阶段 BLOCKED，仅等待首个本地提交授权。
- 学习目标与核心理解：独立 venv 隔离依赖，pyproject 定义安装规则，src 布局配合 editable install；在工程外用 `-I` 导入验证真实安装，避免通过工作目录碰巧导入。
- 本次实现：可安装的 agent-demo 0.1.0、环境配置校验、无 LLM 示例、6 个离线测试；建立固定依赖清单并在第二个全新环境复现。
- 新建文件：README.md、.gitignore、.env.example、pyproject.toml、requirements-lock.txt、src/agent_demo/__init__.py、src/agent_demo/config.py、examples/phase00_hello.py、tests/test_phase00.py、docs/rag_contract.md、docs/phase00_validation.md。
- 修改文件：本路线图，仅更新实际事实、Phase 0 任务/状态、日志及 ADR；其余学习阶段未提前实施。
- 验证命令：`python -m venv .venv`；主环境使用 `pip --isolated install ... --no-build-isolation -e '.[dev]'`；随后运行 `.venv\Scripts\python.exe -m pytest -q`、`-m ruff check .`、`-m ruff format --check .`、`examples\phase00_hello.py`、`-m pip check`。
- 复现命令：创建 `.venv-phase0-check`，安装 requirements-lock.txt、执行 `pip --isolated install --disable-pip-version-check --no-cache-dir --no-build-isolation --no-deps -e .`，再运行相同验证。完整实际命令见 docs/phase00_validation.md。
- 结果：主环境 `6 passed in 0.31s`，复现环境 `6 passed in 0.17s`；两套 Ruff、示例和 pip check 均退出 0；外部依赖版本一致。
- 真实依赖验证：未调用 LLM；RAG 仅静态核实，没有导入模块、启动服务或请求 API；部署不适用。Python 版本兼容声明通过 PyPI 元数据查询核实。
- RAG 结论：旧工程位于 D:\workspace\AI\rag-demo；V1 无独立检索 HTTP 路由，V3 有认证 `/retrieve` 和 `/chat`；原文及文档/版本标识在源码中提供；型号专用字段未提供，真实数据/认证/响应仍待 Phase 6。
- 问题及修复：Git Schannel 错误改用命令级 OpenSSL；默认 pip 安装等待改用隔离配置/明确 PyPI/有限超时；freeze 的 VCS 警告改用 pip list 导出；旧仓库 ownership 检查使用命令级 safe.directory。完整失败与修复见验证记录。
- Git 状态：main 尚无提交；远端查询退出 0，无 HEAD/分支输出；index 为空，交付文件未跟踪；两套 venv、.env、runtime、outputs、日志和缓存忽略规则已核实。
- 旧工程状态：调查前后只读 `git status --porcelain` 均为空，本次未执行任何旧工程写操作。
- 建议 commit：`chore: initialize Phase 0 Python project and document RAG contract`。
- 下一任务：请求首个本地提交授权，推送另行确认；提交后复核 Phase 0 完成标准，再进入 Phase 1 选定实际模型、SDK 与 API 协议。

### 2026-10-10 — Phase 0 / 授权提交与验收收尾

- 状态：DONE。
- 用户授权：明确回复“授权本地提交及完成记录，不推送”。
- 本次完成：复核 Phase 0 清单、运行检查、提交范围和 Git 身份；创建本地根提交，并同步完成状态。
- 验证命令：主环境 `-m pytest -q`、`-m ruff check .`、`-m pip check`、`examples/phase00_hello.py`；Git `diff --cached --stat`、`diff --cached --name-only`、`status --short`；旧工程 `--no-optional-locks ... status --porcelain`。
- 结果：`6 passed in 0.33s`，Ruff/依赖检查/示例均成功；旧工程 Git 状态为空；初次暂存仅包含 12 个计划交付文件。
- Git 提交：`08dc5b4` — `chore: initialize Phase 0 Python project and document RAG contract`，12 个文件，1040 行；无 push。
- 本次修改文件：路线图、README、docs/phase00_validation.md；只更新状态、验收及交付记录。
- 权限处理：沙箱默认拒绝写 `.git/index.lock`；在已有用户授权基础上通过工具权限审查执行 git add/commit，未变更旧仓库或永久 Git 配置。
- 文档检查：初次 diff 检查指出 Markdown 顶部用于换行的行尾双空格；收尾改为显式 `<br>`，保持显示并消除该提示。
- 已知限制：真实 RAG 服务、凭据和业务资料未验证，属于 Phase 6；第二台电脑和 Linux 未验证；远端尚未推送。
- 下一任务：Phase 1 第一项，选定真实模型、SDK 与协议；本次不提前实施。

### 2026-10-10 — 固化阶段总结规则并补齐 Phase 0

- 状态：文档完成；Phase 0 仍为 DONE，Phase 1 未开始。
- 用户要求：每个 Phase 结束后在 docs 下生成总结 MD，说明工作、重点和当前框架。
- 本次完成：新增总结模板与 Phase 0 总结，把文档生成加入固定流程和统一完成标准。
- 修改文件：AGENT_LEARNING_ROADMAP.md、README.md、docs/phase_summary_template.md、docs/phase00_summary.md。
- 验证方式：对照现有代码与阶段证据核查内容和本地文件链接；仅文档变更，不重复运行代码测试。
- Git：本次文档变更尚未提交，未推送；不影响此前已完成的阶段代码提交。
- 下一任务：后续验收执行第 15.1 节；实施下一任务仍为 Phase 1 的模型/SDK/协议选择。

### 2026-10-10 — Phase 1 / 原生 Tool Calling 实施与真实验收

- 状态：DOING；技术验收通过，待本阶段本地提交授权，不推送。Phase 0 保持 DONE。
- 核心理解：模型仅提出请求，应用按白名单校验并执行，再按供应商协议回传结果。
- 实现：两个本地工具、Schema/Registry/Dispatcher、Gemini 官方 SDK 适配、单轮控制器、事件、真实/Mock 示例及 36 项新增测试。
- 修改文件：pyproject.toml、requirements-lock.txt、config.py、.env.example、README、本路线图；新增 tools/、agents/、integrations/ 实际模块、examples/phase01_tool_calling.py、tests/test_phase01.py、docs/phase01_tool_calling.md、docs/phase01_summary.md。
- 实际命令：`pip --isolated install --index-url https://pypi.org/simple --timeout 15 --retries 1 --disable-pip-version-check --no-cache-dir google-genai`；`pip ... --no-build-isolation --no-deps -e .`；主环境 pytest、Ruff check/format、pip check、Phase 0 示例、Phase 1 --mock；pip list 导出 35 个版本；新建 .venv-phase1-check 安装锁定清单、editable 包并重复检查。完整命令见技术说明第 4 节。
- 结果：两套环境各 42 passed，Ruff/依赖/离线示例通过。无密钥真实入口退出 1 configuration_error，不误报成功。
- 真实依赖：用户明确授权只读复用旧工程 Gemini 密钥，仅在进程中使用。真实示例的加法、MOCK-SW-48 和 Hello 均 completed/退出 0；模型与响应版本 gemini-3.5-flash-lite，SDK google-genai 2.29.0。未请求真实 RAG 或部署。
- 轨迹：加法 run_id=bfff1900fe34464d8f0869823e2318dc，call_97714 / add(15,27) → 42 → 最终回答；规格 call_42746 / lookup_product_spec → MOCK 48GE+4×10GE；问候无工具调用。完整 JSON 位于忽略目录 outputs/，文档保留脱敏摘录。
- 失败修复：Ruff 长行、无用导入与文档代码块格式失败后修复；最新别名两次 ServerError，改选稳定模型；SDK 示例 tool 角色回传导致真实 HTTP 400，按安装版 Content 约束改为 user 并补断言，真实闭环通过。历史失败保留在技术说明，不以 Mock 代替真实验收。
- 限制：只有一轮工具，同轮至多四项顺序执行；无持续循环、预算/usage 累计或复杂工具超时取消；规格为 MOCK；其他平台和模型组合未验证。
- Git：当前 phase-1，HEAD c3e5f2e；远端 main/phase-1 查询成功且一致。本阶段未 add/commit/push；旧工程只读 status --porcelain 为空；敏感内容未进入跟踪范围。
- 建议 commit：`feat: implement manual Gemini tool calling with validated local tools`。
- 下一任务：授权本地提交及完成记录，然后 Phase 2 的有上限模型/工具循环；当前不提前实现。

### 2026-10-10 — Phase 1 / 授权本地提交与验收收尾

- 状态：DONE。用户明确授权“Phase 1 本地提交及完成记录，不推送”。
- 复核：提交前为 phase-1 / c3e5f2e，变更与前次交付一致；暂存仅 15 个已核查文件，cached diff --check 通过，无密钥、虚拟环境或运行数据。
- 实现提交：`7a67a36` — `feat: implement manual Gemini tool calling with validated local tools`，15 个文件，1021 行新增、22 行删除。
- 完成记录：更新顶部、进度总览、完成日期、Phase 1 验收项、阶段总结、技术说明和 README；保留等待授权与失败修复的历史日志，完成记录另提交。
- 验证依据：此前两套环境各 42 passed，Ruff/pip check/离线示例通过；真实 Gemini 加法、MOCK 规格与问候通过。此次仅状态文档变更，不重复 API 或代码测试，检查文档格式、差异及最终 Git 状态。
- 收尾修复：首个文档更新脚本因 PowerShell 管道使用 ASCII，匹配中文失败，未写入任何文件；改用直接 UTF-8 补丁更新。
- 权限：按本阶段授权通过工具权限审查写入新工程 Git 索引和本地历史；没有 push，没有修改旧工程。
- 下一任务：Phase 2 首项——实现有轮数、调用数与总期限上限的 Agent Loop；本次不提前实施。

### 2026-10-10 — Phase 3 / LangChain 标准 Agent

- 状态：DOING；技术验收完成，待本地提交授权。
- 实现：LangChain 1.4.4 `create_agent`、Google Gemini 集成 4.4.0、两个复用 Dispatcher 的 Tool 包装、Pydantic `AgentAnswer`、真实与离线验证。
- 修改文件：pyproject.toml、requirements-lock.txt、README、本路线图；新增 `src/agent_demo/agents/langchain_agent.py`、`examples/phase03_langchain_agent.py`、`tests/test_phase03_langchain_agent.py`、`docs/phase03_langchain_agent.md`、`docs/phase03_summary.md`。
- 验证命令：主环境 `pytest -q`、`ruff check .`、`ruff format --check .`、`pip check`、Phase 2 Mock 示例、Phase 3 真实示例；结果 49 passed，静态检查和依赖检查通过。
- 真实验证：Gemini `gemini-3.5-flash-lite` 通过 LangChain Agent 完成 MOCK-SW-48 查询与总端口计算，Pydantic 结构化结果 total_ports=52，退出码 0。密钥仅在授权的进程环境使用，不写入工程。
- 对比结论：LangChain 管理模型消息、工具往返和循环节点；白名单、业务校验、错误、超时、预算和敏感日志仍由应用负责。`recursion_limit` 是图步骤上限，不等于工具次数。
- 限制：CI 文件/真实 runner 尚未单独执行；未实现 Phase 4 显式图、Phase 5 checkpoint、Phase 6 RAG。旧 RAG 工程未修改。
- Git：当前 phase-3，工作区包含 Phase 3 变更，未 add/commit/push。建议 commit：`feat: add LangChain standard agent implementation`。
- 下一任务：获得本地提交授权后进入 Phase 4 Requirement、Evidence、Decision 模型与显式工作流。

## 17. 架构决策记录（ADR）

| ID | 日期 | 决策 | 原因 | 复审点 |
|---|---|---|---|---|
| ADR-001 | 2026-10-10 | 新工程与 RAG-DEMO 独立，旧项目只读 | 保持服务和学习边界 | Phase 6 契约缺口 |
| ADR-002 | 2026-10-10 | 先手写工具调用与循环，再使用框架 | 理解真实执行层和终止控制 | Phase 3 |
| ADR-003 | 2026-10-10 | 原生与框架共用业务工具、模型和用例 | 避免两套业务规则分叉 | Phase 3–4 |
| ADR-004 | 2026-10-10 | Phase 0 提前摸底 RAG，Phase 6 正式集成 | 早发现证据字段缺口 | Phase 6 |
| ADR-005 | 2026-10-10 | 先 JSON 要求到 SOC，再加入 PDF 输入 | 分离解析难题与判断难题 | Phase 10B |
| ADR-006 | 2026-10-10 | Phase 5 验证持久化与重复执行保护 | 内存暂停不足以证明重启恢复 | Phase 9B |
| ADR-007 | 2026-10-10 | MCP 为独立实验 | 不额外增加业务主链路依赖 | Phase 7 |
| ADR-008 | 2026-10-10 | 安全、日志和评测随阶段建设 | 保留早期基线并减少返工 | Phase 8 |
| ADR-009 | 2026-10-10 | 第一版固定版本资料、单型号、小样本 | 控制范围并支持人工逐条核验 | M3 |
| ADR-010 | 2026-10-10 | Phase 0 技术验收与 Git 授权分开记录；默认不提交/推送 | 用户明确要求提交和推送先确认；技术通过不冒充版本交付完成 | 首个本地提交确认 |
| ADR-011 | 2026-10-10 | 当前选择 Python 3.11 系列；依赖用 pip list 排除 editable 导出 | 本机 3.11.0 可用且满足已查声明；pip freeze 在无提交仓库仍触发 VCS 警告 | Python 补丁升级或 Phase 3 引入框架 |
| ADR-012 | 2026-10-10 | 每阶段验收生成 docs/phaseNN_summary.md，按模板讲解工作、重点与框架 | 用户要求固定保存阶段学习知识，便于复习与后续推进 | 每个 Phase 验收 |
| ADR-013 | 2026-10-10 | Phase 1 使用 google-genai 2.29.0 / gemini-3.5-flash-lite，关闭自动执行；结果用 user 角色，保留 ID 和原始 Content | 最新别名两次 ServerError；稳定型号真实通过。SDK 示例 tool 角色被 API 400 拒绝，安装版 Content 只支持 user/model；以真实协议为准 | Phase 2 或模型/SDK 更新 |
| ADR-014 | 2026-10-10 | Phase 3 使用 LangChain 1.4.4 `create_agent` 与 langchain-google-genai 4.4.0；业务函数仍通过 Phase 1 Dispatcher 执行 | 学习框架控制层，同时保持业务权限边界单一；`recursion_limit` 不冒充工具预算 | Phase 4 或依赖升级 |

## 18. 官方资料与版本核实

- LangChain Agent：https://docs.langchain.com/oss/python/langchain/agents
- LangGraph：https://docs.langchain.com/oss/python/langgraph/overview
- LangGraph 持久化：https://docs.langchain.com/oss/python/langgraph/persistence
- LangGraph 中断与恢复：https://docs.langchain.com/oss/python/langgraph/interrupts
- MCP：https://modelcontextprotocol.io/docs/getting-started/intro
- FastAPI：https://fastapi.tiangolo.com/
- pytest：https://docs.pytest.org/

本路线制定时核对了 LangChain Agent、LangGraph 持久化与中断文档。其他库在引入阶段再核实官方文档和兼容版本；链接内容更新不代表本地依赖自动升级。

**Phase 0、Phase 1 已完成。下一任务是 Phase 2 有上限的 Agent Loop；推送仍需另行确认。**
