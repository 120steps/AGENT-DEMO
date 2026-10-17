"""Non-overwriting local reports with reproducibility metadata and no raw payloads."""

import hashlib
import importlib.metadata
import json
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path


def metadata(dataset, project_root):
    def git(*args):
        try:
            return subprocess.run(
                ["git", *args],
                cwd=project_root,
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return None

    versions = {}
    for name in (
        "agent-demo",
        "langchain",
        "langgraph",
        "pydantic",
        "mcp",
        "google-genai",
        "httpx",
    ):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "Unknown"
    prompts = {}
    for path in (
        "agents/tool_calling.py",
        "agents/agent_loop.py",
        "agents/langchain_agent.py",
        "agents/agentic_rag.py",
        "integrations/gemini.py",
        "mcp/tool_adapter.py",
    ):
        source = Path(project_root) / "src/agent_demo" / path
        prompts[path] = hashlib.sha256(source.read_bytes()).hexdigest()
    return {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "git_commit": git("rev-parse", "HEAD"),
        "worktree_status": git("status", "--porcelain"),
        "python": platform.python_version(),
        "platform": platform.system(),
        "dependencies": versions,
        "dataset_sha256": hashlib.sha256(Path(dataset).read_bytes()).hexdigest(),
        "prompt_and_controller_source_sha256": prompts,
        "model_provider": "scripted_offline",
        "model_id": "phase08-scripted-offline-not-llm",
        "provider_response_model_version": "Unknown",
        "sampling": "predetermined_fixture",
        "document_version": "MOCK-v1 / synthetic TEST PDF; not vendor evidence",
        "verified_price_source": None,
    }


def markdown(report):
    metrics = report["metrics"]
    task = metrics["task"]
    lines = [
        "# Phase 8 Evaluation Baseline",
        "",
        f"UTC: {report['metadata']['timestamp_utc']}",
        "",
        "本报告为本地可复现实验；脚本模型、HTTP Mock、TEST PDF 与真实 MCP stdio 分开标记。",
        "",
        f"Commit: `{report['metadata']['git_commit']}`；工作区状态见配套 JSON。",
        "",
        f"用例 {task['total']}；实际执行 {task['executed']}；PASS {task['pass']}；"
        f"FAIL {task['fail']}；TIMEOUT {task['timeout']}；ENV_ERROR {task['env_error']}；"
        f"BLOCKED {task['blocked']}；SKIPPED {task['skipped']}。",
        "",
        "成功率分母为 PASS+FAIL+TIMEOUT+ENV_ERROR；负向用例正确拒绝算用例通过，"
        "不表示工具执行或真实业务成功。未执行的真实用例不计入通过率。",
        "",
        "```json",
        json.dumps(metrics, ensure_ascii=False, indent=2),
        "```",
        "",
        "| Case | Mode | Outcome | Actual | Mismatches / reason |",
        "|---|---|---|---|---|",
    ]
    for result in report["results"]:
        actual = result["actual"]["status"] if result["actual"] else "not_executed"
        details = ", ".join(result["mismatches"]) or result.get("error_type") or "—"
        lines.append(
            f"| {result['case_id']} | {result['execution_mode']} | {result['outcome']} | "
            f"{actual} | {details} |"
        )
    lines += [
        "",
        "## Benchmark",
        "",
        "```json",
        json.dumps(report.get("benchmarks"), ensure_ascii=False, indent=2),
        "```",
        "",
        "三个本地协议/框架样本不能证明真实性能优势。真实 LLM/RAG/PDF 指标为 unavailable，"
        "TEST PDF 的页码回查不能代替真实设备资料验收。",
        "",
        "## 失败与限制",
        "",
        "历史 Phase 2 线程期限、输出配置与原生协议历史问题，"
        "以及 Phase 3 严格预算/超时覆盖缺口继续保留；"
        "本轮只测明确列出的场景，不把通过率推广成任意输入保证。",
        "真实模型/RAG 前提未满足时保持 BLOCKED；旧 RAG 工程不启动、不修改。",
        "",
        "完整安全关键结论以 hard_gate_passed 和三项独立计数为准，不能用总成功率覆盖。",
        "工具成功率是实际调用执行未失败的比例，不表示检索已经取得充分SOC证据。",
        "candidate_pdf_verification包含故意错误页码的负向样例，低值不代表系统接受了错误引用；"
        "真实PDF引用指标单独记录，无真实样本时为null。",
    ]
    return "\n".join(lines) + "\n"


def write_report(report, directory, *, baseline_root=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    text = markdown(report)
    for name, value in (("results.json", payload), ("report.md", text)):
        with (directory / name).open("x", encoding="utf-8") as stream:
            stream.write(value)
    if baseline_root is not None:
        targets = [
            Path(baseline_root) / "phase08_results.json",
            Path(baseline_root) / "phase08_baseline.md",
        ]
        if any(path.exists() for path in targets):
            raise FileExistsError("baseline exists; keep history and choose a new snapshot")
        for path, value in zip(targets, (payload, text), strict=True):
            with path.open("x", encoding="utf-8") as stream:
                stream.write(value)
