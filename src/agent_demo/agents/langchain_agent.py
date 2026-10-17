"""LangChain 1.x create_agent adapter; business rules stay in Phase 1 tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event, Lock
from time import perf_counter
from typing import Annotated

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain.tools import tool
from langchain_core.messages import ToolMessage
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StrictStr

from agent_demo.agents.agent_loop import LoopLimits
from agent_demo.agents.execution import wait_until
from agent_demo.tools import dispatch, finite_number, validate_arguments


class AgentAnswer(BaseModel):
    model: str = Field(description="The simulated model identifier")
    conclusion: str = Field(description="A concise evidence-based conclusion")
    total_ports: int | None = Field(default=None, description="Computed total port count")


class AddArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    a: Annotated[float, BeforeValidator(finite_number)]
    b: Annotated[float, BeforeValidator(finite_number)]


class LookupArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: StrictStr = Field(pattern=r"^MOCK-SW-[0-9]{1,3}$")


@tool(args_schema=AddArguments)
def add_tool(a: float, b: float) -> float:
    """Add two finite numbers using the application dispatcher."""
    output = dispatch("add", {"a": a, "b": b})
    if output["status"] == "error":
        raise ValueError(output["error_type"])
    return output["result"]


@tool(args_schema=LookupArguments)
def lookup_product_spec_tool(model: str) -> dict:
    """Look up explicitly simulated MOCK switch specifications."""
    output = dispatch("lookup_product_spec", {"model": model})
    if output["status"] == "error":
        raise ValueError(output["error_type"])
    return output["result"]


TOOLS = [add_tool, lookup_product_spec_tool]


@dataclass
class LangChainResult:
    status: str
    answer: AgentAnswer | None
    state: dict
    elapsed_ms: float
    error_type: str | None = None
    usage: dict = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)


class AgentStop(RuntimeError):
    def __init__(self, status, reason):
        self.status, self.reason = status, reason
        super().__init__(reason)


class ExecutionGuard(AgentMiddleware):
    """Exact call counters are independent of the graph recursion safety guard."""

    def __init__(self, limits):
        self.limits = limits
        self.deadline = perf_counter() + limits.task_timeout
        self.model_calls = self.tool_calls = 0
        self.lock = Lock()
        self.stopped = Event()
        self.events = []
        self.usage = {
            "total_tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "available": False,
            "estimated_cost": None,
            "price_source": None,
        }

    def check(self):
        if self.stopped.is_set() or perf_counter() >= self.deadline:
            raise AgentStop("timeout", "task_timeout")

    def wrap_model_call(self, request, handler):
        for retry in range(self.limits.max_retries + 1):
            self.check()
            if self.model_calls >= self.limits.max_model_rounds:
                raise AgentStop("budget_exceeded", "max_model_rounds")
            if self.usage["total_tokens"] >= self.limits.max_total_tokens:
                raise AgentStop("budget_exceeded", "max_total_tokens")
            self.model_calls += 1
            started = perf_counter()
            settings = {
                **request.model_settings,
                "max_output_tokens": min(
                    self.limits.max_output_tokens,
                    self.limits.max_total_tokens - self.usage["total_tokens"],
                ),
                "max_retries": 0,
                "timeout": max(0.001, self.deadline - started),
            }
            self.events.append(
                {
                    "event": "MODEL_REQUEST",
                    "model_round": self.model_calls,
                    "retry": retry,
                    "estimated_cost": None,
                }
            )
            try:
                response = wait_until(
                    lambda: handler(request.override(model_settings=settings)), self.deadline
                )
            except TimeoutError:
                self.stopped.set()
                raise AgentStop("timeout", "model_wait_timeout") from None
            except ConnectionError:
                if retry == self.limits.max_retries:
                    raise
                continue
            self.check()
            for message in response.result:
                incoming = getattr(message, "usage_metadata", None)
                if incoming:
                    self.usage["available"] = True
                    for key in ("input_tokens", "output_tokens", "total_tokens"):
                        value = incoming.get(key, 0)
                        if type(value) is int and value >= 0:
                            self.usage[key] += value
            self.events.append(
                {
                    "event": "MODEL_RESPONSE",
                    "model_round": self.model_calls,
                    "elapsed_ms": _elapsed(started),
                    "usage": dict(self.usage),
                }
            )
            if self.usage["total_tokens"] >= self.limits.max_total_tokens:
                raise AgentStop("budget_exceeded", "max_total_tokens")
            return response

    def wrap_tool_call(self, request, handler):
        with self.lock:
            self.check()
            if self.tool_calls >= self.limits.max_tool_calls:
                raise AgentStop("budget_exceeded", "max_tool_calls")
            self.tool_calls += 1
            call = request.tool_call
            name = call["name"]
            mapping = {"add_tool": "add", "lookup_product_spec_tool": "lookup_product_spec"}
            started = perf_counter()
            error = None
            if name not in mapping:
                error = "unknown_tool"
            else:
                try:
                    validate_arguments(mapping[name], call["args"])
                except (ValueError, TypeError):
                    error = "invalid_arguments"
            if error is None:
                try:
                    result = wait_until(
                        lambda: handler(request),
                        min(self.deadline, started + self.limits.tool_timeout),
                    )
                    self.check()
                    self.events.append(
                        {
                            "event": "TOOL_RESULT",
                            "tool_call_id": call["id"],
                            "tool_name": name,
                            "elapsed_ms": _elapsed(started),
                            "status": "returned",
                        }
                    )
                    return result
                except TimeoutError:
                    self.stopped.set()
                    raise AgentStop("timeout", "tool_wait_timeout") from None
                except AgentStop:
                    raise
                except Exception:
                    error = "tool_execution_failed"
            self.events.append(
                {
                    "event": "TOOL_RESULT",
                    "tool_call_id": call["id"],
                    "tool_name": name,
                    "status": "error",
                    "error_type": error,
                }
            )
            return ToolMessage(
                content='{"status":"error","error_type":"' + error + '"}',
                tool_call_id=call["id"],
                name=name,
                status="error",
            )


def build_agent(model, *, max_model_rounds: int = 8, response_format=AgentAnswer, guard=None):
    """Build the official LangChain 1.x graph; recursion is a graph-step guard."""
    if max_model_rounds < 1:
        raise ValueError("max_model_rounds must be positive")
    return create_agent(
        model=model,
        tools=TOOLS,
        middleware=[guard or ExecutionGuard(LoopLimits(max_model_rounds=max_model_rounds))],
        system_prompt=(
            "Use the provided tools for MOCK switch data and arithmetic. "
            "MOCK data is simulated. Return the requested structured answer."
        ),
        response_format=response_format,
    ), max_model_rounds


def run_langchain_agent(
    model,
    prompt: str,
    *,
    max_model_rounds: int = 8,
    timeout: float = 30.0,
    max_tool_calls: int = 12,
    tool_timeout: float = 2.0,
    max_retries: int = 1,
    max_output_tokens: int = 2048,
    max_total_tokens: int = 16000,
):
    started = perf_counter()
    limits = LoopLimits(
        max_model_rounds=max_model_rounds,
        max_tool_calls=max_tool_calls,
        task_timeout=timeout,
        tool_timeout=tool_timeout,
        max_retries=max_retries,
        max_output_tokens=max_output_tokens,
        max_total_tokens=max_total_tokens,
    )
    guard = ExecutionGuard(limits)
    try:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("invalid prompt")
        agent, rounds = build_agent(model, max_model_rounds=max_model_rounds, guard=guard)
        state = agent.invoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config={"recursion_limit": rounds * 2 + 1},
        )
        parsed = state.get("structured_response")
        if not isinstance(parsed, AgentAnswer):
            return LangChainResult(
                "failed", None, state, _elapsed(started), "missing_structured_output"
            )
        return LangChainResult(
            "completed", parsed, state, _elapsed(started), usage=guard.usage, events=guard.events
        )
    except AgentStop as error:
        return LangChainResult(
            error.status, None, {}, _elapsed(started), error.reason, guard.usage, guard.events
        )
    except Exception as error:
        return LangChainResult("failed", None, {}, _elapsed(started), type(error).__name__)
    finally:
        guard.stopped.set()


def _elapsed(started):
    return round((perf_counter() - started) * 1000, 3)
