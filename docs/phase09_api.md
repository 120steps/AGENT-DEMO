# 本地任务 API 与部署边界

最小API已实现并实际验证本机HTTP重启恢复；Dockerfile/Compose及CI已增加，但本机没有Docker，Linux/容器实际运行保持BLOCKED。不是公网部署、分布式任务系统或正式客户发布。

## 运行

```powershell
# 将至少24字符、互不相同的随机Token通过进程环境安全注入。
# AGENT_DEMO_API_TOKENS 的JSON结构是 {"操作员标识":"对应Token"}，不要提交真实值。
$env:AGENT_DEMO_DATA_ROOT = 'D:\workspace\AI\AGENT-DEMO'
.\.venv\Scripts\python.exe -m uvicorn agent_demo.api.app:create_app --factory --host 127.0.0.1 --port 8080 --workers 1
```

没有认证配置就拒绝启动。模型Key、RAG配置、绑定文件仅由受信部署方设置，API不能传任意URL、PDF路径、命令或可信Evidence。不要将API Token放在URL或代码中。程序不自动加载.env。

| 接口 | 用途 |
|---|---|
| GET /health | 健康检查，说明本地单工作线程模式 |
| POST /tasks | Pydantic JSON输入，返回202，交给有界后台队列 |
| GET /tasks/{id} | 状态、拟议业务结果和待审快照 |
| POST /tasks/{id}/run | 重启后显式重新调度pending任务 |
| POST /tasks/{id}/review | approve/reject/modify，必须携带实际审核版本和摘要 |
| POST /tasks/{id}/cancel | 阻止后续动作；不假装撤销已完成副作用 |
| GET /tasks/{id}/result | 当前审核版本的XLSX；未批仅允许显式草稿 |
| POST /rfp/parse | Base64文本PDF→定位候选、原文和警告 |
| POST /rfp/confirm | 人工字段映射及排除原因→确认输入 |

所有任务操作先检查Bearer对应owner；未知任务与他人任务统一404。审核响应错误不回显敏感输入。限流默认每身份60次/分钟，有界队列最多4项，单个任务工作线程；body最大15MB且读取有期限。只在本进程内限流，不宣称跨实例共享。

状态为pending/running/awaiting_review/completed/failed/cancelled。拒绝映射cancelled，具体审核动作保存在应用审计和Graph历史。服务启动将遗留running标记pending，显式run后根据Checkpoint继续，不自动发布文件；等待审核任务保持快照。取消是协作式停止，已在执行的HTTP请求可能继续结束。批准和取消通过同一进程锁避免竞态，已完成结果不能“取消回滚”。

任务/审核/Checkpoint/账本位于runtime/soc，产物位于outputs/phase05及outputs/soc；旧Demo使用原有目录。必须使用单个Uvicorn worker、单个服务进程，不能让两个服务同时挂载同一运行目录。当前没有跨进程调度租约或多实例协调。

## 运行验证

```powershell
.\.venv\Scripts\python.exe examples\project_acceptance.py
```

它真实启动Uvicorn、通过HTTP提交16条MOCK要求，等待审核后停止子进程并重启，修改并重新审核、拒绝旧版本、批准/重复批准、下载回读、再次重启核验字节一致，以及拒绝后禁止导出。输出目录唯一，Token只在子进程环境中传递。控制日志不包含请求认证头和文档全文。

## 容器与CI

```powershell
docker compose config
docker compose up --build -d
# 容器内部PDF绑定文件路径必须属于挂载的/app/data/private。
docker build -t agent-demo:local .
.\.venv\Scripts\python.exe examples\project_acceptance.py --docker-image agent-demo:local
```

Compose只映射127.0.0.1，使用非root用户、只读根文件系统、临时/tmp、受限能力和持久化runtime/outputs卷。私有资料只读挂载，不进入镜像；不要执行删除有效卷的数据清理命令。停止可以使用`docker compose stop`，恢复使用`docker compose start`。

Windows80项固定版本已经实际安装核验；requirements-linux.txt仅移除Windows专用pywin32的Linux候选，**尚未验证安装兼容**。CI增加Windows/Linux回归、离线Evaluation和真实本机HTTP检查；独立容器job实际构建并执行同一HTTP重启脚本，使用本次UUID命名的临时容器及卷。当前没有推送或执行GitHub runner，因此不能宣称远端CI或容器通过。

官方实现依据：[FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/)、[认证机制](https://fastapi.tiangolo.com/tutorial/security/first-steps/)。当前API使用官方依赖注入、HTTPBearer及lifespan管理线程池；认证值由应用验证和任务归属检查，并非SDK自动提供业务授权。
