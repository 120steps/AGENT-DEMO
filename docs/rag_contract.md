# RAG-DEMO 接口契约调查（Phase 0）

调查日期：2026-10-10。旧工程位置：`D:\workspace\AI\rag-demo`。

**调查方式：仅静态阅读源码、README 和测试，不导入模块、不启动 API、不运行旧工程测试/CLI、不访问其数据库或索引、不安装依赖、不修改 Git 配置。** 下文“已核实”表示源码实现已核实，不代表真实服务请求已验证。

## 1. 工程与 API 版本

| 入口 | 已核实的能力 | 运行说明 |
|---|---|---|
| 根目录 `app.py`（V1） | 健康检查、问答、上传/列表/删除文档；未定义独立检索 HTTP 路由 | 根 README 使用 `uvicorn app:app --reload`，未明确固定端口；没有运行该命令 |
| `rag_langchain_native/api.py`（V3） | 独立检索、问答、认证、会话、文档与版本管理、下载、可观测接口 | V3 README 给出 `python -m uvicorn rag_langchain_native.api:app --host 127.0.0.1 --port 8011`；没有运行 |
| `langchain_rag/`（V2） | 根 README 描述 Python 函数入口 | 根 `/chat` 尚未切换到 V2，不把函数当成 HTTP API |

未来 Phase 6 优先调查 V3 `/retrieve` 的真实可用性，不使用 V1 `/chat` 作为默认检索工具。V3 的企业 collection 与早期 collection 分离；旧知识库有数据，不代表企业接口已拥有发布且可见的资料。

## 2. V3 请求、认证与路由

来源：`rag_langchain_native/api.py` 的 `LoginRequest`、`QueryRequest`、`current_principal` 及各路由。

- `POST /auth/login`：`tenant_id`、`username`、`password`（至少 8 字符）。返回 `access_token`、`token_type: bearer`。
- `POST /retrieve`、`POST /chat`：要求 `Authorization: Bearer <token>`。租户、角色和组从服务端加载；不能由请求体选择身份。
- 当前没有读取 `.env`、口令或 Token；真实地址、可用凭据和授权知识库未知。

| QueryRequest 字段 | 类型、默认值与限制 |
|---|---|
| question | 字符串，1～4000 字符，还受配置的字符上限限制 |
| knowledge_base_id | 非空字符串，默认 `default` |
| conversation_id | 可空字符串 |
| document_id | 可空字符串；限制逻辑文档 |
| version_id | 可空字符串；受到服务端授权/版本范围限制，不保证任意历史版本可检索 |
| classification | 可空字符串 |
| top_k | 整数，默认 10，范围 1～50 |

**路由差异：** `/retrieve` 把 `top_k` 传入检索服务；`/chat` 虽复用同一个请求模型，但路由没有把请求的 `top_k` 传入 `enterprise().chat()`，不能承诺这个参数控制问答返回条数。

`/retrieve` 执行授权检索及重排，不生成最终答案。但带会话 ID 时可能做上下文改写，开启 query rewrite/expansion 时也可能调用模型；“不生成答案”不等于“完全无模型成本”。

`/chat` 包括路由、检索、答案和拒答；带会话 ID 时在服务端添加 user/assistant 消息，有持久化写入。问候还可能走 normal_chat，不返回证据。

## 3. V3 响应结构

V3 路由使用 `-> dict`，没有独立 `response_model` 固定返回 schema。契约来自实际返回构造路径，可能随状态变化。

### 正常 `/retrieve` 路径

`chain.py:NativeRAGService.retrieve_only` 返回查询处理字段、`documents`、`latency_ms`。`enterprise.py:retrieve_only` 追加 `contextual_query`、`contextual_rewrite_failed`、`tenant_id`、`knowledge_base_id`、`authorization_epoch`。

`documents[]` 的序列化来源：`retrieval.py:serialize_document`。

| 字段 | 已核实的来源与语义 |
|---|---|
| document | `Document.page_content`，检索 chunk 原文；不是整份 PDF |
| source | metadata 中的文档来源，企业索引时来自文档注册记录 |
| page | PDF 物理页序号，从 1 开始；不是印刷页码 |
| chunk_id | 页内切分序号，从 0 开始；单独使用不全局唯一 |
| document_id | 企业索引中是逻辑文档 ID；早期非企业 ingestion 曾用它代表 chunk 稳定 ID，不能混用 |
| version_id | 企业索引时加入的版本 ID；字段可因资料 metadata 不完整而为空 |
| chunk_uid | 企业索引的 chunk 唯一标识，包含租户、知识库、文档、版本、页和 chunk 信息的 SHA-256 |
| tenant_id / knowledge_base_id / classification | 企业索引 metadata，服务端授权范围相关 |
| rank | 最终结果顺序 |
| vector_distance | 向量 cosine distance（若向量路线提供）；不能当作统一概率 |
| fusion_score | 融合分数（若相关路线产生） |
| rerank_score | 重排分数（若启用/返回） |
| matched_retrievers / matched_queries | 命中的检索路线和查询，缺失时为空列表 |
| metadata | 保留完整的 metadata 字典；部分字段取决于实际索引内容 |

源码中没有统一的顶层 `score`；客户端不能将多个量纲不同的分数直接混为一个置信度。

### 空授权范围路径

`enterprise.py:_empty_authorized_result` 返回空 `documents`、空 `sources`、空 context、`refused: true`、`refusal_reason: no_authorized_documents`；`retrieve_only` 删除 `answer` 字段。这条路径用的是 `retrieval_latency_ms`，正常检索路径为 `latency_ms`。

客户端需要适配这些分支，不能假定每次都有完全相同的字段。空授权结果也不代表设备不满足技术要求。

### `/chat` 路径

正常知识问答包含 `answer`、`refused`、`refusal_reason`、`sources`、`documents`、`retrieved_context` 及查询/延迟字段。`sources[]` 由 metadata 构造，包含 source、page、chunk_id、document_id、version_id、tenant_id 和 knowledge_base_id；原文在 `documents[]`。

问答路由还追加 route、contextual_query、contextual_rewrite_failed、tenant_id、knowledge_base_id、authorization_epoch、total_latency_ms。normal_chat 与拒答路径可能没有证据。

## 4. 证据字段核查与缺口

| 目标信息 | V1 `/chat` | V3 `/retrieve` | 后续注意事项 |
|---|---|---|---|
| 原文片段 | `source[].document`，非拒答时构造 | `documents[].document` | 真实内容与来源仍待请求验证 |
| source/page/chunk_id | schema 有；缺失 page 代码填 `N/A` | 序列化有，可空 | V1 的 `page: int | None` 与 `N/A` 不一致，可能导致响应校验失败 |
| document_id | 未提供 | 提供 | 区分逻辑文档 ID 与早期 chunk ID |
| metadata | 未完整提供 | 提供完整字典 | 字典可扩展不等于特定业务字段已存在 |
| 设备型号 | 未提供专用字段 | 未提供专用字段 | 需在新工程维护型号与允许文档/版本映射；不能从文件名擅自确定型号 |
| 文档版本 | 未提供 | `version_id` | 不是 Datasheet 的业务修订版本号 |
| 文档内容哈希 | 未提供 | 检索序列化未专门提供 | Catalog 版本有 `content_hash`；可进一步调查版本列表 API |
| 数值评分 | `distance` | 分开的 distance/fusion/rerank 字段 | 可缺失，且量纲不同 |
| 按型号筛选 | 未提供 | 未提供专用参数 | 可用 document_id/version_id 作为映射后的筛选条件，仍受权限控制 |

哈希来源已静态核实：`lifecycle.py:upload_version` 用上传字节计算 SHA-256；`catalog.py` 的 `document_versions` 表保存 `content_hash` 和 `version_number`；`GET /documents/{document_id}/versions` 返回生命周期版本列表。尚未读取数据库或真实列表响应，因此不能声称当前资料已经有可用哈希。

页码来源：V3 `ingestion.py:load_pdf_pages` 将 loader 的 0-based page 加 1；V1 `document_loader.py:load_pdf` 使用 `page_index + 1`。都指 PDF 物理页，印刷页码映射未提供。

## 5. 错误与副作用

V3 API 源码显式处理：401（缺失/无效认证）、403（无权限）、404（记录/文件/trace 不存在）、409（Catalog 冲突）、413（请求/上传过大）、429（限流，带 Retry-After）、503（ready 失败）；Pydantic/FastAPI 请求验证错误为 422。没有统一自定义的所有服务异常响应，未处理异常仍可能为 500；真实错误体与代理行为未验证。

以下内容不能为了“只读调查”而执行：

- 根 `app.py` 导入时调用 `os.makedirs`；其依赖还可能初始化其他对象。
- V3 `api.py` 模块底部 `app = create_app()`；create_app 会构造 DocumentCatalog，其构造会建目录、初始化 SQLite schema，并使用 WAL。
- `/ready` 会 mkdir runtime；`/retrieve` 可能加载模型、创建缓存或写观测日志；不能视为无文件副作用。
- `/chat` 带会话 ID 会写历史；登录/读取路由也可能触发观测日志。
- 文档上传、索引、发布、回滚、删除、恢复、创建用户和 ingest 都是写入任务。

本阶段没有执行这些操作。

## 6. 已获得的样例证据与未知项

已静态阅读 `tests/test_enterprise_conversation_api.py`：测试使用注入的假模型和临时数据，包含未认证检索返回 401、跨租户下载拒绝、normal_chat 写会话等断言。**本次没有运行这些测试；已有测试源码不能冒充本次真实响应。** 未获取实际部署服务的响应样本。

Phase 6 前仍需确认：

- 实际服务地址、运行状态、凭据及可访问知识库。
- 目标设备 Datasheet 是否已进入 V3 企业库并发布、授权；不能假定目前的公司制度样本适合设备 SOC。
- 真实 documents metadata 的完整性、版本列表和哈希返回、页码与 PDF 回查。
- 请求超时、默认 rewrite/expansion、缓存与模型费用的实际配置。
- 正常/空结果/无权限/错误响应的实际样本与兼容性。
- 运行真实集成所需的旧工程写入授权或独立隔离服务方案。

## 7. 调查结论

**Phase 0 静态契约摸底已完成。** V3 的 `/retrieve` 在源码层面提供原文、来源、物理页、chunk 和文档/版本标识，具备作为后续检索工具的基础；当前不需要为 Phase 0 改造旧仓库。

**Phase 6 真实集成尚未验证。** 型号映射、业务资料版本、数据是否已经就绪，以及启动/调用副作用仍是进入真实集成前必须处理的事项。

旧仓库 Git 只读状态检查使用 `--no-optional-locks` 和命令级 `-c safe.directory=D:/workspace/AI/rag-demo`，未修改全局配置或旧仓库引用。调查前输出为空；交付前再次核对并在新工程的 Phase 0 验证记录中记录结果。

## 8. Phase 6 重新核实（2026-10-14）

本节补充当前事实，保留前面的 Phase 0 调查历史。旧仓库仍是 `D:\workspace\AI\rag-demo`，本次仅读取源码、README、文件名和 Git 状态；没有导入旧项目、读取 `.env`/凭据、启动服务、访问数据库、运行旧测试或发送 HTTP 请求。

### 8.1 当前服务状态与实际检查

执行的只读检查：

```powershell
git --no-optional-locks -c safe.directory=D:/workspace/AI/rag-demo -C D:/workspace/AI/rag-demo status --short
git --no-optional-locks -c safe.directory=D:/workspace/AI/rag-demo -C D:/workspace/AI/rag-demo log -1 --format='%h %s'
netstat -ano -p TCP
```

- Git 工作区状态输出为空；当前提交为 `d72c329 update readme.md`。
- `netstat` 未发现本机 `8000` 或 `8011` 的 `LISTENING` 记录；`Get-NetTCPConnection` 查询也未返回这两个端口的监听项。
- 使用新工程 `.venv\Scripts\python.exe` 和标准库 socket，对 `127.0.0.1:8011`、`127.0.0.1:8000` 分别执行 TCP-only 检查（0.5 秒超时），`connect_ex` 均返回 `10035`，在检查期限内未建立连接。该值不是 HTTP 状态码，也不能作为真实服务响应或鉴权失败证据。
- V3 README 第 39 行仍给出 `127.0.0.1:8011`；`docker-compose.yml` 第 7 行仅绑定本机 `8011`。没有发现当前可请求的部署实例；其他机器、容器网络或未公开端口的状态未知。

这次没有真实 `/retrieve` 响应、真实 source/page 回查或登录成功证据。**真实旧 RAG 集成验收仍为 BLOCKED，离线契约测试不能替代这项验收。**

### 8.2 当前 V3 契约与源码定位

以下行号均相对于旧仓库 `rag_langchain_native/`，对应本次读取的 `d72c329`。

| 契约 | 已核实源码 | 客户端边界 |
|---|---|---|
| `POST /auth/login` | `api.py:54`、`api.py:307`、`security.py:176` | tenant_id/username/password，返回 access_token/token_type；未读取或取得当前可用凭据 |
| `POST /retrieve` | `api.py:60`、`api.py:341` | Bearer 认证；question、knowledge_base_id、top_k，以及可选 document_id/version_id/classification/conversation_id；没有按设备型号查询的专用参数 |
| 正常检索响应 | `chain.py:629`、`enterprise.py:161` | documents 原文片段和查询处理字段；正常延迟为 latency_ms，另追加 tenant_id/knowledge_base_id/authorization_epoch/contextual_query |
| 空授权结果 | `enterprise.py:108`、`enterprise.py:188` | documents=[]、refused=true、refusal_reason=no_authorized_documents；删除 answer，延迟字段为 retrieval_latency_ms；不能解释为设备 NC |
| 文档片段 | `retrieval.py:537` | document/source/page/chunk_id/document_id/version_id/chunk_uid/metadata；字段存在于序列化代码不代表实际索引中值必定非空 |
| 分数字段 | `retrieval.py:564` | vector_distance/fusion_score/rerank_score 独立保留；没有统一 score，不把 distance 当概率 |
| PDF 页码 | `ingestion.py:72` | loader 的 0-based page 加一，代表 PDF 物理页；印刷页码映射未提供 |
| 文档版本列表 | `api.py:472`、`lifecycle.py:330`、`catalog.py:142` | 可返回版本记录中的 content_hash/version_number；当前未请求真实列表；version_id 不等于产品手册修订号 |
| 内容哈希 | `lifecycle.py:181`、`lifecycle.py:255` | 上传 bytes 的 SHA-256 存入 Catalog；企业 chunk metadata 构造没有加入 content_hash，检索序列化没有专门返回文档哈希 |
| 下载 | `api.py:529`、`lifecycle.py:333` | 按 document_id 和可选 version_id 返回 PDF；下载路径在服务端限制于 upload_dir；客户端不得把 source 当可执行的本地路径 |
| `/chat` 与检索区别 | `api.py:361`、`enterprise.py:209` | 生成回答，并可能写会话；路由不转发 top_k；Phase 6 原文证据工具不应拿 answer 代替 document |

`QueryRequest` 的具体限制仍为：question 1–4000 字符，knowledge_base_id 默认 `default`，top_k 默认 10、范围 1–50，其他筛选字段可空。实际部署还能用 `max_query_chars` 收紧问题长度。租户/角色来自验证 Token 后的服务端用户记录，客户端不能提交身份字段替代认证（`api.py:222`、`security.py:202`）。

检索结果没有保证提供设备 model、属性 actual_value、单位 unit 或适用配置。必须在新工程校验并保留“未知”，不能从 source 文件名或检索相似度补造这些业务字段。使用 document_id/version_id 过滤前，也需要明确的型号—允许文档/版本映射和服务端授权；旧服务还验证输出 version_id 属于当前授权版本集合（`enterprise.py:129`）。

### 8.3 启动和请求的写入副作用

| 操作 | 已核实行为 | 本次处理 |
|---|---|---|
| 导入或启动 V3 API | `api.py:560` 调用 create_app；第 113 行构建 Catalog；`catalog.py:51` 创建目录，第 60 行 WAL，第 189 行执行 schema | 没有导入或启动 |
| `GET /health` | `api.py:181` 豁免自定义观测中间件；第 258 行仅返回设置中的状态、版本、collection 和 auth_configured；无业务 DB/索引调用 | 已知运行实例的 handler 可作轻量探测，但当前没有建立连接，未发送请求；外部访问日志行为未知 |
| `GET /ready` | `api.py:300` 打开 Catalog 连接，第 302 行 mkdir runtime；请求仍经过观测 | 不作为旧仓库只读探测 |
| `POST /retrieve` | `enterprise.py:49` 懒初始化 VectorStore；`vectorstore.py:54` 准备运行目录；`embedding.py:93` 可创建模型缓存；QueryProcessor 第 191 行准备目录，启用 rewrite/expansion 时可写 JSON cache | 没有请求；不能视为无文件写入的“读取” |
| 登录、检索、版本列表、下载 | `api.py:178` 请求观测；默认 `observability/config.py:25` enabled=true、第 26 行 exporter=local；`observability/core.py:383` 写请求 JSONL，metric/trace 也可能写文件 | 默认配置下不能保证旧仓库零写入；没有请求 |
| 首次版本列表/下载 | `api.py:201` 懒构造 Lifecycle；`lifecycle.py:93` ensure_runtime_dirs、第 94 行 create_vectorstore，即使最终业务方法只读 Catalog/PDF | 没有请求；不能因 HTTP GET 就推定无副作用 |

源码默认关闭 query rewrite 和 expansion（`config.py:157`），默认启用 reranker（第 150 行）。这些是源码默认值，不是已运行实例的实际配置；本次未读取 `.env` 或进程凭据。没有 conversation_id 可减少上下文改写成本，仍不消除模型加载、缓存、Catalog WAL 和观测写入。

**在“RAG-DEMO 绝不修改”的约束下，不自动启动旧服务，也不假定可以安全调用默认 `/retrieve`、登录或下载。** 后续真实验收需要已经准备好的、具备明确访问授权的独立 RAG 服务，以及对该服务请求副作用的确认；也可以由用户另行提供或授权完全隔离的服务实例。不能为本次调查安装旧依赖、改旧配置或迁移数据库。

### 8.4 资料与未完成项

仅列出 `data/pdf` 文件名，当前有 `employee_handbook.pdf`、`expense_policy.pdf`、`security_policy.pdf`、`travel_policy.pdf`。未打开 PDF、未查询 Catalog/索引，不能推定它们已发布或对当前用户可见，也不能把公司制度资料作为设备规格证据。

真实验收仍缺：可访问服务 URL、可用且授权的 Bearer 凭据、知识库/文档/版本范围、目标设备资料与型号映射、返回 metadata 完整性、原始 PDF 的 source/page 回查结果。错误路径仅静态核实：401、403、404、409、413、422、429（Retry-After）、503，以及可能的未处理 500；真实错误体、代理及部署行为未验证。

新工程可以先实现有限超时、明确错误类别、严格证据字段校验和 Mock HTTP 集成测试；这些验证应分别注明“离线契约/模拟服务”，不标记真实 RAG 访问成功。

### 8.5 新工程的 PDF 引用核查验证

新增 `src/agent_demo/integrations/citation_verifier.py:verify_citation`：调用方提供 PDF bytes 或明确允许目录内的 Path、期望的整份 PDF SHA-256、source、quote、page，并明确声明 `page_semantics="pdf_physical_1_based"`。代码只读给定文件，使用 pypdf 的 `PdfReader` 和 `reader.pages[page - 1].extract_text()`，按实际 PDF 物理页核查；不下载文件、不猜印刷页偏移、不补造引用 ID、不调用 LLM/OCR。

引用验证同时要求哈希匹配、物理页存在、原文片段出现在该页。匹配只合并空白，不修改大小写、标点或数值。缺哈希、未知页码语义、引用页越界、引文不匹配、无可提取文字、加密或解析失败都会保留明确的未验证结果。source 标签和文档/版本授权由上游契约及映射校验，PDF 检验本身不把任意 source 字符串认定为可信身份，也不证明型号适用或业务 FC。

实际执行：

```powershell
.venv\Scripts\python.exe -m pytest tests/test_phase06_citations.py -q
.venv\Scripts\python.exe -m ruff check src/agent_demo/integrations/citation_verifier.py tests/test_phase06_citations.py
```

结果：**32 passed**，Ruff 全部通过；实际安装并执行的解析器为 **pypdf 6.20.1**。测试使用手工构造的有效两页 TEST PDF，真实解析页面并验证内容、哈希、页码、空白归一化、数值不匹配、加密文件及允许路径范围。需要落盘的测试仅写 pytest 临时目录，没有读取旧工程 PDF 或改动旧仓库。

**这证明新工程能够验证调用方给出的 TEST PDF 引用，不证明真实 RAG 的 source/page 已通过回查。** 真实服务原文与授权 PDF 的对应关系仍等待前述 BLOCKED 项解除。实现接口参考 [pypdf 官方文本提取文档](https://pypdf.readthedocs.io/en/stable/user/extract-text.html) 与 [PdfReader API](https://pypdf.readthedocs.io/en/stable/modules/PdfReader.html)。

## 2026-10-17 全阶段审计补记

旧RAG只读核查HEAD仍为`d72c329`，Git工作区干净；未启动、导入、重新索引或调用旧服务。当前进程没有配置RAG URL/Token。用户再次明确“尚未具备，先完成软件和隔离测试，真实验收保留BLOCKED”。因此没有新的真实响应、文档、来源页码或引用通过记录，不改写上述未知项。

SOC应用复用既有HTTP客户端及绑定/PDF核验路径，实际HTTP Mock+TEST PDF通过不代表真实资料通过。发现Windows CPython3.11的monotonic小期限分辨率问题，客户端统一改用perf_counter；原失败XML与修复回归保存于`outputs/completion-audit/`。服务接口契约未被修改。
