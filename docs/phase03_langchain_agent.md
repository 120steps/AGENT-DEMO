# Phase 3：LangChain 标准 Agent

本阶段使用当前 LangChain 1.x 的 `create_agent`，复用 Phase 1 的业务函数和 Phase 2 的贯穿任务，不实现显式 LangGraph 工作流、checkpoint 或 RAG。

## 实现

`src/agent_demo/agents/langchain_agent.py` 中的 `build_agent` 调用官方 `create_agent(model, tools, response_format=AgentAnswer)`。两个 `@tool` 只是 LangChain 的输入描述和调用入口，真正业务校验仍由 Phase 1 `dispatch` 完成。`AgentAnswer` 是 Pydantic 最终结构化输出：型号、结论、总端口数。

LangChain 管理消息历史和工具循环；`recursion_limit` 是图步骤上限，不等于精确的工具调用次数。因此应用仍需在工具包装、调用超时、预算和外部任务层增加限制。本阶段保留 `max_model_rounds` 的映射作为图步骤保护，未把它宣称为完整成本控制。

## 与原生实现的区别

原生 Phase 2 手写 `while`、消息上下文、调用 ID、Action/Observation 和所有终止分支；LangChain 将模型绑定、工具消息往返和循环节点封装在编译图中。业务白名单、参数校验、工具异常、API 密钥隔离仍由应用负责。LangChain 依赖 LangGraph 运行时，但本阶段只使用 `create_agent` 公共 API，不编写 Phase 4 的显式图。

学习顺序先手写 Loop，再使用框架，是为了先理解模型消息、工具结果和终止边界；框架减少样板代码，却不会自动解决任意工具权限、超时取消、预算计费、敏感日志或业务正确性。

## 运行与验证

### 2026-10-17 控制与对照补齐

`ExecutionGuard`通过实际安装版`wrap_model_call`/`wrap_tool_call`实现模型尝试、工具尝试、输出/累计token、重试和期限；递归步数仅作为额外保护，不等同于业务次数。严格Pydantic Schema在任何类型转换前拒绝bool、字符串数值和额外字段，Middleware继续校验原Dispatcher允许列表。未知工具、非法参数与业务异常返回关联ToolMessage错误，模型仍可在预算内处理；预算/超时终止不会返回成功答案。

统一对照测试覆盖普通回答、同轮多个调用、连续多轮、执行异常、非法结构化输出、有限重试和实际停止等待。使用既有脚本模型与相同业务结果比较工具动作；原Phase8三组Benchmark再次运行，不据此比较真实模型质量。实际实现依据[官方Middleware API](https://reference.langchain.com/python/langchain/agents/middleware)，本机LangChain1.4.4通过回归；本次无Key，没有重新消耗真实API Token。

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe examples\phase03_langchain_agent.py
```

离线测试验证 Pydantic、工具包装、Dispatcher 错误边界及 `create_agent` 参数；真实模式读取 `GEMINI_API_KEY`，不自动加载 `.env`。当前结构化输出依赖模型供应商对 tool/structured response 的支持；不兼容时返回失败并记录类型，不伪造成功。

官方参考：[create_agent](https://docs.langchain.com/oss/python/langchain/agents)、[Google Gemini 集成](https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai)。版本实际验证为 `langchain==1.4.4`、`langchain-google-genai==4.4.0`。
