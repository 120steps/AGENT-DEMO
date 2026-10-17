# 全阶段整合基线（本地软件与隔离样本）

执行日期：2026-10-17。环境Windows x64 / CPython3.11.0；起点/当前已提交HEAD为`9cea417`，本次修改未提交。实际依赖、源码/用例Hash、Benchmark和详细统计保存在[JSON](project_completion_baseline.json)。历史Phase6/8基线与本次初始失败均保留。

## 验证范围及结果

| 范围 | 实际结果 | 不代表什么 |
|---|---|---|
| 初始完整pytest | 394通过、1失败、1跳过 | 不掩盖Windows期限失败 |
| 最终完整pytest | 439通过、0失败、1跳过；新增44项 | 跳过的真实服务/PDF未运行 |
| Phase8统一评测 | 44/44符合预期；4 BLOCKED不计分母 | 不是真实SOC任务成功率 |
| 工具执行 | 16/18成功，88.89%；24请求 | 正确拒绝不算执行成功；2次预设故障 |
| 状态判断 | 18/18正确，FC/NC错判0 | 不推广为任意条款准确率 |
| 安全硬门槛 | 未授权写入0、无证据FC0、接受伪造引用0 | 不证明真实LLM抵御任意注入 |
| 已接受引用 | 成员/来源映射各6/6 | Mock映射不是原产品PDF真值 |
| 候选TEST PDF | 1/2，错误页码被拒绝 | 被拒绝候选不是接受错误引用 |
| 真实PDF | unavailable，0样本 | 不填充虚假准确率 |
| 实际本机HTTP | 18/18检查通过，两次进程重启 | 通信真实，业务数据仍MOCK |
| Excel | 16行、10个内部证据链接、中文/字面文本/结构化修改与审核版本回读正确 | 未生成正式客户结论 |
| Docker/Linux | BLOCKED，Docker命令不存在 | Dockerfile/CI存在不等于构建通过 |
| 真实LLM/RAG/RFP | BLOCKED，未调用 | 无Token Usage、费用与真实波动结果 |

pytest控制台104.73s，XML suite时间104.453s，计时范围不同。统一评测与18项HTTP检查有重叠，不把它们与439个单元/集成测试相加伪造“总样本量”。实际HTTP脚本另检查拒绝、归属、修改、新版本、旧审核拒绝、重复批准、重启后字节一致与下载回读。

## 控制修复与实际业务能力

修复原生线程池超时后仍等待退出的问题；Gemini输出配置下传、历史工具结果去重；模型重试计入轮数和累计token。LangChain增加独立执行Guard、严格输入Schema、错误ToolMessage、实际等待期限和同题对照。数值/单位及复合条款业务规则继续使用原Phase4。

SOC应用通过可信HTTP绑定/原文核验路径接受真实证据，但当前只完成HTTP Mock+TEST PDF证明；未验证真实服务兼容性。结构化JSON/人工确认PDF要求可以运行原判断和审核图并生成有来源的DRAFT XLSX。审核快照包含导出类型/目录/模板范围；业务审核和文件授权不混为一谈。

## Benchmark解释

三组Benchmark仍复用原Phase8实现，同一脚本问题与模拟资料，模型/Prompt/协议封装存在差异；原生/框架各3样本，直接Tool/MCP warm各3样本、启动单列，固定/Agentic沿用6场景。本轮原生/框架任务均成功，预算护栏增加的应用开销也在测量内；具体每样本毫秒见JSON。

控制分支与历史Phase8保持一致：44通过、4阻碍、安全三项0。当前真实质量及供应商usage未可得，因此不推导模型或框架优劣，也不设基于当前成绩反推的性能门槛。真实资料版本及RFP覆盖率为Unknown，不能声称Agentic Retrieval优于固定检索。

## 失败与阻碍保留

初始失败XML：`outputs/completion-audit/baseline.xml`；修复前失败是有效发现，不覆盖。开发阶段更严格Pydantic校验提前抛ValidationError，旧测试按具体类名判断失败；改为验证ValueError边界，依旧要求非法输入被拒绝，没有放宽业务数据。新增加真实os._exit()测试验证批准Checkpoint与任务审计同步窗口。

最终XML：`outputs/completion-audit/final-regression.xml`；最终评测：`outputs/phase08/20261017T104232Z-b2125c92/`；HTTP及Excel：`outputs/completion-acceptance/430c3358a0ee4facb033b9267f6fad64/`；Docker阻碍：`outputs/completion-acceptance/fa422e751174498a8033453c2d9b586e/`。运行库、日志和生成文件都不进入Git。

真实毕业仍需安全RAG、固定资料/型号/BOM、人工10–20条参考答案、真实RFP标注及Docker/Linux环境。用户明确同意先完成软件与隔离测试，保留这些验收BLOCKED。完整进度以[路线图](../../AGENT_LEARNING_ROADMAP.md)为准，缺口见[审计](../../docs/project_completion_audit.md)。
