"""Bound waiting without claiming that an SDK/thread operation was cancelled."""

from contextvars import copy_context
from queue import Empty, Queue
from threading import Thread
from time import perf_counter


def wait_until(function, deadline):
    remaining = deadline - perf_counter()
    if remaining <= 0:
        raise TimeoutError("wait deadline exceeded")
    box = Queue(maxsize=1)
    context = copy_context()

    def worker():
        try:
            box.put((True, context.run(function)))
        except Exception as error:
            box.put((False, error))

    Thread(target=worker, daemon=True, name="agent-bounded-wait").start()
    try:
        ok, value = box.get(timeout=remaining)
    except Empty:
        raise TimeoutError("wait deadline exceeded; cancellation unconfirmed") from None
    if not ok:
        raise value
    if perf_counter() >= deadline:
        raise TimeoutError("late response; cancellation unconfirmed")
    return value
