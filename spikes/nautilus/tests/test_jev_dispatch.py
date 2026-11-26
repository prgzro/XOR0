"""Jev calls leave the event thread in live mode; verdicts come back on it."""

import threading

from spike.jev import JevDispatcher, Verdict


class FixedJev:
    def __init__(self, verdict):
        self.verdict = verdict
        self.threads = []

    def decide(self, request):
        self.threads.append(threading.get_ident())
        return self.verdict


def test_inline_mode_delivers_the_verdict_during_submit():
    got = []
    dispatcher = JevDispatcher(FixedJev(Verdict(True, "ok")), mode="inline")
    dispatcher.submit({"candidate": 1}, got.append)
    assert got == [Verdict(True, "ok")]


def test_threaded_mode_calls_jev_off_thread_and_delivers_only_on_drain():
    got = []
    jev = FixedJev(Verdict(False, "low quality"))
    dispatcher = JevDispatcher(jev, mode="threaded")
    dispatcher.submit({"candidate": 1}, lambda v: got.append((v, threading.get_ident())))
    dispatcher.wait_idle(timeout=5)

    assert got == []  # nothing delivered behind the event thread's back
    assert dispatcher.drain() == 1
    assert got == [(Verdict(False, "low quality"), threading.get_ident())]
    assert jev.threads and jev.threads[0] != threading.get_ident()
    dispatcher.close()


class BrokenJev:
    def decide(self, request):
        raise TimeoutError("jev deadline 5s")


def test_a_failing_jev_call_becomes_a_reject_in_both_modes():
    for mode in ("inline", "threaded"):
        got = []
        dispatcher = JevDispatcher(BrokenJev(), mode=mode)
        dispatcher.submit({"candidate": 1}, got.append)
        dispatcher.wait_idle(timeout=5)
        dispatcher.drain()
        dispatcher.close()
        assert len(got) == 1, mode
        assert got[0].approved is False
        assert "TimeoutError" in got[0].reason
