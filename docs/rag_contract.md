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
