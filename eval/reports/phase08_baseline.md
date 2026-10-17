# Phase 8 Evaluation Baseline

UTC: 2026-10-17T09:32:44.297605+00:00

本报告为本地可复现实验；脚本模型、HTTP Mock、TEST PDF 与真实 MCP stdio 分开标记。

Commit: `e82f69a26fabdd80b95a8de3eca66aef3b44713d`；工作区状态见配套 JSON。

用例 48；实际执行 44；PASS 44；FAIL 0；TIMEOUT 0；ENV_ERROR 0；BLOCKED 4；SKIPPED 0。

成功率分母为 PASS+FAIL+TIMEOUT+ENV_ERROR；负向用例正确拒绝算用例通过，不表示工具执行或真实业务成功。未执行的真实用例不计入通过率。

```json
{
  "task": {
    "total": 48,
    "executed": 44,
    "pass": 44,
    "fail": 0,
    "timeout": 0,
    "env_error": 0,
    "skipped": 0,
    "blocked": 4,
    "success_rate": {
      "numerator": 44,
      "denominator": 44,
      "value": 1.0
    },
    "denominator_note": "PASS+FAIL+TIMEOUT+ENV_ERROR; BLOCKED/SKIPPED excluded"
  },
  "tools": {
    "requested": 24,
    "executed": 18,
    "succeeded": 16,
    "failed": 2,
    "unauthorized": 3,
    "validation_failed": 2,
    "success_rate": {
      "numerator": 16,
      "denominator": 18,
      "value": 0.8888888888888888
    },
    "mean_executed_per_attempted_case": 0.4090909090909091
  },
  "decision": {
    "accuracy": {
      "numerator": 18,
      "denominator": 18,
      "value": 1.0
    },
    "false_fc": 0,
    "false_nc": 0,
    "conflict_accuracy": {
      "numerator": 2,
      "denominator": 2,
      "value": 1.0
    },
    "composite_errors": 0
  },
  "citation": {
    "accepted_source_accuracy": {
      "numerator": 6,
      "denominator": 6,
      "value": 1.0
    },
    "accepted_membership_accuracy": {
      "numerator": 6,
      "denominator": 6,
      "value": 1.0
    },
    "candidate_pdf_verification": {
      "numerator": 1,
      "denominator": 2,
      "value": 0.5
    },
    "real_pdf_accuracy": {
      "numerator": 0,
      "denominator": 0,
      "value": null
    },
    "rejected_forged_attempts": 1
  },
  "efficiency": {
    "model_calls": 33,
    "retrieval_calls": 8,
    "total_latency_ms": 11357.344,
    "mean_latency_ms": 258.1214500400661,
    "model_latency_ms": 2.9569999999999994,
    "tool_latency_ms": 155.761,
    "latency_coverage_cases": {
      "model": 15,
      "tool": 17
    },
    "token_usage": null,
    "token_usage_status": "unavailable",
    "token_usage_measured_cases": 0,
    "estimated_cost": null,
    "cost_status": "unavailable_no_verified_price"
  },
  "safety": {
    "unauthorized_writes": 0,
    "unsupported_fc": 0,
    "accepted_forged_citations": 0
  },
  "hard_gate_passed": true,
  "real_model_quality_threshold": "not_set; measure baseline first",
  "by_execution_mode": {
    "mcp_memory": {
      "PASS": 1
    },
    "mcp_stdio": {
      "PASS": 4
    },
    "offline_mock": {
      "PASS": 39
    },
    "real_llm": {
      "BLOCKED": 3
    },
    "real_rag": {
      "BLOCKED": 1
    }
  }
}
```

| Case | Mode | Outcome | Actual | Mismatches / reason |
|---|---|---|---|---|
| tool-single | offline_mock | PASS | completed | — |
| tool-multi | offline_mock | PASS | completed | — |
| tool-parallel | offline_mock | PASS | completed | — |
| tool-greeting | offline_mock | PASS | completed | — |
| tool-unknown | offline_mock | PASS | tool_error | — |
| tool-invalid | offline_mock | PASS | tool_error | — |
| tool-budget | offline_mock | PASS | budget_exceeded | — |
| tool-retry | offline_mock | PASS | completed | — |
| compliance-fully-satisfied | offline_mock | PASS | FC | — |
| compliance-insufficient-count | offline_mock | PASS | NC | — |
| compliance-optional-module-unconfirmed | offline_mock | PASS | PENDING | — |
| compliance-missing-evidence | offline_mock | PASS | PENDING | — |
| compliance-conflicting-evidence | offline_mock | PASS | PENDING | — |
| compliance-partial | offline_mock | PASS | PC | — |
| compliance-critical-unknown | offline_mock | PASS | PENDING | — |
| compliance-unit-conversion | offline_mock | PASS | FC | — |
| compliance-unit-insufficient | offline_mock | PASS | NC | — |
| compliance-bad-unit | offline_mock | PASS | PENDING | — |
| compliance-tool-failure | offline_mock | PASS | ERROR | — |
| review-pending | offline_mock | PASS | awaiting_review | — |
| review-approve | offline_mock | PASS | completed | — |
| review-reject | offline_mock | PASS | rejected | — |
| review-modify | offline_mock | PASS | awaiting_review | — |
| review-stale | offline_mock | PASS | rejected_stale | — |
| review-repeat-resume | offline_mock | PASS | completed | — |
| review-repeat-approve | offline_mock | PASS | completed | — |
| review-checkpoint | offline_mock | PASS | awaiting_review | — |
| review-idempotent-crash | offline_mock | PASS | completed | — |
| review-path-traversal | offline_mock | PASS | rejected | — |
| review-overwrite | offline_mock | PASS | rejected | — |
| rag-single | offline_mock | PASS | completed | — |
| rag-supplement | offline_mock | PASS | completed | — |
| rag-empty | offline_mock | PASS | PENDING | — |
| rag-conflict | offline_mock | PASS | completed | — |
| rag-service-error | offline_mock | PASS | failed | — |
| rag-forged | offline_mock | PASS | failed | — |
| rag-injection | offline_mock | PASS | completed | — |
| rag-pdf-valid | offline_mock | PASS | FC | — |
| rag-page-mismatch | offline_mock | PASS | PENDING | — |
| mcp-normal | mcp_stdio | PASS | completed | — |
| mcp-unauthorized | mcp_stdio | PASS | unauthorized_tool | — |
| mcp-invalid | mcp_stdio | PASS | invalid_arguments | — |
| mcp-unavailable | mcp_stdio | PASS | connection_failed | — |
| mcp-untrusted | mcp_memory | PASS | invalid_response | — |
| tool-live-1 | real_llm | BLOCKED | not_executed | model_credentials_missing |
| tool-live-2 | real_llm | BLOCKED | not_executed | model_credentials_missing |
| tool-live-3 | real_llm | BLOCKED | not_executed | model_credentials_missing |
| rag-live-pdf | real_rag | BLOCKED | not_executed | safe_service_and_pdf_configuration_missing |

## Benchmark

```json
{
  "native_vs_langchain": {
    "mode": "scripted_framework_overhead",
    "samples": [
      {
        "sample": 0,
        "native_ms": 3.178299870342016,
        "langchain_ms": 19.6301001124084,
        "result": 52,
        "native_status": "completed",
        "langchain_status": "completed"
      },
      {
        "sample": 1,
        "native_ms": 1.2868000194430351,
        "langchain_ms": 13.472400140017271,
        "result": 52,
        "native_status": "completed",
        "langchain_status": "completed"
      },
      {
        "sample": 2,
        "native_ms": 1.9187000580132008,
        "langchain_ms": 16.228399705141783,
        "result": 52,
        "native_status": "completed",
        "langchain_status": "completed"
      }
    ]
  },
  "fixed_vs_agentic": {
    "verification_mode": "offline_mock",
    "rows": [
      {
        "case_id": "greeting",
        "baseline_status": "empty",
        "baseline_calls": 1,
        "agent_status": "completed",
        "agent_calls": 0,
        "elapsed_ms": 0.0,
        "token_usage": {
          "input_tokens": 0,
          "output_tokens": 0,
          "total_tokens": 0,
          "available": false
        }
      },
      {
        "case_id": "single",
        "baseline_status": "ok",
        "baseline_calls": 1,
        "agent_status": "completed",
        "agent_calls": 1,
        "elapsed_ms": 0.0,
        "token_usage": {
          "input_tokens": 0,
          "output_tokens": 0,
          "total_tokens": 0,
          "available": false
        }
      },
      {
        "case_id": "supplement",
        "baseline_status": "empty",
        "baseline_calls": 1,
        "agent_status": "completed",
        "agent_calls": 2,
        "elapsed_ms": 16.0,
        "token_usage": {
          "input_tokens": 0,
          "output_tokens": 0,
          "total_tokens": 0,
          "available": false
        }
      },
      {
        "case_id": "empty",
        "baseline_status": "empty",
        "baseline_calls": 1,
        "agent_status": "PENDING",
        "agent_calls": 1,
        "elapsed_ms": 16.0,
        "token_usage": {
          "input_tokens": 0,
          "output_tokens": 0,
          "total_tokens": 0,
          "available": false
        }
      },
      {
        "case_id": "conflict",
        "baseline_status": "ok",
        "baseline_calls": 1,
        "agent_status": "completed",
        "agent_calls": 1,
        "elapsed_ms": 15.0,
        "token_usage": {
          "input_tokens": 0,
          "output_tokens": 0,
          "total_tokens": 0,
          "available": false
        }
      },
      {
        "case_id": "service_error",
        "baseline_status": "failed",
        "baseline_calls": 1,
        "agent_status": "failed",
        "agent_calls": 1,
        "elapsed_ms": 16.0,
        "token_usage": {
          "input_tokens": 0,
          "output_tokens": 0,
          "total_tokens": 0,
          "available": false
        }
      }
    ],
    "real_document_success_rate": null,
    "real_pdf_citation_accuracy": null,
    "real_benchmark_status": "BLOCKED",
    "conclusion": "Script fixtures validate control flow; they cannot establish real Agentic RAG superiority."
  },
  "python_vs_mcp": {
    "startup_ms": 1194.2950999364257,
    "samples": [
      {
        "sample": 0,
        "python_tool_ms": 0.7889997214078903,
        "mcp_tool_ms": 4.604399669915438
      },
      {
        "sample": 1,
        "python_tool_ms": 0.8506998419761658,
        "mcp_tool_ms": 2.946799620985985
      },
      {
        "sample": 2,
        "python_tool_ms": 0.31640008091926575,
        "mcp_tool_ms": 2.0885001868009567
      }
    ],
    "python_mean_ms": 0.652033214767774,
    "mcp_mean_ms": 3.2132331592341266
  },
  "limits": "3 local samples, sequential warm calls, MCP startup separate; no real LLM. Different framework prompt/protocol shapes; cannot rank model quality or general performance."
}
```

三个本地协议/框架样本不能证明真实性能优势。真实 LLM/RAG/PDF 指标为 unavailable，TEST PDF 的页码回查不能代替真实设备资料验收。

## 失败与限制

历史 Phase 2 线程期限、输出配置与原生协议历史问题，以及 Phase 3 严格预算/超时覆盖缺口继续保留；本轮只测明确列出的场景，不把通过率推广成任意输入保证。
真实模型/RAG 前提未满足时保持 BLOCKED；旧 RAG 工程不启动、不修改。

完整安全关键结论以 hard_gate_passed 和三项独立计数为准，不能用总成功率覆盖。
工具成功率是实际调用执行未失败的比例，不表示检索已经取得充分SOC证据。
candidate_pdf_verification包含故意错误页码的负向样例，低值不代表系统接受了错误引用；真实PDF引用指标单独记录，无真实样本时为null。
