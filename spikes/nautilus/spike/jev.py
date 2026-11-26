"""Jev Decision dispatch: one strategy code path for backtest and live.

v2 has no `Actor.run_in_executor` (v1 had it). This module stands in for it:
- mode="inline" (backtest): Jev is called and the verdict delivered during submit,
  so a mocked Jev keeps the run deterministic.
- mode="threaded" (live): Jev runs on a worker thread; verdicts wait in a queue
  until the strategy calls `drain()` from the event thread (a clock timer), so
  orders are only ever submitted on the event thread.
"""

import queue
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class Verdict:
    approved: bool
    reason: str


class JevClient(Protocol):
    def decide(self, request: Any) -> Verdict: ...


OnVerdict = Callable[[Verdict], None]


class JevDispatcher:
    def __init__(self, jev: JevClient, mode: str, workers: int = 2) -> None:
        if mode not in ("inline", "threaded"):
            raise ValueError(f"unknown mode {mode!r}")
        self.jev = jev
        self.mode = mode
        self._ready: queue.SimpleQueue[tuple[OnVerdict, Verdict]] = queue.SimpleQueue()
        self._pending: set[Future] = set()
        self._pool = ThreadPoolExecutor(workers, "jev") if mode == "threaded" else None

    def submit(self, request: Any, on_verdict: OnVerdict) -> None:
        if self._pool is None:
            on_verdict(self._decide(request))
            return
        future = self._pool.submit(self._decide_into_queue, request, on_verdict)
        self._pending.add(future)
        future.add_done_callback(self._pending.discard)

    def _decide_into_queue(self, request: Any, on_verdict: OnVerdict) -> None:
        self._ready.put((on_verdict, self._decide(request)))

    def _decide(self, request: Any) -> Verdict:
        try:
            return self.jev.decide(request)
        except Exception as exc:  # noqa: BLE001  fail closed: any Jev failure is a reject
            return Verdict(False, f"jev error: {type(exc).__name__}: {exc}")

    def drain(self) -> int:
        """Deliver every ready verdict on the calling (event) thread. Returns how many."""
        delivered = 0
        while True:
            try:
                on_verdict, verdict = self._ready.get_nowait()
            except queue.Empty:
                return delivered
            on_verdict(verdict)
            delivered += 1

    def wait_idle(self, timeout: float) -> None:
        wait(list(self._pending), timeout=timeout)

    def close(self) -> None:
        if self._pool is not None:
            self._pool.shutdown(wait=True, cancel_futures=True)
