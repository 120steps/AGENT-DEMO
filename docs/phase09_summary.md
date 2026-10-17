# Phase 9 阶段总结（部分验收）

日期2026-10-17。状态BLOCKED：9A本地软件已验证，9B实际容器/Linux验收缺Docker；未达到整个Phase9完成标准。当前进度见[路线图](../AGENT_LEARNING_ROADMAP.md)。

## 1. 做了什么

增加[FastAPI入口](../src/agent_demo/api/app.py)，提供任务、状态、审核、恢复、取消、Excel获取和PDF候选确认；复用[SOCService](../src/agent_demo/soc/service.py)、原业务图及Checkpoint。提供Dockerfile、Compose、隔离构建上下文及CI。

## 2. 最重要的概念

任务ID只是定位信息，Bearer身份与SQLite owner才决定访问权限；停止等待不等于取消已执行的动作；进程内队列不是分布式可靠调度平台。

## 3. 当前框架

HTTP/Pydantic → owner/限流/有界队列 → SOCService → 原业务图/审核图 → SQLite Checkpoint与操作账本 → DRAFT Excel。配置与真实文档绑定由部署方控制，请求不能选择任意服务或可信证据。

## 4. 验收证据

[真实本机HTTP验收脚本](../examples/project_acceptance.py)实际停进程并重启，验证审核版本、修改、拒绝、重复批准、下载与重启后字节一致。自动化测试覆盖权限和副作用。全部命令、统计和路径见[全阶段审计](project_completion_audit.md)。

## 5. 限制

真实产品/RAG毕业验收BLOCKED；Linux固定版本清单仅候选；Docker与远端CI未运行。必须单个服务进程/单个Uvicorn worker，不能多个实例共享运行目录；尚无公网TLS/SSO/分布式限流与调度。

## 6. 下一步

提供安全RAG及固定版本资料；在Docker可用环境执行构建、持久化重启验收，检查Linux依赖。详见[API操作说明](phase09_api.md)。不把部署材料存在当作部署通过。
