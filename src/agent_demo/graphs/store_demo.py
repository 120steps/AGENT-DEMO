"""Small cross-thread store experiment with explicit caller namespace grants."""

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.store.memory import InMemoryStore
from typing_extensions import TypedDict


class MemoryState(TypedDict, total=False):
    note: str


def namespace_access(store, namespace, grants, *, value=None):
    if namespace not in grants:
        raise PermissionError("namespace not granted by caller")
    if value is not None:
        store.put(namespace, "mock-note", value)
    item = store.get(namespace, "mock-note")
    return item.value if item else None


def run_store_demo():
    saver = InMemorySaver()
    store = InMemoryStore()
    builder = StateGraph(MemoryState)
    builder.add_node("keep", lambda state: {"note": state.get("note", "empty")})
    builder.add_edge(START, "keep")
    builder.add_edge("keep", END)
    graph = builder.compile(checkpointer=saver, store=store)
    a = {"configurable": {"thread_id": "A"}}
    b = {"configurable": {"thread_id": "B"}}
    graph.invoke({"note": "MOCK note from A"}, a)
    graph.invoke({}, a)
    own = graph.get_state(a).values["note"]
    isolated = not graph.get_state(b).values
    namespace = ("demo-project", "shared-mock")
    grants = {namespace}  # Trusted application grants, NOT derived from thread_id.
    namespace_access(store, namespace, grants, value={"source_type": "mock", "note": own})
    shared = namespace_access(store, namespace, grants)
    denied = False
    try:
        namespace_access(store, namespace, set())
    except PermissionError:
        denied = True
    fresh = builder.compile(checkpointer=InMemorySaver())
    return {
        "thread_a_note": own,
        "thread_b_isolated": isolated,
        "authorized_thread_b_store": shared,
        "unauthorized_denied": denied,
        "fresh_saver_has_no_state": not fresh.get_state(a).values,
    }
