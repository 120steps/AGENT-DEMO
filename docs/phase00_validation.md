# Phase 0 实施与验证记录

日期：2026-10-10（Africa/Cairo）。工程：`D:\workspace\AI\AGENT-DEMO`。

## 1. 实际结论

本地环境、包安装、离线测试、源码静态接口调查和敏感文件排除检查已完成。两个独立虚拟环境均通过验证。经用户明确授权，已创建本地根提交 `08dc5b4`；没有推送，没有实施 Phase 1，没有启动或修改旧 RAG 工程。

技术验收与本地版本交付均已完成，路线图 Phase 0 标记 DONE。以下保留初次调查和安装验证的历史记录；授权后收尾记录见第 7 节。

## 2. 仓库与解释器调查

实际执行了 `Get-Location`、`git status --short --branch`、`git log -3 --oneline`、`git remote -v`、`git show-ref`。

- 初次调查时目录正确，main 尚无提交；当时 `git log` 因无提交退出 128，这是仓库现状而非代码失败。
- 远端 origin 为 `https://github.com/120steps/AGENT-DEMO.git`。
- 上游显示 `origin/main [gone]`；本地另有工具生成的 `refs/codex/...` 引用，没有修改它们。
- `git ls-remote --symref origin HEAD 'refs/heads/*'` 首次因 Schannel `SEC_E_NO_CREDENTIALS` 失败。
- 改用 `git -c http.sslBackend=openssl ls-remote --symref origin HEAD 'refs/heads/*'` 后两次查询均退出 0，输出为空，没有返回 HEAD 或分支。没有 fetch、创建分支、重置或修改永久 Git 配置。
- `py -0p` 输出 `No installed Pythons found!`；`python --version` 和 `sys.executable` 核实实际存在 CPython 3.11.0 x64，路径为 `C:\Users\Huawei\AppData\Local\Programs\Python\Python311\python.exe`。
- `python3` 指向 WindowsApps，未将其视为已验证解释器。本地 Python 安装目录只发现 Python311。
- 未在工程和已检查的上级目录发现适用的 AGENTS.md。

通过新工程的 Python 使用 urllib 读取 PyPI 发布元数据，核实 requires_python：FastAPI 0.143.0、LangChain 1.4.4、LangGraph 1.2.14、Pydantic 2.14.0、pytest 9.1.1 均包含 Python 3.11。仅安装当前所需的 pytest、Ruff 及构建工具，未安装这些未来框架。

元数据来源：[FastAPI](https://pypi.org/pypi/fastapi/json)、[LangChain](https://pypi.org/pypi/langchain/json)、[LangGraph](https://pypi.org/pypi/langgraph/json)、[Pydantic](https://pypi.org/pypi/pydantic/json)、[pytest](https://pypi.org/pypi/pytest/json)。后续引入时重新核实，不能将声明的解释器兼容性等同于依赖组合已经实测。

## 3. 主环境实际命令

在工程根目录按顺序执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip --isolated install --index-url https://pypi.org/simple --timeout 15 --retries 1 --disable-pip-version-check --no-cache-dir --upgrade pip 'setuptools>=77' wheel
.\.venv\Scripts\python.exe -m pip --isolated install --index-url https://pypi.org/simple --timeout 15 --retries 1 --disable-pip-version-check --no-cache-dir --no-build-isolation -e '.[dev]'
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe examples\phase00_hello.py
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pip list --format=freeze --exclude-editable
```

| 检查 | 实际结果 |
|---|---|
| venv / 构建工具 / editable 安装 | 退出 0；成功构建并安装 agent-demo 0.1.0 |
| pytest | 退出 0；`6 passed in 0.31s` |
| Ruff lint | 退出 0；`All checks passed!` |
| Ruff format | 退出 0；`7 files already formatted` |
| hello | 退出 0；Python 3.11.0、virtual_environment=true、包路径为工程 src 下文件 |
| pip check | 退出 0；`No broken requirements found.` |
| 外部依赖导出 | 退出 0；10 个固定版本，与 requirements-lock.txt 一致 |

6 个测试覆盖：显式配置映射与进程环境隔离、配置规范化、3 种错误配置拒绝，以及在工程外的临时工作目录使用 Python `-I` 导入已安装包。最后一项忽略 PYTHONPATH，验证导入来自 src 源码和已安装分发元数据，未在测试配置中设置 pythonpath 来掩盖安装问题。

## 4. 全新验证环境实际命令

创建 `.venv-phase0-check`，保留它作为本次复现环境，已被 Git 忽略，没有覆盖主环境：

```powershell
python -m venv .venv-phase0-check
.\.venv-phase0-check\Scripts\python.exe -m pip --isolated install --index-url https://pypi.org/simple --timeout 15 --retries 1 --disable-pip-version-check --no-cache-dir -r requirements-lock.txt
.\.venv-phase0-check\Scripts\python.exe -m pip --isolated install --disable-pip-version-check --no-cache-dir --no-build-isolation --no-deps -e .
.\.venv-phase0-check\Scripts\python.exe -m pytest -q
.\.venv-phase0-check\Scripts\python.exe -m ruff check .
.\.venv-phase0-check\Scripts\python.exe -m ruff format --check .
.\.venv-phase0-check\Scripts\python.exe examples\phase00_hello.py
.\.venv-phase0-check\Scripts\python.exe -m pip check
.\.venv-phase0-check\Scripts\python.exe -m pip list --format=freeze --exclude-editable
```

全部退出 0；pytest 为 `6 passed in 0.17s`，lint/format/依赖检查通过。hello 指向 `.venv-phase0-check\Scripts\python.exe`，包仍来自同一 src 目录。10 个外部依赖版本与主环境一致。

这是同机全新虚拟环境复现，尚未在第二台电脑或 Linux 验证；没有将已有环境的 site-packages 复制过去。

## 5. 遇到的问题与实际修复

1. Git Schannel 凭据错误：用仅本次命令的 OpenSSL 后端验证远端，未改永久配置。
2. 默认 pip 配置导致两次安装尝试长时间无输出：中止后使用 `--isolated`、关闭版本检查，并对网络安装指定 PyPI、15 秒超时和 1 次重试；成功。README 记录了修复后的命令，没有保存私有镜像地址或凭据。
3. `pip freeze --all` 在未提交仓库解析 editable VCS 信息时警告；加入 `--exclude-editable` 仍产生警告。最终改用 `pip list --format=freeze --exclude-editable` 导出外部包固定版本，避免绝对路径和 VCS 引用。
4. 旧仓库 Git 检查遇到 ownership 防护：只使用命令级 `-c safe.directory=...` 和 `--no-optional-locks`；没有修改全局 safe.directory 或旧工程配置。
5. 一次辅助 Python 进程枚举被系统拒绝；没有提升权限，使用已有安装会话中断机制停止等待中的 pip。
6. 一次辅助文件搜索误把 PowerShell 参数传给 rg；修正为 Test-Path 与 Get-Content 检查上级文件。没有因此修改项目内容。

测试、lint 和格式检查第一次运行均通过，没有隐藏失败或将未运行检查写成成功。

## 6. RAG 与 Git 交付检查

静态契约详见 [rag_contract.md](rag_contract.md)。旧仓库的只读 Git 状态检查在调查前、调查中和调查后均为空：

```powershell
git --no-optional-locks -c safe.directory=D:/workspace/AI/rag-demo -C D:\workspace\AI\rag-demo status --porcelain
```

本次没有向旧工程执行写命令、导入其模块、启动服务、读写数据库、运行测试或安装依赖。Git 状态相同是工作区检查证据，不被表述为对所有被忽略文件的全盘哈希审计。

新仓库执行 `git status --short --untracked-files=all`、`git ls-files`、`git check-ignore --verbose`。初次交付前 index 为空，所有交付文件尚未跟踪；以下模式已实测被忽略：`.env`、`.env.local`、两套 venv、runtime/checkpoint.sqlite3、outputs/result.xlsx、logs/run.log、Python 缓存。`.env.example` 只包含非敏感样例，授权后已纳入版本控制。

建议 commit message：`chore: initialize Phase 0 Python project and document RAG contract`。

最终核查共 12 个交付文件（11 个新建，路线图修改）；常见私钥、AWS Access Key、GitHub Token 模式扫描未发现匹配，非 Markdown 文件未发现行尾空白。这是有限模式检查，不是全面凭据审计。两套环境的 10 个外部包均逐项与固定版本清单比较一致。

仅在用户确认后创建本地提交；推送另行确认。本阶段不存在远端删除、force push 或发布操作。

## 7. 授权后的本地交付收尾

用户明确回复：授权本地提交及完成记录，不推送。

- 再次复核工程状态：仍为 12 个计划文件；无已暂存的其他用户内容。
- 再次运行主环境测试：6 passed in 0.33s；Ruff、pip check 和 hello 均成功；旧工程只读 Git 状态为空。
- 使用已有 Git 身份，未修改用户配置；Git hooks 仅有 `.sample` 文件。
- 默认沙箱无法创建 `.git/index.lock`，在已有授权基础上通过工具权限审查完成暂存及本地提交。
- 根提交：`08dc5b4`，提交信息 `chore: initialize Phase 0 Python project and document RAG contract`，12 个文件，1040 行。
- 顶部 Markdown 硬换行的双空格曾被 diff 检查提示，收尾改为 `<br>`；不影响业务代码。
- 完成状态、README 和本记录以另一个本地文档提交保存；最终哈希通过 `git log -2 --oneline` 获取，不在提交自身内容中循环记录自身哈希。
- 最终检查包含 `git diff --cached --check`、提交文件列表、忽略规则和 `git status --porcelain`；没有 push。

Phase 0 的环境和静态调查任务均已完成。真实 RAG 请求、设备资料及 API 授权留待 Phase 6，不作为本阶段缺失功能。
