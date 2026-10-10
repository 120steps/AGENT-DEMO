# Phase 0 总结：建立可安装、可验证的 Python 工程

完成日期：2026-10-10。状态：已验收。环境：Windows 10 x64 / CPython 3.11.0。

本文记录 Phase 0 结束时的工程快照。当前进度以 [路线图](../AGENT_LEARNING_ROADMAP.md) 为准，实际命令和失败修复见 [验证记录](phase00_validation.md)。

## 1. 这一阶段做了什么

开始时，工程只有 Git 初始化和路线图，没有提交、Python 包或开发环境。本阶段建立了后续开发的基础：

- 核对现有仓库和远端，没有重复初始化或克隆。远端查询成功，但未返回 HEAD 或分支引用。
- 创建独立 `.venv`，隔离新工程与旧 RAG 工程的依赖。
- 使用 `pyproject.toml` 定义安装、开发依赖及检查规则，建立 `src/agent_demo` 包。
- 安装 pytest、Ruff 和构建工具，保存 10 个外部依赖的实际固定版本。
- 实现配置读取与校验、无模型调用的 hello 示例，以及 6 个离线测试。
- 创建第二个全新虚拟环境，按固定清单安装并验证，证明安装流程可复现。
- 只读调查旧 RAG 接口，记录证据字段、使用边界和未知项。
- 经授权创建本地提交，没有推送，没有启动或修改旧 RAG 工程。

## 2. 最重要的是什么

**重点是证明工程真正安装成功，而且环境可以重新建立。** 编辑器能跳转、文件存在或在根目录运行成功，都不足以单独证明安装正确。

### `.venv`：项目自己的工具箱

它保存这个项目使用的 Python 入口和依赖，让不同项目可以使用不同版本。直接执行 `.venv\Scripts\python.exe`，能避免终端激活状态导致选错解释器。

虚拟环境不提交 Git。重新建立环境依靠 Python 版本、依赖清单和安装步骤，而不是复制整个 `.venv`。

### `pyproject.toml` 和 `src` 布局

`pyproject.toml` 告诉工具这个包叫什么、支持什么 Python、怎样安装、依赖哪些工具，同时集中保存 pytest 和 Ruff 配置。

`src` 布局把可导入代码与根目录的示例、测试、文档分开，有助于发现“没有安装，只是碰巧从当前目录导入”的问题。安装时的分发包名是 `agent-demo`，代码中的导入名是 `agent_demo`。

### Editable install：可编辑安装

执行 `pip install -e .` 后，环境中的包导入指向源码。修改源码后通常不用重装；修改依赖或包元数据后需要重新安装。

本项目的测试在工程外的临时目录启动 Python，并用 `-I` 忽略 PYTHONPATH 和当前目录的导入影响。仍然能导入 src 下的包，才证明安装关系生效。

## 3. 当前大致框架

当前是具备开发和验证基础的最小 Python 包，Agent 执行链路尚未实现。

```text
pyproject.toml + requirements-lock.txt
                  ↓ 安装
              独立 .venv
                  ↓ 可编辑安装指向源码
          src/agent_demo/
          ├── __init__.py：包入口，无导入副作用
          └── config.py：读取并校验非敏感配置
                  ↑
        ┌─────────┴──────────┐
        │                    │
examples/phase00_hello.py  tests/test_phase00.py
环境与安装信息演示        配置规则与工程外导入验证

docs/：学习总结、验证证据和 RAG 契约
AGENT_LEARNING_ROADMAP.md：唯一进度入口
```

配置数据流：

```text
进程环境变量，或测试显式传入的字典
                    ↓
              load_settings()
                    ↓
      补默认值 → 规范大小写/空格 → 校验
                    ↓
        不可变 Settings，或明确的 ValueError
```

当前只读取 `AGENT_DEMO_ENV` 和 `AGENT_DEMO_LOG_LEVEL`，默认 development 和 INFO。空值或错误值立即拒绝。`.env.example` 是配置说明，代码不会自动加载 `.env`，也不需要 API Key。

| 关键文件 | 职责 |
|---|---|
| [pyproject.toml](../pyproject.toml) | 安装规则、Python 范围、开发依赖与工具配置 |
| [requirements-lock.txt](../requirements-lock.txt) | 固定外部依赖，项目自身单独安装 |
| [config.py](../src/agent_demo/config.py) | 集中读取配置，尽早暴露错误 |
| [hello 示例](../examples/phase00_hello.py) | 展示解释器、虚拟环境、包路径和配置 |
| [离线测试](../tests/test_phase00.py) | 验证配置规则和真实安装导入 |
| [.gitignore](../.gitignore) | 排除环境、密钥、缓存和运行数据 |
| [README](../README.md) | 安装、运行与排错入口 |
| [RAG 契约](rag_contract.md) | 提前识别后续集成的证据与权限缺口 |

## 4. 怎么证明它完成了

| 验证 | 阶段结束时的结果 |
|---|---|
| 主环境可编辑安装 | 成功，agent-demo 0.1.0 |
| pytest | 主环境和全新验证环境均为 6 passed |
| Ruff、格式检查、pip check | 通过 |
| hello | 正确显示虚拟环境和 src 包路径 |
| 依赖固定版本 | 两套环境的 10 个外部包版本一致 |
| Git 与隔离 | 本地提交完成，运行文件已忽略，旧工程只读调查 |

实际复现步骤见 [README](../README.md)，完整证据见 [phase00_validation.md](phase00_validation.md)。本总结只提炼结论，不复制整份日志。

阶段代码提交：`08dc5b4`；验收收尾提交：`f87ec8d`。本总结是在验收后补充的学习记录，这两个提交不包含本总结。

## 5. 问题、限制与容易误解的地方

- Git Schannel 凭据错误通过命令级 OpenSSL 后端解决，没有修改永久 Git 配置。
- 默认 pip 配置导致安装等待，通过隔离配置、明确 PyPI 地址和有限超时/重试解决。
- 无提交仓库中的 `pip freeze` 会尝试识别 editable 的 VCS 信息并警告，最终用 `pip list --format=freeze --exclude-editable` 导出外部依赖。
- 固定清单适用于已验证的 Windows x64 / CPython 3.11 环境，不含文件哈希或跨平台保证。第二台电脑和 Linux 尚未验证。
- Python 3.11.0 是较早补丁版本，升级时需要重建环境并重跑检查。
- 旧 RAG V3 源码提供 `/retrieve`、`/chat`、原文、物理页和版本标识，但没有专用设备型号字段。实际服务、凭据和设备资料是否就绪仍未知。
- 静态阅读只能核实源码逻辑，不能证明部署后的实际响应。真实 RAG 请求留待 Phase 6，并先处理启动和调用可能写数据的权限边界。

## 6. 下一阶段怎么接着做

Phase 1 先选定实际可用、支持工具调用的模型、对应 SDK 和 API 协议，再完成最小工具闭环：模型提出调用请求，应用校验并执行工具，然后返回结果。

继续复用包结构、配置入口、隔离环境和测试方式，只逐步引入当前需要的代码与依赖。每个阶段验收时都生成对应的总结文档。
