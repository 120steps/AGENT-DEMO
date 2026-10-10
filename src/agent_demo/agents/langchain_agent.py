"""LangChain 1.x create_agent adapter; business rules stay in Phase 1 tools."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from langchain.agents import create_agent
from langchain.tools import tool
from pydantic import BaseModel, Field

from agent_demo.tools import dispatch


class AgentAnswer(BaseModel):
    model: str = Field(description="The simulated model identifier")
    conclusion: str = Field(description="A concise evidence-based conclusion")
    total_ports: int | None = Field(default=None, description="Computed total port count")


@tool
def add_tool(a: float, b: float) -> float:
    """Add two finite numbers using the application dispatcher."""
    output = dispatch("add", {"a": a, "b": b})
    if output["status"] == "error":
        raise ValueError(output["error_type"])
    return output["result"]


@tool
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


def build_agent(model, *, max_model_rounds: int = 8, response_format=AgentAnswer):
    """Build the official LangChain 1.x graph; recursion is a graph-step guard."""
    if max_model_rounds < 1:
        raise ValueError("max_model_rounds must be positive")
    return create_agent(
        model=model,
        tools=TOOLS,
        system_prompt=(
            "Use the provided tools for MOCK switch data and arithmetic. "
            "MOCK data is simulated. Return the requested structured answer."
        ),
        response_format=response_format,
    ), max_model_rounds


def run_langchain_agent(model, prompt: str, *, max_model_rounds: int = 8, timeout: float = 30.0):
    started = perf_counter()
    try:
        agent, rounds = build_agent(model, max_model_rounds=max_model_rounds)
        state = agent.invoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config={"recursion_limit": rounds * 2 + 1},
        )
        parsed = state.get("structured_response")
        if not isinstance(parsed, AgentAnswer):
            return LangChainResult(
                "failed", None, state, _elapsed(started), "missing_structured_output"
            )
        return LangChainResult("completed", parsed, state, _elapsed(started))
    except Exception as error:
        return LangChainResult("failed", None, {}, _elapsed(started), type(error).__name__)


def _elapsed(started):
    return round((perf_counter() - started) * 1000, 3)
