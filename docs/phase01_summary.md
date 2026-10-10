# Phase 1 总结：原生 Tool Calling

记录日期：2026-10-10。状态：技术验收通过，DOING（待授权本地提交）；真实 API 验收结果见[技术记录](phase01_tool_calling.md)。交付状态以路线图为准。环境：Windows x64 / Python 3.11.0 / google-genai 2.29.0 / gemini-3.5-flash-lite。

## 1. 这一阶段做了什么

在 Phase 0 的独立环境与 src 工程上增加两个本地工具：严格校验的加法，以及明确标记 MOCK 的交换机规格查询。新增工具菜单与白名单 Dispatcher、Gemini 官方 SDK 适配器、单轮控制流程和可运行示例。业务数据为模拟数据，不接入真实 RAG，不修改旧工程。

离线模型用固定脚本产生调用请求，真实模式使用 Gemini API；两者共用 Dispatcher。通过业务、故障和协议测试验证执行边界。README、锁定依赖与学习解释同步维护。

## 2. 最重要的是什么

最重要的一句话：模型提出调用请求，程序校验并执行，结果再交回模型。

工具 Schema 是菜单和参数约定，不能代替本地校验。Dispatcher 是执行入口，只允许两个工具，拒绝布尔值、非有限数字、路径、命令及额外参数。调用关联让返回结果与原请求对应：实际 Gemini ID 可能缺省，不应凭空编造 ID；原始模型上下文必须保留。

## 3. 当前大致框架

```text
examples/phase01_tool_calling.py
  ├─ config.py：复用应用配置 + 模型环境配置
  └─ agents/tool_calling.py：单轮控制、事件、终止状态
       ├─ integrations/gemini.py：手动 SDK 协议、模型上下文
       └─ tools/__init__.py：Schema → 白名单 → 校验 → 本地执行
tests/test_phase00.py + tests/test_phase01.py
```

相比 Phase 0，包已经能接受模型提出的工具请求。最多两次模型请求，一轮至多四项工具顺序执行。还没有多轮 Agent Loop、框架、真实 RAG 或服务 API。

关键入口：[示例](../examples/phase01_tool_calling.py)、[控制器](../src/agent_demo/agents/tool_calling.py)、[SDK 适配器](../src/agent_demo/integrations/gemini.py)、[工具](../src/agent_demo/tools/__init__.py)。

## 4. 怎么证明它完成了

主环境和独立 `.venv-phase1-check` 均通过 42 项离线测试，包括原 Phase 0 的 6 项。两套环境的 Ruff、pip check、Phase 0 示例与 Phase 1 Mock 示例均通过；35 项外部包已固定版本，并在新环境真实安装。

真实模型实际完成加法闭环（15+27=42）、规格闭环（MOCK-SW-48，48个GE、4个10GE）、问候直接回答；三个真实示例均退出 0。完整命令、轨迹及失败修复见[技术说明](phase01_tool_calling.md)。Mock 通过只能证明控制器与工具工作，不能代替真实 API。当前代码未提交，本阶段提交需独立授权。

## 5. 问题、限制与容易误解的地方

`gemini-flash-latest` 两次生成返回 ServerError；切换稳定模型后，原 `role='tool'` 回传触发 HTTP 400。依据安装版 Content 类型说明改为 `role='user'`，补测试后真实闭环通过；这也是不能只靠 Mock 验收的原因。首次 Ruff 及文档代码块格式检查失败均已修复。SDK 自动函数执行关闭；即使模型提出新的请求，也不会在第二次响应后继续执行。

规格只覆盖 MOCK-SW-24、MOCK-SW-48；模拟规格不是产品证据。无效参数与工具异常是不同状态。日志只展示实际事件，签名上下文不是可展示的推理过程。其他操作系统与模型组合未验，模型别名可能变化。

## 6. 下一阶段怎么接着做

先完成 Phase 1 的授权版本交付。随后进入 Phase 2：为多步“查询规格 → 计算/比较 → 回答”增加有上限的循环、超时、预算、usage 和终止测试，再补离线 CI。复用当前工具、校验和 SDK 适配器，不复制业务规则。
