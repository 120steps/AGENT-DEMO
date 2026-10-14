# Phase 6：固定检索与 Agentic RAG 对比记录

日期：2026-10-14。**真实评测 BLOCKED；本次仅 offline_mock 控制实验。**

HTTP 使用 MockTransport，模型使用明确脚本响应，文本标注 TEST ONLY。脚本预设的检索决策只验证真实 `create_agent` 的循环和预算机制，不能冒充 LLM API 决策或真实设备资料。真实用例集合尚为空。

实际命令：

```powershell
.\.venv\Scripts\python.exe examples\phase06_agentic_rag.py --offline --mode benchmark
```

运行 JSON：[offline-benchmark-20261014-45261010.json](../../outputs/phase06/offline-benchmark-20261014-45261010.json)，处于 Git 忽略目录。用例定义：[agent_test_cases.json](../agent_test_cases.json)。

| 离线用例 | 固定检索次数 | Agent 检索次数 | Agent 控制状态 |
|---|---:|---:|---|
| 普通问候 | 1 | 0 | completed |
| 一次检索 | 1 | 1 | completed |
| 补充检索 | 1 | 2 | completed |
| 空证据 | 1 | 1 | PENDING |
| 冲突形状的片段 | 1 | 1 | completed（仅检索循环结束） |
| 服务错误 | 1 | 1 | failed |

两侧平均检索次数均为 1。此运行 Agent 离线控制耗时平均 15.67 ms，包含脚本模型与框架开销；没有远端检索、真实模型或网络延迟，不能用于真实性能排名。普通问候避免了检索，补充场景多检索一次，只证明控制分支可执行。

冲突用例的 completed 不表示 FC：没有型号/PDF 绑定，业务层保持 PENDING。另有测试使用两个不同数值的实际 TEST PDF，分别核查哈希、物理页及原文后，确认确定性图识别冲突并保留两方证据。

| 实际效果指标 | 结果 |
|---|---|
| 真实任务成功率 | unavailable，缺授权真实服务和设备问题/标准答案 |
| 真实 PDF 引用准确性 | unavailable，真实 HTTP + PDF 验收未执行 |
| 真实缺证据处理准确性 | unavailable；离线空结果及未知字段门禁通过 |
| 真实平均工具/检索次数、耗时 | unavailable |
| Token Usage / 成本 | 脚本无真实 usage，available=false；价格未核实，费用不可估算 |
| 模拟控制用例 | 六类检索次数和终态与用例定义一致，自动回归通过 |

可执行真实对比入口已实现：

```powershell
# 仅在安全独立服务、模型凭据和真实用例已准备后使用。
.\.venv\Scripts\python.exe examples\phase06_agentic_rag.py --mode benchmark --case-file data\private\live-cases.json
```

该 manifest 的 `live_cases[]` 要提供 id、query、scope、人工 requirements、DocumentBinding 和 expected_status。代码对同一问题固定检索一次和有限 Agent 检索分别调用同一业务图，记录终态、已知标签下的成功与否、实际 PDF 引用比例、调用次数、耗时和可得 usage。没有标准答案或引用时相应指标保持 None，不填充虚假准确率。

没有预设 Agentic RAG 优于固定检索。目前能得出的结论仅是两种控制方式均可运行；需要真实同题评测才能比较效果。
