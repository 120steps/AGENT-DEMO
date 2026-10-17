# AGENT-DEMO — Agent 学习与工程实施路线图

> 版本：v2.0，实施版<br>
> 更新日期：2026-10-17<br>
> 当前状态：**全阶段整合DOING；本地SOC/API/PDF软件可运行，真实毕业及Docker验收BLOCKED**<br>
> 当前阶段：**Phase2/3控制补齐；16行MOCK SOC、真实本机HTTP重启及审核导出通过；Phase6真实条件仍缺失**<br>
> 下一任务：**核查本次整合版本；提供安全RAG、固定版本产品资料、真实RFP及10–20条人工核对要求，在Docker环境完成实际部署与最终验收。不推送、不发布客户文件。**<br>
> 唯一进度入口：本文件。后续按本文任务与验收证据推进。<br>
> 边界：AGENT-DEMO 独立开发；RAG-DEMO 只读检查，未经明确授权不修改。

## 0. 使用方式与当前事实

本文是学习和实施计划，不代表功能已经实现。任务完成后必须记录验证证据，不能仅凭代码生成或文件存在标记 DONE。

### 0.1 已确认的工程事实

截至 2026-10-17 的本地检查：

- 本次全阶段整合起点为`phase-4 / 9cea417`，工作区干净。完整审计见`docs/project_completion_audit.md`。用户明确同意“尚未具备，先完成软件和隔离测试，真实验收保留BLOCKED”，因此允许在保留真实前提的同时实施Phase9/10本地软件；不将MOCK写成毕业通过。
- 初始394 passed / 1 failed / 1 skipped；失败为Windows低分辨率期限判断，改用perf_counter修复，保留原失败XML。原生Loop超时等待、SDK输出配置、消息重复回传和LangChain独立预算/类型边界已补齐，实际新回归见最新日志。
- 增加SOC应用、文本PDF定位与人工确认、受审核范围绑定的XLSX草稿、任务归属/限流/有界队列API。实际本机HTTP18项验收通过，含两次进程重启、修改重审和重复下载字节核对。真实设备/RAG/RFP与容器部署未验证，尚未自动提交本次修改。

以下为Phase8收尾时的同日记录：

- Phase8开始时分支`phase-4`、HEAD `e82f69a`，工作区干净，Phase7实现与完成记录已存在。用户随后明确授权Phase8本地提交及完成记录，实现提交`0fb559e`已创建，完成记录另提交；未推送。
- Phase8统一48条用例，44条实际执行PASS、3条真实LLM与1条真实RAG/PDF因缺配置BLOCKED；不计入通过率。工具16/18执行成功，状态18/18正确，三项安全违规均0，仅代表明确测试范围。
- 完整395 passed / 0 failed / 1 skipped（78.25s），新增34与原361全部通过；Ruff/format/pip check通过，既有76项依赖不变。Trace、运行历史及pytest XML位于outputs，脱敏基线位于eval/reports，旧RAG保持只读。

以下为Phase7收尾时的同日记录：

- 当前分支 `phase-4`；本次开始时 HEAD `378f948`、工作区干净，已包含 Phase 6 提交 `aaf6c8f`。Phase 7 经用户明确授权形成实现提交 `2f6fd60`，完成记录另提交；不改变既有历史，不推送。
- 官方 MCP Python SDK 2.3.0 实际安装兼容当前 Python 3.11.0、Pydantic 2.14.0、LangChain 1.4.4。原61个依赖版本未变，新增15项，固定清单76项；本地 stdio 实际协商到 2026-07-28。
- Phase 7 的50项专项测试通过；完整回归361 passed / 0 failed / 1 skipped（60.19s），包含原Phase0–6的311项通过。真实stdio、脚本模型create_agent→MCP和进程清理验证完成；真实模型Key不可用，未调用LLM，唯一跳过仍为Phase6真实服务/PDF验收。
- 旧 RAG-DEMO 未启动、未修改，只读 Git 前后干净；Phase 6 继续 BLOCKED。用户已授权 Phase 7 本地提交及完成记录，不推送；统一版本收尾完成，Phase 7 标记 DONE。

以下 2026-10-14 的本地检查作为历史保留：

- 当前分支 `phase-4`，HEAD `9260a54`（`phase 5`），本次开始时工作区干净。Phase 5 已提交；既有 164 项测试在新回归中全部通过，另验证原 2026-10-13 已保存任务仍能核验为 completed。
- Phase 6 完整 pytest 为 311 passed / 0 failed / 1 skipped；唯一跳过的是安全真实服务/设备 PDF 未配置的 opt-in 验收。HTTP Mock、脚本 Chat Model、TEST PDF、真实本机关闭端口错误检查分别标注，不冒充真实 RAG 请求。
- RAG-DEMO 当前 HEAD `d72c329`，只读 Git 前后干净，当前未发现 8000/8011 监听；V3 `/retrieve` 及下载/启动可能写旧运行数据。未导入、启动或调用旧服务，没有读取旧凭据或修改旧项目。
- 当前进程没有 RAG URL/Token 或 Gemini API Key；无授权真实设备资料与固定 PDF 绑定。Phase 6 客户端/流程可离线运行，真实端到端与评测保持 BLOCKED。

以下 2026-10-13 检查作为历史保留：

- 当前分支 `phase-4`，HEAD `9e4a8f3`（`phase 4`），任务开始时工作区干净。Phase 4 已形成版本，原 98 项测试复核通过，正式收尾 DONE。本次未查询远端，不声称实时推送状态。
- Phase 5 完整回归 164 passed / 0 failed / 0 skipped（原 98 + 新增 66）；SQLite 真实独立进程退出/恢复、审核版本、拒绝无写入、真实文件发布后进程异常恢复、幂等性、Thread/Store 边界通过。实际 CLI 证据：`runtime/phase05/validation-20261013-d63b2cb0.json`，运行数据保持忽略；Phase 5 尚未提交。
- 本次复用 Phase 4 完整业务图，不复制比较规则；没有访问或修改 RAG-DEMO，没有真实 LLM 调用，没有 MCP/API/Docker 实现。Phase 6 的真实服务和证据资料前提尚未验证。

以下 2026-10-11 检查作为历史保留：

- 当前分支 `phase-4`，HEAD `757f3f3`；历史包含 Phase 2 的 `d93d59a` / 合并 `ec763bf`，Phase 3 的 `d785bc3` / 合并 `757f3f3`。此前“待提交”的描述已过时；本次未查询远端，不把本地合并记录当作实时远端状态。
- Phase 4 完整回归 98 passed / 0 failed，Ruff、pip check、五类离线图 Demo 通过；代码和文档尚未提交。继续时检测到用户已暂存昨日代码，保留暂存状态，不自动 add/commit/push。
- Phase 3 当前执行限制与旧验收声明存在差异，详见第 16 节 2026-10-11 纠正说明；不因本次 Phase 4 测试通过就宣称这些旧限制已补齐。

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
| 2 | 原生 Agent Loop | DOING | 历史版本保留；本次补齐实际等待/输出配置/消息重复，待整合版本 | — |
| 3 | LangChain 标准 Agent | DOING | 本次补齐独立预算/期限/严格Schema及同题对照，待整合版本 | — |
| 4 | LangGraph 显式工作流 | DONE | 98 项验证记录保留；实现提交 9e4a8f3，本次复核通过 | 2026-10-13（复核） |
| 5 | Checkpoint、恢复、人工审核 | DONE | 实现提交 9260a54；164 项回归及既有审核快照兼容复核通过 | 2026-10-14（复核） |
| 6 | 真实 Agentic RAG | BLOCKED | HTTP/Tool/真实证据路径与离线评测机制完成；311 passed，真实服务/PDF/实测缺失 | — |
| 7 | MCP 独立实验 | DONE | v2真实stdio、Agent与50项专项通过；授权实现提交2f6fd60 | 2026-10-17 |
| 8 | 评测、安全、可观测性汇总 | DONE | 本地范围：48用例44PASS/4BLOCKED；本次增加系统覆盖，真实质量延期见ADR-035 | 2026-10-17 |
| 9 | 最小 API 与部署完善 | BLOCKED | 9A真实本机HTTP通过；9B材料/CI已实现，Docker/Linux实际验证缺环境 | — |
| 10 | RFP → SOC 毕业项目 | BLOCKED | JSON/PDF人工映射→审核→XLSX已通过MOCK；真实业务/文档/部署验收缺失 | — |

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
- [x] 保留执行次数、超时和预算约束；2026-10-17补齐ExecutionGuard与实际等待测试，递归步数仅额外保护，旧不足记录保留。
- [x] 使用同题脚本对照直接回答/同轮多工具/多轮任务，检查结果和动作；Phase8三样本Benchmark保留调用/延迟，预算与禁止动作专项通过。只证明离线控制，不扩大真实质量声明。
- [x] 记录原生实现与框架实现的消息、工具执行、middleware 和终止机制对照。

**交付：** `examples/phase03_langchain_agent.py`、对照笔记及验证记录。

**验收：** 两种实现均完成核心任务；非法工具和错误参数不会绕过业务边界；不要求真实模型输出逐字相同或轨迹顺序完全一致。

**2026-10-10 实际结果：** `langchain==1.4.4`、`langchain-google-genai==4.4.0` 已安装并锁定；主环境 49 passed，Ruff/format/pip check 通过。真实 Gemini LangChain Agent 完成 MOCK-SW-48 查询与总端口计算，Pydantic 输出为 52，退出码 0。阶段总结见 [docs/phase03_summary.md](docs/phase03_summary.md)，技术说明见 [docs/phase03_langchain_agent.md](docs/phase03_langchain_agent.md)。仅剩本地提交授权，暂不标记 DONE。

## 8. Phase 4 — LangGraph 显式工作流与业务模型

**学习问题：** 哪些决策交给模型，哪些流程和规则应由代码固定？

**必做任务**

- [x] 定义 Requirement、Evidence、Decision 三类 Pydantic 数据模型。
- [x] 将复合条款拆成可分别核验的子要求；保留父条款 ID、原文及位置。（人工结构化输入，保留 mandatory。）
- [x] 建立提取或读取要求 → 查询证据 → 校验 → 判断 → 输出的显式图。
- [x] 设置有证据、缺证据、冲突、工具失败路径；判断前执行确定性校验。
- [x] 将数值、单位、比较运算和字段完整性检查交给代码。
- [x] 理解 State 更新、消息合并及 reducer，避免重试造成重复追加。（顺序图采用默认替换 reducer 和 ID 字典，不引入聊天消息。）
- [x] 画出流程图，离线覆盖每条关键分支。

**交付：** `examples/phase04_langgraph_workflow.py`、共用业务模型、条件分支测试。

**验收：** 缺证据不生成肯定结论；工具失败不等同于设备不满足；冲突进入待确认；数值规则可独立验证。

**2026-10-11 实际结果：** 技术验收通过，98 passed（Phase 0–3 原有 49 + Phase 4 新增 49），Ruff/pip check/editable 安装及 Demo 通过。五类 MOCK 场景分别 FC、NC、PENDING、PENDING、PENDING；工具失败 ERROR；未知优先保留 PENDING。原工具的介质字段缺失，完全满足场景使用单独标注来源的人工 MOCK 补充证据。技术文档及 Mermaid 见 [docs/phase04_langgraph_workflow.md](docs/phase04_langgraph_workflow.md)，总结见 [docs/phase04_summary.md](docs/phase04_summary.md)。没有真实 LLM/RAG 调用。当时授权本地提交前保持 DOING。

**2026-10-13 收尾复核：** 本地历史已存在实现提交 `9e4a8f3`，工作区起始干净，98 项既有测试及五场景 Demo 复核通过，Phase 4 标记 DONE；保留当时待提交的日志与总结快照。

## 9. Phase 5 — Checkpoint、重启恢复与人工审核

**学习问题：** 如何恢复任务，并避免恢复、重试或重复审批导致再次写入？

**必做任务**

- [x] 区分消息上下文、checkpoint、跨 thread store 和业务数据库。
- [x] 先演示内存 checkpoint，再接入本地持久化 checkpoint。
- [x] 验证同一 thread 连续性、新 thread 隔离，以及停止进程后的恢复。（独立 Python 进程真实验证。）
- [x] 将待审核内容明确保存为具体要求、证据、判断及拟执行动作。
- [x] 拆分准备、审核和执行节点；理解 interrupt 恢复可能重跑节点。
- [x] 对写入动作使用操作 ID 和重复执行保护；设计输出文件重复生成策略。
- [x] 测试批准、拒绝、修改后重新校验；影响范围改变时重新审核。
- [x] 测试重复恢复、重复提交审批，以及执行后重试不会重复产生业务结果。
- [x] 用最小例子展示跨 thread store 的存取；记录其与业务状态的区别。
- [x] 明确 thread_id 不是授权凭据，服务化时必须检查任务归属。

**交付：** `examples/phase05_checkpoint_hitl.py`、持久化恢复与审核测试。

**验收：** 关闭程序后恢复成功；拒绝后无受保护写入；重复审批/恢复不重复执行；新 thread 无上下文串线。

**2026-10-13 实际结果：** 技术验收通过。主环境 164 passed / 0 failed / 0 skipped；InMemorySaver 两独立进程证明状态丢失，SqliteSaver 三独立进程 start/status/resume 恢复同一快照；文件已发布但账本/Checkpoint 未完成时 `os._exit()` 后安全恢复，文件字节和修改时间不变。Approve/Reject/Modify、旧版本拒绝、输出路径及 NTFS junction 防护、完成产物被删改后拒绝重复审批、并发操作去重通过。CLI 的配置修改由 PENDING → 新审核版本 2 / FC → 批准 completed；文件仍为 MOCK DRAFT。说明、Mermaid、实际证据及限制见 [技术文档](docs/phase05_checkpoint_hitl.md) 和 [总结](docs/phase05_summary.md)。代码未提交，按第 15 节保持 DOING；未消耗真实模型 Token。

**2026-10-14 收尾复核：** 已存在本地提交 `9260a54`，既有 164 项测试通过，Phase 5 标记 DONE。Phase 6 扩展业务模型时新增实际 SQLite 旧快照恢复测试：仅规范化新可选默认字段作比较，不修改原快照摘要或已生成文件，保留既有数值理由。历史未提交记录按原日期保留。

## 10. Phase 6 — 真实 Agentic RAG 集成

**学习问题：** 如何让模型决定检索，同时让证据和权限保持可核验？

**进入条件：** Phase 0 的契约已核实，真实服务可以返回足够的证据信息。无法满足时，明确阻碍；可以完成客户端离线开发，但不得标记真实集成 DONE。

**必做任务**

- [ ] 更新 `docs/rag_contract.md`，保存脱敏响应样本和实际错误场景。（源码契约/副作用已更新；真实响应样本待安全服务。）
- [x] 编写 RAGClient 与 `search_knowledge_base` 工具，限定服务地址、参数范围、超时及重试。（离线 API/框架实际运行通过。）
- [ ] 将真实响应映射到 Evidence；缺失字段显式标注，不自行补造页码或原文。（代码和模拟契约验证完成；真实响应待验收。）
- [x] 保留文档 ID、版本/哈希（可获得时）、原文片段、chunk_id、页码语义和适用型号/条件。（离线字段映射验证；缺失保留 None。）
- [x] 对一般问候允许直接回答；设备合规判断必须经过证据流程。（脚本模型验证调用机制；真实 LLM 待验证。）
- [x] 支持有限次数的查询改写和补充检索；证据不足后停止并返回待确认。（实际 create_agent 图、脚本响应验证上限。）
- [x] 测试空结果、接口故障、字段缺失、来源冲突和引用不匹配。
- [x] 加入检索内容中的提示注入样本，验证其不能改变工具权限。（执行白名单/消息角色/业务门禁验证，不宣称模型对所有注入免疫。）
- [ ] 比较一次固定检索基线与 Agentic RAG 的任务效果、调用数和延迟。（六类离线控制实验完成，真实同题评测未完成。）
- [x] 分别记录 Mock API 测试与真实服务端到端结果。（真实端到端明确 BLOCKED，没有冒充通过。）

**交付：** RAGClient、真实引用样例、Agentic RAG 评测用例与报告。

**验收：** 真实 PDF 引用可回查且页码解释明确；服务不可用时返回可诊断状态；无证据不生成 FC；旧项目未被修改。

**2026-10-14 实际结果：** BLOCKED。实现和离线验证完成：311 passed / 0 failed / 1 skipped；原 Phase 0–5 的 164 项包含其中。服务契约及副作用更新、HTTP 客户端、受限 Tool、LangChain Agent、真实 Evidence 模型路径、原业务图及审核集成完成。pypdf 实际 TEST PDF 验证不等于真实服务 PDF 回查；真实 HTTP/PDF/同题评测都未通过。详见 [技术说明](docs/phase06_agentic_rag.md)、[总结](docs/phase06_summary.md)、[对比记录](eval/reports/phase06_baseline.md)。旧仓库保持只读，本次不启动、不索引、不修改旧数据。

## 11. Phase 7 — MCP 独立实验

**定位：** 学习标准化工具发现与调用；不强制用 MCP 改造已稳定的 HTTP 集成。

**必做任务（选择实施本阶段时）**

- [x] 理解 Host、Client、Server 及工具发现；技术文档有架构与时序图。
- [x] 核实官方稳定 SDK 2.3.0，使用 v2 MCPServer / Client，真实 stdio 暴露既有两工具。
- [x] 实际 server/discover 协商2026-07-28、发现、调用、结构化/文本结果解析及进程退出清理。
- [x] 校验工具名称、原参数 Schema、业务结果；Host 允许列表独立于发现集合。
- [x] 真实测试启动失败/超时、服务退出、调用超时、协议错误、工具错误及无效返回。
- [x] 实际 create_agent 经 MCP 使用共用工具，Phase 3 原直接工具保持共存；模型为离线脚本，通信为真实 stdio。
- [x] 对比 Python 函数、HTTP API 与 MCP 的职责、开销、错误和权限。
- [x] 生成技术文档 `docs/phase07_mcp.md` 和固定阶段总结 `docs/phase07_summary.md`。
- [x] 经用户明确授权创建本阶段实现提交 `2f6fd60`，完成统一标准第15节的版本收尾；完成记录另提交，不推送。

**2026-10-17 实施记录：** 50项专项通过；Client add(15,27)=42、MOCK规格查询、Agent lookup→add(48,4)=52均通过真实stdio运行。SDK内存连接、真实子进程和脚本模型分别标注；无有效模型Key，真实LLM未验证且不冒充。最终回归与版本状态见第16节。

**最终验收结果：** 完整361 passed / 0 failed / 1 skipped；Ruff、格式和pip check通过。用户随后明确授权本地提交及完成记录，实现提交 `2f6fd60` 已建立，Phase 7 标记 DONE；未推送。真实LLM未验证的限制保留，不影响已通过的本地MCP实验验收。

**扩展任务：** 远程 HTTP 传输及认证单独实施，不阻塞本地实验。

**验收：** Agent 能通过 MCP 调用共用工具，失败可诊断，子进程可清理。若延期，标记 DEFERRED 并记录原因；不把延期实验写成已实现。

## 12. Phase 8 — 评测、安全与可观测性汇总

**定位：** 汇总此前的测试和事件，不重新从零建设。

**必做任务**

- [x] 汇总 `eval/agent_test_cases.json`，保留旧六案例并增加48条结构化统一用例及各字段。
- [x] 分开报告offline_mock、mcp_stdio、mcp_memory、real_llm、real_rag；未运行真实用例BLOCKED，不计通过率。
- [x] 记录UTC时间、Git/dirty状态、Python/依赖、模型标记、控制器/Prompt Hash、数据集Hash与资料范围；未知实际模型/真实文档不推断。
- [x] 实际计算任务/工具/状态/引用、调用数及可观测延迟；usage缺失与价格未核实保持unavailable，不捏造费用。
- [ ] 关键真实模型三次代表性重复测量：当前无Key，三条BLOCKED，波动未测；延至真实条件具备后，不标PASS。
- [x] 扩展未知工具、参数、预算、有限重试、路径与覆盖保护、注入、服务故障、版本/重复审核与幂等验证，实际执行权限及文件副作用。
- [x] 统一payload-free JSONL及run/thread/调用ID关联，使用原event_sink与SDK Callback定位Node/Model/Tool，导入事件明确时间含义。
- [x] 输出非覆盖基线JSON/Markdown，保留初次43/44失败产物，提供回放、分母和下一步限制。
- [x] CI增加离线Evaluation硬门槛；安全回归包含于完整pytest，已本地验证退出码；未运行远端CI。
- [x] 生成技术文档与固定阶段总结。
- [x] 经本阶段明确授权形成本地实现提交`0fb559e`，完成记录另提交；不推送。

**2026-10-17 本地验收：** 48条中44PASS、4BLOCKED；执行工具16/18成功、状态18/18正确、接受引用成员/来源6/6，TEST PDF候选1/2（错页被拒绝），真实PDF指标无样本。未授权写入/无证据FC/接受伪造引用均0。完整395 passed / 0 failed / 1 skipped；专项34passed。真实质量重复测量延期的原因和影响见ADR-035，不把本地控制结果当作真实模型质量。

**硬性验收：** 离线控制逻辑测试全部通过；选定测试集中未授权写入、无证据 FC、伪造引用为 0；所有这些结果必须标注测试范围，不能推广成对任意输入的绝对保证。

**收尾状态：** 用户明确授权本地提交及完成记录，21个文件的实现提交`0fb559e`已建立。Phase8按ADR-035限定的本地交付范围标记DONE；上方真实重复测量复选框保持未勾选、4个真实用例仍BLOCKED，Phase6状态与后续业务进入条件不变。

真实模型成功率等质量指标先测基线，再在扩展前制定明确门槛；不得通过降低门槛掩盖回归。

## 13. Phase 9 — 最小 API 与部署完善

### 9A：最小 API（Phase 10A 后）

- [x] 定义健康检查、任务提交、任务状态、审核/恢复和结果获取接口，实际本机HTTP验证。
- [x] 使用Pydantic定义输入、状态响应及审核；错误响应使用固定类型，不回显敏感输入。
- [x] 区分pending、running、awaiting_review、completed、failed、cancelled；拒绝动作保存在审核记录。
- [x] 明确单服务进程/单任务线程/有界队列；不宣称分布式调度，重启后pending任务需显式run。
- [x] Bearer身份与SQLite owner绑定；他人任务的状态/run/cancel/export均实际404。
- [x] 实际HTTP验证提交、审核、拒绝、修改、新版本、重复批准、进程重启及XLSX获取；目前业务资料MOCK。

**验收：** 一个调用方能通过接口完成小业务闭环；长任务状态可查询；敏感动作经过权限和审核检查。

### 9B：部署完善（业务流程稳定后）

- [x] 本地Bearer认证、每身份限流、有界并发/队列、任务等待期限、取消状态及归属验证已测试；不宣称生产身份系统。
- [x] 取消仅协作式阻止后续步骤，已完成副作用不能假装撤销；实际并发取消测试通过。
- [x] 制作Dockerfile/Compose及隔离上下文，配置非root、只读根目录、持久化卷及固定RAG配置；仅材料静态核查。
- [ ] CI 增加构建检查；验证 Linux 环境依赖与 Windows 环境差异。
- [ ] 验证容器重启后任务和审批状态可恢复，输出文件仍可访问。
- [x] 补充日志、配置、单进程启动/停止与恢复说明，详见docs/phase09_api.md；远端CI及容器实际状态不推断。

**验收：** 干净环境按 README 可启动；核心 API 流程通过；密钥不进入镜像和日志；容器重启恢复成功。若未实现自动发布，交付称为 CI 与本地部署，不宣称完整 CD。

## 14. Phase 10 — RFP → SOC 毕业项目

### 10A：人工整理要求 → 有证据的 SOC（Phase 6 后优先）

- [ ] 准备一个真实型号、固定资料版本、10～20 条人工整理要求，以及人工核验答案。
- [ ] 包含满足、不满足、复合条款、缺证据、配置限制和冲突样例。
- [x] JSON软件链路已完成并通过MOCK及HTTP Mock+TEST PDF测试；真实检索验收仍BLOCKED。
- [x] Excel软件导出完成，保留原文/结构化子要求、理由及缺失/冲突项、来源版本、位置、审核人/版本；字面文本防公式注入。
- [x] 16行MOCK文件回读核对ID/行数/状态/中文和内部证据跳转；三张表完成实际渲染检查，非真实业务验收。
- [x] 未审核及本地已批准结果都标DRAFT；审核与export_policy存于应用/Checkpoint，作用范围变化重新审核，拒绝/取消禁止导出。

**验收：** 全部样例逐条核查；无证据不 FC；未检索到不 NC；每个自动判断均能追溯适用证据；审核后导出与审核结果一致。

### 10B：增加 RFP PDF 输入

- [ ] 选择一份公开或脱敏、文本可提取的 RFP，先人工标注条款与页码。
- [x] 文本PDF读取/编号候选/物理页/行号/Hash及未分配文本已实现和TEST PDF验证；原文与人工结构化输入分别保留。
- [x] 型号由调用方明确指定并核查单型号；不从RFP猜测型号。
- [x] 人工映射提供Pydantic父子结构，未知候选必须映射或说明排除原因；不是通用LLM自然语言拆分。
- [ ] 记录漏抽、错抽、单位变化和页码错误；修正后再进入判断流程。
- [ ] 用完整工作流生成 Excel，并与人工标注逐条对照。

**验收：** 条款提取覆盖率和错误有记录；关键要求没有静默遗漏；原文和位置可回查；扫描件与不支持布局明确返回限制。

### 10C：整体交付

- [ ] 用同一份资料通过 API 完成输入 → 判断 → 审核 → Excel。
- [x] 本地MOCK完整链路中途暂停、两次重启、重复审核/重试不重复发布；真实业务/容器仍需独立验收。
- [x] 完整回归与评测已保存新证据目录，保留旧基线和失败XML；版本清单80项Windows已核对。
- [x] 提供16行MOCK输入、预期答案、CLI、实际HTTP验收、XLSX样例、操作文档及明确限制；未冒充真实交付样例。
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

当前阶段总结：[Phase 0](docs/phase00_summary.md)、[Phase 1](docs/phase01_summary.md)、[Phase 2](docs/phase02_summary.md)、[Phase 3](docs/phase03_summary.md)、[Phase 4](docs/phase04_summary.md)、[Phase 5](docs/phase05_summary.md)、[Phase 6](docs/phase06_summary.md)、[Phase 7](docs/phase07_summary.md)、[Phase 8](docs/phase08_summary.md)。总结保留各自快照，存在总结不等于当前阶段DONE，实时进度以上表为准。

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

### 2026-10-11 — Phase 4 / 显式业务图实现及技术验收

- 状态：DOING，技术验收通过；本阶段尚未提交，不自动 push。
- 修改文件：`src/agent_demo/domain/{requirements,evidence,decisions,mock_cases}.py`、`src/agent_demo/graphs/compliance_graph.py`、`examples/phase04_langgraph_workflow.py`、`tests/test_phase04_langgraph_workflow.py`；pyproject.toml、requirements-lock.txt、`.github/workflows/ci.yml`、README、本路线图；`docs/phase04_langgraph_workflow.md`、`docs/phase04_summary.md`。
- 实现：人工条款拆分；结构化 State；逐条校验、条件路由及 Python 数值/单位比较；父子汇总；MOCK 证据、配置条件、冲突和故障区分。未知不判 NC，故障单独 ERROR。没有 LLM、RAG、checkpoint 或人工审批实现。
- 验证命令：`.venv\Scripts\python.exe -m pip --disable-pip-version-check install --no-index --no-build-isolation --no-deps -e .`；`-m pytest`；`-m ruff check .`；`-m ruff format --check .`；`-m pip check`；Phase 4 Demo；Phase 0 示例、Phase 1 `--mock`、Phase 2 `--mock`。技术说明保存具体命令与结果。
- 结果：Windows 10 x64 / Python 3.11.0；langgraph 1.2.14、pydantic 2.14.0；98 passed / 0 failed，Ruff/check/format、依赖检查和示例通过。五类结果 FC、NC、PENDING、PENDING、PENDING；额外覆盖 PC、单位、错误型号、全部运算符、层级/输入错误、工具异常、每条条件分支、State 不原地修改及重复运行无污染。
- 失败修复：初次 91 passed / 1 failed，顶层 PC 汇总错误变 NC，修复并保留回归；一处 Ruff 超长行修复。初始 pip 命令长时间未返回，不记录成功；改用 no-index、禁用版本检查的离线安装成功。Windows CIM 进程诊断被拒绝，未终止不明进程。
- 先前记录纠正：本地历史证明 Phase 2/3 已提交合并，旧“待提交”不再适用。Phase 3 只有三项离线测试；timeout 参数未实际执行，recursion_limit 未实现独立工具次数/预算限制，完整原生对比覆盖不足。因此撤回对应两项复选框并保留历史日志，不继续声称全量验收通过。此缺口不阻塞完全确定性的 Phase 4，本次不无关重构。
- Git：`phase-4` / `757f3f3`；昨天开始时干净，今天继续时代码已暂存，保留用户暂存范围；本次未 add/commit/push。新文档及后续修复需在授权后统一核查提交。敏感目录保持忽略。
- 限制：全部资料为 MOCK；手工拆分；原工具没有介质或资料版本；CI 仅修复依赖安装，未运行 GitHub runner；没有真实资料、自动自然语言解析、持久化或 HITL。
- 建议 commit：`feat: add explicit LangGraph MOCK compliance workflow`。
- 收尾补充：WorkflowResult 返回要求、证据及校验记录，引用 ID 可回查。加入中文条款后曾暴露 Windows cp1252 输出异常，改用 JSON Unicode 转义，并新增无密钥/ASCII 控制台回归，最终完整测试 98 passed。
- 下一任务：授权保存 Phase 4 可追踪版本；Phase 5 先区分消息上下文、checkpoint、跨 thread store 和业务数据库，再演示内存 checkpoint。前阶段验收缺口另行保留，不将其掩盖。

### 2026-10-13 — Phase 5 / Checkpoint、持久化恢复和人工审核

- 状态：DOING，所有本阶段技术验收通过；等待授权版本提交，无 push。Phase 4 发现已有 `9e4a8f3`，复核后标记 DONE；Phase 2/3 覆盖缺口保留，不无关重构。
- 核心理解：Checkpoint 保存执行位置，操作账本保存副作用意图和完成状态；审核快照必须与待执行对象绑定。interrupt 节点会重跑，因此受保护写入在独立执行节点中；版本修改后重新校验并再次中断。
- 修改文件：新增 `src/agent_demo/domain/reviews.py`、`src/agent_demo/graphs/review_graph.py`、`src/agent_demo/graphs/store_demo.py`、`src/agent_demo/persistence/operations.py`、`examples/phase05_checkpoint_hitl.py`、`tests/test_phase05_checkpoint_hitl.py`、`tests/test_phase05_operations.py`、`docs/phase05_checkpoint_hitl.md`、`docs/phase05_summary.md`；修改 pyproject.toml、requirements-lock.txt、README、本路线图。原 Phase 0–4 代码和入口保持可用。
- 依赖实际安装：`pip --isolated --disable-pip-version-check install --index-url https://pypi.org/simple --timeout 15 --retries 1 --no-cache-dir langgraph-checkpoint-sqlite` 成功；SQLite Saver 3.1.2 解析到 checkpoint 4.3.0、aiosqlite 0.22.1、sqlite-vec 0.1.9；LangGraph 1.2.14/Pydantic 2.14.0 保持。经 editable 安装、pip check、pip list 核验并更新 Windows 锁定文件。
- 验证命令：虚拟环境 `-m pytest`、`-m ruff check .`、`-m ruff format --check .`、`-m pip check`；Phase 4 五场景 Demo；Phase 5 CLI `start/status/resume --action modify/approve/reject`、重复批准及 `store-demo`；测试真实 SQLite、不同 Python PID、os._exit() 及文件内容/mtime。详细命令见技术文档。
- 结果：164 passed / 0 failed / 0 skipped（原 98 + 新增 66）；业务数据均 MOCK；内存状态不跨进程保存、SQLite 状态跨进程恢复、Thread 隔离、Namespace 授权、批准/拒绝/修改、新版本审核、重复执行、操作绑定、路径越界、未知文件保护与真实崩溃恢复通过。Ruff/format/pip check 通过；Phase 4 五类业务场景保持原结果。
- CLI 实际轨迹：`phase05-validation-20261013-d63b2cb0`，未确认模块 PENDING/awaiting_review → 新进程 status 恢复 → modify 配置 → review_version=2、FC/awaiting_review → approve completed → repeat completed；独立拒绝任务 rejected，无受保护文件。运行证据 `runtime/phase05/validation-20261013-d63b2cb0.json`；唯一批准产物 `outputs/phase05/ecd711964a642dc9106836df8f967785af81c0a2caa9c899d6e6c1464be38062.json`，仍为 DRAFT。
- 失败及修复：最初 Modify 序列化把未修改字段变成显式 null，导致三项测试失败；统一省略 null 后重新校验正常。Ledger 允许 SQLite 工作线程访问并用 RLock/事务保护同连接；重复批准终态原本只信任 Checkpoint，补充产物完整性核查，文件被删改时拒绝重建。Windows 符号链接创建权限不足时用实际 NTFS junction 检测路径保护，最终无跳过；CLI 修改 JSON 支持 UTF-8 BOM；Ruff 长行/代码块格式修复。
- Git：当前 `phase-4` / `9e4a8f3`；本次代码和文档未 add/commit/push。runtime、outputs、数据库、凭据和虚拟环境保持忽略；没有访问或修改 RAG-DEMO。
- 收尾核查：60 个锁定依赖与实际安装版本全部一致；32 个 README/Phase 5 文档本地链接有效；Git diff/check 与敏感跟踪检查通过。额外 UTF-8 BOM CLI 修改进入审核第 2 版后拒绝，无产物。
- 限制：可信本地 CLI，不是身份认证服务；状态/快照数据库必须由可信操作者保护。幂等保证仅限受控本地目录、支持原子硬链接的文件系统和进程异常恢复；不承诺断电或任意外部 API Exactly-once。Checkpoint 在 Phase 4 完整判断节点边界保存，内部只读计算可重跑；不实现生产并发审核调度。Store 仅内存实验，未构建长期用户记忆。真实 LLM/RAG/部署不适用，CI 远端未运行。
- 建议 commit：`feat(agent): add persistent checkpoints and human review workflow`。
- 下一任务：授权保存 Phase 5；Phase 6 先核实实际服务地址/权限、已发布设备资料、真实检索原文/页码/版本响应及调用副作用，当前进入真实集成的条件尚未满足。

### 2026-10-14 — Phase 6 / HTTP Agentic RAG 开发与真实验收阻碍

- 状态：BLOCKED，安全服务、模型凭据与授权设备 PDF/固定版本缺失；代码和离线验收已完成，不将 Mock 或 TEST PDF 当作真实 RAG 验收。Phase 5 实现提交 `9260a54` 已核实，收尾 DONE。
- 核心理解：Agent 只选择检索查询；HTTP 服务返回原文；PDF/来源核验和限定数值抽取产生结构化 Evidence；既有 LangGraph 判断及审核负责最终结论。LLM 候选解释和有效 citation ID 不能代替业务规则或事实适用性。
- 旧仓库调查：HEAD `d72c329`，只读 status 前后空；V3 Bearer `/retrieve` 返回原文、1-based 物理页、页内 chunk、document/version、独立评分和 metadata；没有 model 专用筛选或统一 score。源码确认启动会初始化 Catalog，检索/下载可写缓存、日志、WAL；未启动或调用。本机 8000/8011 未发现监听。已存在文档为员工/费用/安全/差旅资料，不能当设备 Datasheet。
- 新增文件：`integrations/rag_client.py`、`integrations/citation_verifier.py`、`integrations/rag_evidence.py`、`tools/rag_search.py`、`agents/agentic_rag.py`、`evaluation/rag_benchmark.py`、`examples/phase06_agentic_rag.py`；Phase 6 客户端/Agent/PDF/Evidence/benchmark/旧快照测试及 opt-in 集成测试；`eval/agent_test_cases.json`、`eval/reports/phase06_baseline.md`、两份 Phase 6 文档。
- 修改文件：Requirement/Evidence/WorkflowResult/Review 模型、compliance_graph/review_graph、pyproject/lock、README、.env.example、.gitignore（私有资料目录）及本路线图、rag_contract。所有既有功能保留，不复制旧检索引擎或创建新向量库。
- 验证命令：虚拟环境 `pip --isolated ... install pypdf`、`pip --disable-pip-version-check install --no-index --no-build-isolation --no-deps -e .`；`-m pip check`；`-m pytest`；`-m ruff check .` / `format --check .`；Phase 6 `--offline --scenario supplement`、`--scenario greeting --chat`、`--mode benchmark`；真实配置入口 `--mode retrieve` 返回 BLOCKED/exit1；原 Phase 5 status 核验及旧 SQLite 快照批准/修改/重启回归。实际 CLI 和命令见技术文档。
- 结果：完整 311 passed / 0 failed / 1 skipped（32.76s），跳过仅真实安全服务/PDF 验收；Ruff/format/pip check 通过；61 项锁定版本与实际安装一致。客户端58、Agent34、TEST PDF32、Evidence19、离线benchmark1、旧Checkpoint兼容2、真实关闭端口网络故障1均通过；既有164通过。LangChain1.4.4、LangGraph1.2.14、httpx0.28.1、pypdf6.20.1。模型使用和费用不可获得时明确标记 unavailable。
- 最终复核：完整 pytest 再次为 311 passed / 0 failed / 1 skipped（30.09s）；Ruff check、64 文件格式检查和 pip check 通过。36 个本地文档链接可解析，敏感文件未进入跟踪范围，工作区仅为本阶段待提交变更。
- 实际离线轨迹：supplement 为模型轮次3、工具检索2；greeting 检索0。六案例固定检索均1，Agent分别0/1/2/1/1/1，平均均1；离线 Agent 控制耗时均值15.67ms，不能推导真实性能优势。证据文件 `outputs/phase06/offline-benchmark-20261014-45261010.json` 保持忽略。冲突样例 completed 仅表示检索循环结束；真实业务缺绑定仍 PENDING，已验证两份不同 TEST PDF 来源冲突被规则识别。
- 失败/修复：初次 Ruff 长行修复；真实配置入口安全服务确认缺失返回明确原因，不发送 HTTP。新增 Evidence 可选字段曾造成旧快照严格字典比较风险，改为校验后填默认字段比较，保留原摘要/原文件/原 MOCK 数值理由，实际旧任务仍 completed。真实路径在节点内禁止回退 MOCK；原文核验摘要防意外改动；模型预算失败传入业务故障，不能伪装 FC。
- Git：`phase-4` / `9260a54`，本阶段未 add/commit/push；旧项目未修改；凭据、私有 PDF、outputs/runtime、运行库均忽略。
- 限制：实际 HTTP、真实设备文档页码回查、真实模型自主检索与真实评测未执行。数值提取仅支持明确规格行；人工 DocumentBinding 必须确认型号、版本、配置及授权，不能自证资料厂商真实性。超时停止等待不等于取消；token 事后预算不撤销已计费调用。历史 Phase 3 缺口继续保留。
- 建议 commit：`feat(agent): integrate bounded RAG retrieval with verified evidence workflows`。
- 下一任务：提供安全独立服务与凭据、已授权固定设备 PDF/绑定/标准答案，完成 opt-in HTTP/PDF 验收及真实对比；Phase 10A 尚不能进入，Phase 7 为独立可选学习实验，不是业务主链依赖。
- 用户后续确认：目前暂无独立 RAG 服务，先完成开发并保留真实验收 BLOCKED。开发与离线验证已完成；不启动或修改旧 RAG-DEMO，待服务准备后接续真实验收。

### 2026-10-17 — Phase 7 / 官方 MCP v2 stdio 独立实验

- 授权前实施状态：DOING，本地技术实施与专项验收通过，统一版本收尾待本阶段提交授权；不推送。Phase 6 真实验收状态不变。
- 核心理解：MCP 是工具发现/执行协议，Host 仍负责授权，SDK 不替代业务校验；模型循环由 LangChain 管理，Server 无需 LLM。
- 实现：官方 MCPServer / Client，本地 stdio 复用原 add/lookup_product_spec 和 Dispatcher；原 Schema、原业务逻辑、固定允许列表、严格输入和结果校验、独立连接/工具期限、错误分类、完整进程生命周期；薄 StructuredTool 适配和独立 create_agent 入口复用 AgentAnswer。
- 新增文件：`src/agent_demo/mcp/server.py`、`client.py`、`tool_adapter.py`；三个 Phase 7 examples；`tests/test_phase07_mcp.py`；`docs/phase07_mcp.md`、`docs/phase07_summary.md`。修改 pyproject、requirements-lock、README 及本路线图，合计13个文件。
- 版本：Python3.11.0/Windows x64、mcp2.3.0、mcp-types2.3.0、pydantic2.14.0、langchain1.4.4、langgraph1.2.14、anyio4.15.1、pywin32 312。PyPI元数据Python>=3.10与当前官方文档3.11+有差异；仅声明本机3.11实际兼容。原61项依赖版本全部保持，新增15项，76项清单适用于Windows，不宣称Linux锁文件。
- 实际命令：`.venv\Scripts\python.exe -m pip --isolated --disable-pip-version-check install --index-url https://pypi.org/simple --timeout 15 --retries 1 --no-cache-dir "mcp==2.3.0"`；`pip ... install --no-index --no-build-isolation --no-deps -e .`；Phase7 Client和Agent Demo；`-m pytest tests/test_phase07_mcp.py -q`；完整 `-m pytest -q --tb=short --junitxml outputs/phase07/pytest-20261017.xml`；Ruff check/format、pip check。
- 专项结果：50 passed / 0 failed / 0 skipped（30.68s）。SDK内存连接、原始SDK真实stdio非法调用、调用/启动超时、服务退出、错误回复、脚本模型MCP往返、调用ID、工具授权、stderr日志和进程returncode均验证。完整回归最终结果补记于本段后续核查。
- 最终完整回归：361 passed / 0 failed / 1 skipped（60.19s）；原311项全部通过，新增50项全部通过。唯一跳过保留Phase6真实RAG/PDF条件。Ruff check、74文件格式检查、pip check通过；34个README/本阶段文档本地链接有效；76项固定依赖一致，旧61项无版本变更；独立Server脚本入口也完成真实Client调用。XML：`outputs/phase07/pytest-20261017.xml`；Git diff/check、敏感跟踪及旧仓库只读状态检查通过。
- 实际轨迹：协议2026-07-28；Client发现add与lookup_product_spec，add(15,27)=42；Agent脚本phase07-1查MOCK-SW-48→phase07-2 add(48,4)=52→AgentAnswer。原Gemini/GOOGLE进程Key均未配置；没有真实LLM调用。Demo证据 `outputs/phase07/validation-20261017.json`，完整XML同目录，保持忽略。
- 失败与修复：测试进程观测函数名与v2实际接口不同，改读已安装源码；裸dict强制结构化输出被SDK拒绝，改为dict[str,Any]；SDK连接关闭码初被归为协议错误，增加独立分类；read timeout未约束整个auto探测，增加连接整体期限；随后短工具期限影响冷启动，拆分connect_timeout与timeout，定向与专项回归通过。旧失败不删除、不通过跳过测试掩盖。
- Git：`phase-4` / `378f948`，本阶段未add/commit/push。旧RAG只读Git前后干净，未启动/导入/调用旧项目。输出、运行库、凭据及虚拟环境未进入跟踪范围。
- 限制：无真实LLM验收；本地受信命令，不是身份认证/OS沙箱；无远程MCP/Streamable HTTP/OAuth/Inspector；递归限制不是精确工具次数，超时包含清理延迟且不证明远端未执行。Phase2/3及Phase6旧缺口保持。
- 建议commit：`feat(agent): implement MCP server client and tool integration`。
- 下一任务：授权本阶段本地版本及完成记录；后续Phase8汇总，同时按路线图补齐Phase2/3与Phase6真实条件。Phase10A进入条件仍未满足。

#### 2026-10-17 — Phase 7 授权本地提交与完成收尾

- 用户明确授权：“授权本地提交及完成记录，不推送”。复核分支与13个文件，暂存区原为空，无额外用户修改；仅提交既定交付范围。
- 实现提交：`2f6fd60` — `feat(agent): implement MCP server client and tool integration`。包含代码、50项测试、示例、依赖及技术文档；未提交凭据、虚拟环境、数据库或运行产物。
- 状态：DONE。更新顶部、总览、版本复选框与两份阶段文档，完成记录另作本地提交；保留此前DOING历史及所有实际验证结果。
- 验证沿用已完成的361 passed / 0 failed / 1 skipped、Ruff/format/pip check及真实stdio/清理证据。本次仅Git提交和文档状态变化，不声称重新运行完整测试。
- 下一任务：Phase8先汇总已有评测用例与离线/真实验证分类；Phase2/3缺口及Phase6真实验收继续单独跟踪。未推送，不扩大授权。

### 2026-10-17 — Phase 8 / Evaluation、Security与Observability

- 状态：DOING，本地技术验收通过，等待本阶段授权版本；真实LLM三次代表用例与真实RAG/PDF样例BLOCKED，原因是当前进程没有模型Key、安全服务与资料绑定。Phase6及旧控制缺口不变。
- 核心理解：任务Oracle优先用结构化结果、实际动作及副作用；拒绝攻击可算用例PASS，但不算工具执行成功。BLOCKED/SKIPPED不进入通过率分母，安全三项单独门控。
- 实现：Pydantic统一用例、Runner、Oracle/安全门槛、显式分母指标、非覆盖JSON/Markdown、真实用例条件检查与既有集成入口、本地JSONL/SDK Callback、三组脚本/协议Benchmark、失败回放及CI离线检查；未改稳定业务或重写Agent。
- 文件：新增evaluation/{models,fixtures,scenarios,live,runner,metrics,security,report,benchmarks}.py、observability.py、examples/phase08_evaluation.py、两份Phase8测试、技术文档及总结、eval/reports/phase08_{baseline.md,results.json}；修改统一数据集、CI、README和路线图。
- 用例：tool11（含3真实）、compliance11、review11、rag10（含1真实）、mcp5，共48；39 offline_mock、4真实stdio、1内存SDK通过，4真实条件阻碍。真实结果不假设、不进入离线通过数。
- 实际命令：`.venv\Scripts\python.exe examples/phase08_evaluation.py`、`--no-benchmarks`、`--include-live --save-baseline`；`-m pytest tests/test_phase08_evaluation.py tests/test_phase08_security.py -q`；完整`-m pytest -q --tb=short --junitxml outputs/phase08/pytest-20261017.xml`；Ruff check/format、pip check。未新增依赖，原76项清单保留。
- 结果：专项34 passed（21.70s）；完整395 passed / 0 failed / 1 skipped（78.25s），原361全部通过。唯一pytest跳过仍Phase6真实环境，不与Evaluation4个BLOCKED混算。Ruff/87文件格式/pip check通过。
- 正式基线：44/44符合预期；24工具请求、18实际执行、16成功/2预设失败、3未授权拒绝/2参数拒绝，另有预算拒绝；状态18/18、FC/NC错判0、复合错误0、冲突2/2。接受引用成员/来源6/6，候选TEST PDF1/2（负向错页被拒绝），真实PDF无样本；Token/费用unavailable。工具计数范围为Agent及MCP边界，业务图内部确定性辅助调用按Node观察，不算模型工具请求。
- 安全：在本用例集内，未授权写入、无足够关联证据FC、被接受伪造/来源不一致引用均0；反向测试证明即便结果贴PASS，任一关键违规仍使硬门槛失败。恶意文档不能执行额外工具、不能跳审核或制造FC；无真实LLM抗注入普遍保证。
- Benchmark：脚本计划查规格→加法52，原生/框架各3样本，均值约2.13/16.44ms；直接Tool/MCP warm各3，约0.65/3.21ms，启动1194.30ms另列；固定与Agentic检索复用六场景，平均次数均1。同机同时回归、负载非受控，均不能推断真实性能/模型优劣。
- 证据：[基线Markdown](eval/reports/phase08_baseline.md)、[JSON](eval/reports/phase08_results.json)；正式运行`outputs/phase08/20261017T093232Z-d137f986/`及完整pytest XML。元数据Git=e82f69a及dirty状态，数据集SHA256=76b832a1f5c0bcb28c435ef779b910f51a95b317eb0dbca856f40b6a8cf19dee，源码/Prompt Hash另存JSON。
- 失败历史：首次43/44，mcp-untrusted夹具无描述先触发invalid_discovery；补齐描述后进入原预期的invalid_response，没有降低门槛。初次运行`outputs/phase08/20261017T092126Z-3618d3be/`保留。用例动作预期补强后同步修正评测器负向测试夹具，重新完整回归通过；未覆盖历史失败报告。
- 可观测性：原生实时事件、实际SDK节点Callback、MCP调用及RAG既有事件导入；导入时间明确标记，不伪造发生时间。默认不存Prompt/参数/文档全文/认证头，ID稳定匿名化。评测独立临时目录及SQLite，不污染既有Checkpoint。
- CI：新增离线Evaluation、安全硬门槛与格式检查；Windows已运行相同核心命令，GitHub/Linux远端未执行。实际退出码负向测试证明错误预期返回1。
- 收尾回放：实际执行`examples/phase08_evaluation.py --case rag-forged --case mcp-untrusted --no-benchmarks`，2/2符合预期、退出0；证据`outputs/phase08/20261017T094030Z-a773d5ba/`。实际Trace CLI按run_id查询得到同一Run的10条事件、退出0；46个本地文档链接、76项锁定版本及基线Hash核查通过。曾因终端cp1252无法输出中文导致只读检查失败，改为Python `-X utf8`后成功，未影响文件内容或测试结果。
- Git：phase-4/e82f69a，本阶段未add/commit/push；旧RAG只读Git保持干净，未启动、修改或访问旧数据库。建议commit：`feat(agent): add evaluation security and observability framework`。
- 下一任务：授权本地版本；之后优先Phase2/3控制修复及真实服务/PDF条件，再执行真实质量重复基线。Phase9/10前提仍未满足。

#### 2026-10-17 — Phase 8 授权本地提交与完成收尾

- 用户明确授权：“授权 Phase 8 本地提交及完成记录，不推送”。复核当前phase-4、21个文件及原空暂存区，仅提交授权范围，没有额外用户修改。
- 实现提交：`0fb559e` — `feat(agent): add evaluation security and observability framework`，21个文件，6998行新增、23行删除。未包含凭据、数据库、运行日志、生成产物或虚拟环境。
- 状态：DONE（本地Evaluation、安全门槛与Observability范围，见ADR-035）；同步顶部、总览、版本复选框及两份阶段文档，完成记录另作本地提交。真实LLM/RAG的4条BLOCKED与未勾选真实测量项保持原状，未将真实质量标为通过。
- 验证沿用完整395 passed / 0 failed / 1 skipped、专项34 passed、44/44可执行评测、安全三项0以及Ruff/格式/pip check；本次仅Git与文档收尾，不声称重跑测试或真实请求。暂存差异检查通过，敏感跟踪检查为空，旧RAG只读Git状态干净。
- 基线保留执行时的e82f69a/dirty元数据与历史失败报告，不追改为提交后的Git状态。Windows换行转换提示不涉及业务内容或失败。
- 下一任务：修复Phase2/3已有控制缺口，并准备安全RAG服务、授权固定PDF及真实模型重复基线；不扩大到Phase9/10，不推送。

### 2026-10-17 — 全阶段审计、控制补齐与SOC/API/PDF整合

- 状态：DOING；Phase2/3控制软件已补齐待本次版本，Phase9/10本地软件通过但真实/部署验收BLOCKED。用户明确回复“尚未具备，先完成软件和隔离测试，真实验收保留BLOCKED”。不撤销Phase6真实前提，不虚构毕业完成。
- 核心理解：线程超时停止等待不等于取消；审核版本还必须绑定导出格式和目录；任务owner、Graph状态、Checkpoint、业务审计与副作用账本各有职责。PDF原文定位不等于理解任意自然语言条款，人工映射需要核查遗漏、单位与来源。
- 审计：`docs/project_completion_audit.md`，以9cea417/phase-4干净工作区为起点。初始pytest394 passed / 1 failed / 1 skipped（137.41s）；Windows monotonic小期限失败保留XML，改perf_counter后原测试通过。Ruff初始通过。
- 控制修复：原生实际等待、严格计数/累计token、重试计入轮数、Gemini输出/期限配置和历史结果去重；LangChain独立ExecutionGuard、严格Schema、允许列表、错误回传、同题对照；Phase3新增显式离线Demo，原运行入口保留。
- 应用：SOCInput复用既有Requirement/Evidence/Decision；单型号、最多20原子要求；可信HTTP/文档绑定路径、原Graph/审核、实际SQLite任务归属、拒绝/修改/重复审核和恢复。export_policy把Excel草稿类型、目录及soc-v2模板绑定入审核摘要。二进制发布复用原账本，不覆盖，字节确定且可崩溃恢复；JSON旧入口不变。
- PDF与API：保留全文、物理页、行号、编号候选、Hash与未分配文本，人工确认字段/拆分/排除；扫描/复杂布局有限制。FastAPI认证/归属、有界队列、限流、状态、审核、取消、下载、PDF确认；单进程原型，不宣称分布式或公网生产系统。
- 修改文件：agents/{execution,agent_loop,langchain_agent}.py、Gemini/RAGClient、review_graph/reviews/operations；新增soc/{models,service,rfp,excel}.py、api/app.py、SOC CLI及HTTP验收脚本、MOCK输入与预期、两份补齐测试；依赖/CI/Docker/Compose、README/.env.example、审计/Phase9/10技术文档及阶段总结、本路线图与新整合基线。原业务比较规则、历史报告及旧RAG未改。
- 安装：实际FastAPI0.143.3、openpyxl3.1.5、annotated-doc0.0.5、et-xmlfile2.0.0，原76项保持，总80项Windows版本已核对；editable离线安装/pip check通过。Linux候选移除pywin32，但未实际验证，不声明跨平台锁定通过。
- 实际命令：初始/最终`-m pytest -q --tb=short --junitxml outputs/completion-audit/...xml`；`-m ruff check .`、`-m ruff format --check .`、`-m pip check`；`examples/project_acceptance.py`、`--docker-image agent-demo:local`；`examples/phase08_evaluation.py --include-live`；Phase0 hello、Phase1/2/3离线Demo。Excel额外回读及Artifact Tool只读渲染三张表，不改产物。
- 最终结果：**439 passed / 0 failed / 1 skipped（104.73s）**，原395与新增44项通过；唯一跳过Phase6真实服务/PDF。Ruff/105文件格式/依赖通过。真实本机HTTP18/18通过，含两次停进程重启；16行XLSX、10个内部引用、中文、审核版本及修改目标96回读正确，三张表可读且无公式错误。
- 评测：原48统一用例44PASS/4BLOCKED；工具16/18，状态18/18，接受引用成员/来源6/6；候选TEST PDF1/2负向正确拒绝，真实PDF无样本；安全三项0。未使用真实模型/付费服务，usage/费用不可用；原生/框架/MCP对照只代表脚本和协议成本。
- 证据：`outputs/completion-audit/{baseline,final-regression}.xml`；最终HTTP/Excel目录`outputs/completion-acceptance/430c3358a0ee4facb033b9267f6fad64/`；评测目录`outputs/phase08/20261017T104232Z-b2125c92/`；脱敏整合基线`eval/reports/project_completion_baseline.{md,json}`。旧Phase6/8基线、初始失败和中间报告均保留。
- 阻碍：Docker命令不存在，实际尝试返回BLOCKED，未构建镜像/运行容器/远端CI。真实型号、固定版本PDF、人工10–20条答案、RFP标注及安全RAG均缺失。无限定语义抽取、OCR、跨型号选型及正式发布不在已验证能力内。
- Git：phase-4/9cea417，本次尚未add/commit/push，先前Phase8授权不覆盖整合。旧RAG只读HEAD d72c329、工作区干净；没有启动/导入/修改旧代码、索引或数据。全部产物/runtime/凭据保持忽略。
- 收尾补充：SOC CLI真实执行submit/run/status/review/export/重复export共6命令成功，证据`outputs/completion-cli/f54ef099227f4e61b25f4d6adb997e4d/cli-validation.json`；最终Ruff格式106文件通过、72个本地链接有效、80项固定版本及基线源码Hash匹配。41个交付文件未暂存，无敏感跟踪；本次只读复核旧RAG仍干净。
- 下一任务：核查本次整合版本，准备真实条件和Docker环境，执行Phase6、10A/10B真实逐条核验及9B容器恢复，再进行10C毕业验收；不将软件/MOCK通过写成全部DONE。

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

Phase 4 新增决策（2026-10-11）：

- ADR-015：使用完全确定性的顺序 StateGraph，状态字段默认替换，以稳定 ID 字典保存结果；当前无并发聚合需求，不使用追加 reducer，不提前实现 checkpoint。
- ADR-016：复合条款按 ERROR → PENDING → 必要项 NC → 已证实部分满足 PC → 全部 FC 汇总；只有可选项失败且无已知满足时保守 PENDING。政策仅适用 MOCK 教学，正式 RFP 前确认必要性和业务口径。
- ADR-017：复用原 MOCK 工具的真实字段；电口介质由独立人工 MOCK 证据补充，来源版本未知保留 null。原工具没有返回的字段不由适配器补造。

复审点：Phase 5 状态持久化与恢复、Phase 6 真实证据、毕业项目的正式业务规则。

Phase 5 新增决策（2026-10-13）：

- ADR-018：审核图调用原 Phase 4 完整确定性图，外层持久化保存 JSON 状态，避免复制业务规则及自定义模型反序列化；内层只读计算重跑安全，细粒度中间 Checkpoint 延期。
- ADR-019：审核快照绑定 run/thread/version/内容摘要及拟执行路径；审核与执行拆分，Modify 必须重算并进入新版本，业务结论和人工审核结果分开记录。
- ADR-020：SQLite 操作账本以 operation_id 和目标路径唯一约束绑定 SHA-256，prepared 先持久化、临时文件 fsync 后非覆盖原子硬链接发布、完成记录随后提交。重试核验产物与账本，不盲目重建或覆盖；不扩展为分布式 Exactly-once。
- ADR-021：Thread 仅执行上下文，跨 Thread Store 用显式 namespace 和可信调用方授权；本阶段 CLI 不提供身份认证，后续服务必须验证任务归属并保护持久化数据。

复审点：Phase 6 真实服务调用副作用与证据来源、Phase 9 身份权限和部署文件系统、毕业项目的正式 SOC 审核。

Phase 6 新增决策（2026-10-14）：

- ADR-022：仅使用现有 V3 HTTP `/retrieve`，配置固定 origin、Bearer、KB 和 caller 文档范围；不登录、不启动旧工程、不复建检索引擎。真实副作用安全条件不满足时保持 BLOCKED。
- ADR-023：复用原业务模型和图，real_rag 模式禁止 MOCK 混入或回退。人工型号/文档/版本/哈希/条件绑定 + 实际 PDF 引用核验 + 限定字面规格抽取，缺失或不支持格式保持 PENDING，不把 LLM 摘要作为数值证明。
- ADR-024：create_agent 加应用 Middleware，分别限制模型调用、搜索工具尝试、HTTP 重试、token 和期限；事件不记录凭据/全文，超时不宣称取消或成本撤销。工具白名单只有 search，结构化输出通道不增加业务执行权限。
- ADR-025：新 Evidence 默认字段向后兼容；旧 Checkpoint 比较时规范化可选默认值，原快照摘要与既有产物保持不变。真实证据审核沿用独立版本和操作账本，仍输出 DRAFT。
- ADR-026：offline_mock/TEST PDF、实际网络故障、真实 HTTP、真实 PDF、真实效果评测分别记录；缺真实条件不填充成功率或声称 Agent 优于固定流程。

复审点：解除 Phase 6 真实验收阻碍、Phase 10A 正式业务口径、Phase 9 服务身份授权与部署。

Phase 7 新增决策（2026-10-17）：

- ADR-027：选择经安装验证的官方稳定mcp2.3.0（v2），使用MCPServer/Client，不混用v1示例；记录实际现代协议server/discover和2026-07-28，而不伪造initialize握手。
- ADR-028：仅开放原add和MOCK规格工具，复用Schema/校验/Dispatcher；原始参数在SDK转换前验证，Host授权列表独立于发现结果。Tool annotations仅是提示。
- ADR-029：固定当前sys.executable启动stdio，单个异步连接贯穿Agent运行；SDK管理子进程，连接与工具期限独立，错误后不盲目重试；测试观察真实进程句柄验证清理。
- ADR-030：MCP作为独立学习路径，保留Phase3直接调用与Phase6 HTTP；真实通信和脚本模型/真实LLM分开报告；远程认证扩展不阻塞本地实验，Git版本收尾仍按授权执行。

复审点：本地授权版本收尾、Phase8安全/错误汇总、需要跨机器工具时的Streamable HTTP与认证。

Phase 8 新增决策（2026-10-17）：

- ADR-031：保留Phase6旧数据结构，新增严格evaluation_cases；通过既有入口执行，Oracle使用结构化结果/实际动作/文件副作用，不比较自然语言关键词。
- ADR-032：报告执行模式与显式分母，区分请求/实际执行/业务结果；三项安全违规独立门控。真实质量阈值先留空，缺真实前提不计PASS，有限样本不推广绝对保证。
- ADR-033：统一payload-free JSONL，通过既有事件与SDK Callback观察；调用ID匿名化、导入事件标记时间依据、未知值为null。局部评测SQLite只允许明确业务类反序列化，不放开pickle或改旧库。
- ADR-034：每次运行唯一目录，固定基线仅首次创建；首次失败保留。Benchmark仅本机脚本/协议成本观测，记录样本量和负载限制，不强制外部平台。
- ADR-035：本阶段按用户“真实条件可用时执行”的边界交付本地评测与门槛；三次真实模型及真实RAG质量测量因无Key/安全服务/PDF延期为BLOCKED，不冒充完成。影响：无法给出真实SOC/引用/抗注入质量结论，Phase6阻碍和真实业务进入条件继续保留。

复审点：Phase2/3修复后的同题回归、真实模型/RAG样本与安全质量阈值、未来部署监控。

全阶段整合新增决策（2026-10-17）：

- ADR-036：用户明确授权在真实资料暂缺时先完成软件和隔离测试。因此按10A软件→9A→10B软件→系统评测→9B材料推进，Phase6及真实毕业前提不撤销，真实验收保持BLOCKED，不降低标准。
- ADR-037：抽取共用有界等待，原生/框架独立计算实际调用预算，使用高分辨率计时修复Windows小期限；不宣称线程、远程请求或已产生费用已取消。
- ADR-038：SOC应用包装原业务/审核图，以SQLite owner管理任务；审核前持久化身份/时间，快照绑定Excel类型、目录、模板，Binary账本复用原非覆盖原子发布。旧Phase5默认没有Excel策略，保持原JSON契约和旧摘要。
- ADR-039：PDF先保留完整页面及定位候选，人工显式映射Schema与父子要求；未覆盖候选需说明排除，未知布局/单位/真实规格不由LLM或关键词补造。通用语义抽取与OCR不冒充已实现。
- ADR-040：FastAPI采用本地单服务进程、单任务工作线程与有界队列；支持身份归属、取消语义和恢复，不提前构建分布式平台。Docker/Linux/远端CI只有材料和可运行检查脚本，缺环境不标通过；Windows80项与Linux候选分别说明。

复审点：本次授权版本、真实产品资料及RFP覆盖率、容器实际恢复、后续生产身份/调度边界。

## 18. 官方资料与版本核实

- LangChain Agent：https://docs.langchain.com/oss/python/langchain/agents
- LangGraph：https://docs.langchain.com/oss/python/langgraph/overview
- LangGraph 持久化：https://docs.langchain.com/oss/python/langgraph/persistence
- LangGraph 中断与恢复：https://docs.langchain.com/oss/python/langgraph/interrupts
- MCP：https://modelcontextprotocol.io/docs/getting-started/intro
- FastAPI：https://fastapi.tiangolo.com/
- pytest：https://docs.pytest.org/

本路线制定时核对了 LangChain Agent、LangGraph 持久化与中断文档。其他库在引入阶段再核实官方文档和兼容版本；链接内容更新不代表本地依赖自动升级。

**本次全阶段整合：Phase2/3控制已补齐待版本；Phase9/10本地软件与MOCK验收通过，真实RAG/产品资料/RFP及Docker/Linux验收仍BLOCKED。Phase8本地DONE历史保留；不宣称毕业通过，不发布客户文件，不推送。**
