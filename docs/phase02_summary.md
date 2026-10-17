# Phase 2 总结：原生 Agent Loop

日期：2026-10-10。状态：技术验收完成，DOING（待本地提交授权）。环境：Windows x64 / CPython 3.11.0 / google-genai 2.29.0 / gemini-3.5-flash-lite。

## 做了什么

将 Phase 1 单轮 Tool Calling 扩展为多轮循环，支持同轮多个工具顺序执行、连续模型请求、模型重试、工具/任务超时、轮数与调用数预算、usage 累计及明确终止状态。复用原有工具、Schema、Dispatcher 和 Gemini 适配器，没有引入框架或 RAG。

## 最重要的理解

模型决定下一步动作，程序决定动作是否允许执行。循环必须有轮数、工具数、时间和重试上限；达到限制时返回 `budget_exceeded`、`timeout` 或 `failed`，不能伪装为成功。

## 当前框架

```text
examples/phase02_agent_loop.py → agents/agent_loop.py
  → integrations/gemini.py（逐轮 Content + FunctionResponse）
  → tools/（白名单、校验、执行）
tests/test_phase02.py + GitHub Actions CI
```

贯穿样例为 `lookup_product_spec(MOCK-SW-48) → add(48, 4) → 最终回答 52`。

## 验收与限制

主环境 46 项测试通过，Ruff check/format 通过，Mock 三轮通过；真实 Gemini 多步任务成功，调用顺序为 lookup_product_spec、add，最终回答 52。CI 已建立，GitHub runner 尚未单独执行。工具超时只能停止等待，不能强制终止外部副作用；当前工具均为短时本地纯函数。

下一阶段进入 Phase 3：验证 LangChain 标准 Agent，并与当前原生实现对比。

## 2026-10-17 补齐复核与版本收尾

上文保留2026-10-10阶段快照。后续审计发现的等待/配置/消息控制缺口已修复，通过本次新增控制测试和439项整合回归，原生多步Demo仍成功。用户明确授权后实现版本`ee192a3`已创建，Phase2收尾DONE。真实LLM依据原日期记录，本次无Key、没有重新验证真实API；新修复的SDK消息与限制通过离线验证。真实RAG和毕业验收仍BLOCKED，实时进度见根目录路线图。
