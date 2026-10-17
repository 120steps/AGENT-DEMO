# Phase 2：原生 Agent Loop

本阶段把 Phase 1 的“一轮工具调用”扩展为受边界保护的多轮循环。

## 核心区别

Phase 1 是：模型请求一次 → 执行工具 → 回传 → 得到答案。Phase 2 允许模型根据上一轮 observation 再选择工具，直到直接回答或触发明确终止状态。模型决定下一动作，Python 决定是否允许执行。

同一轮可以返回多个 Tool Call，循环按模型给出的顺序执行，并保留每个 call ID。模型可以选择直接回答；没有调用时立即完成。

`run_agent_loop` 位于 `src/agent_demo/agents/agent_loop.py`，复用 Phase 1 的 `dispatch`、Schema 和 Gemini 协议适配器。每一轮记录 `ACTION` / `OBSERVATION`，同时记录轮次、耗时、调用 ID、token usage 和终止原因。

## 控制边界

`LoopLimits` 提供 `max_model_rounds`、`max_tool_calls`、`tool_timeout`、`task_timeout`、`max_retries` 与输出 token 上限。超过轮数或工具数返回 `budget_exceeded`，总期限或单工具超时返回 `timeout`，模型持续失败返回 `failed`，只有模型直接回答且未触发错误时返回 `completed`。

工具超时只停止等待并记录超时；Python 线程无法强制取消已经运行的外部副作用，因此本阶段工具必须是短时本地纯函数。重试只用于模型请求，次数有限；工具不会被隐式重复执行。

token usage 从适配器响应的 `usage_metadata` 累计。当前没有可靠价格表，因此成本字段为 `None`，状态为 `unavailable`，不会伪造金额。

## 消息流

```text
prompt
  → MODEL_REQUEST(round=1)
  → MODEL_RESPONSE(function_call A, B)
  → ACTION A → OBSERVATION A
  → ACTION B → OBSERVATION B
  → MODEL_REQUEST(round=2, 保留历史 Content 与结果)
  → MODEL_RESPONSE(function_call C)
  → OBSERVATION C
  → MODEL_REQUEST(round=3)
  → FINAL_RESPONSE / TERMINATION
```

有限轮数、调用预算、总期限和重试上限共同避免无限循环。每轮继续还是结束由模型响应是否包含 function call 决定，但执行资格始终由本地白名单与预算控制。

## 运行

```powershell
.\.venv\Scripts\python.exe examples\phase02_agent_loop.py --mock
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
```

Mock 贯穿样例先查询 `MOCK-SW-48`，再计算 48+4，最后回答 52。它是固定协议脚本，不根据 prompt 做意图识别。真实模式读取进程中的 `GEMINI_API_KEY`，不自动读取旧工程或 `.env`。

## 限制

### 2026-10-17 控制缺口修复

统一工程审计发现旧线程池context manager会在超时后等待线程退出；改用`agents/execution.wait_until`的有界等待，未结束操作明确标记取消未确认。重试也计入模型调用轮数；增加累计token限制和严格预算参数类型验证。Gemini每次运行接收输出上限与SDK请求期限；历史中已经成对保存的工具结果不再重复回传，保留原始调用ID和Content。

新增测试见`tests/test_completion_controls.py`，使用真实事件等待验证提前返回、脚本协议验证消息不重复和预算不伪装完成；本次没有模型凭据，没有新增真实LLM验证，原真实记录只代表当时版本。费用仍不可估算。

本阶段不实现持久化 checkpoint、人工审核、并发工具执行、真实 RAG、成本计费或强制终止外部进程。CI 只运行无密钥的 pytest 与 Ruff。真实多步验证结果以路线图和本文件的验证记录为准。
