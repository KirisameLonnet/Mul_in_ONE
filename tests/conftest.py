"""Pytest configuration for timeout logging and diagnostics.

Test Timestamp: 2025-11-20T17:30:00+08:00
Coverage Scope: Global timeout monitoring and traceback dumping for slow tests.
"""

from __future__ import annotations

import faulthandler
import logging
import os
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import pytest

_DEFAULT_TIMEOUT_SECONDS = float(os.getenv("PYTEST_TEST_TIMEOUT", "30"))
_LOGGER = logging.getLogger("tests.timeout")

_ROOT_DIR = Path(__file__).resolve().parents[1]
_SRC_DIR = _ROOT_DIR / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))


def pytest_addoption(parser):
    parser.addoption(
        "--test-timeout",
        action="store",
        default=str(_DEFAULT_TIMEOUT_SECONDS),
        help=(
            "Per-test timeout threshold in seconds. "
            "If a test exceeds this duration, a stack trace is dumped to stderr."
        ),
    )


@dataclass
class _TimeoutGuard:
    nodeid: str
    timeout: float
    start: float | None = None
    _timer: threading.Timer | None = None

    def start_timer(self) -> None:
        if self.timeout <= 0:
            return
        self.start = time.perf_counter()
        self._timer = threading.Timer(self.timeout, self._on_timeout)
        self._timer.daemon = True
        self._timer.start()

    def cancel(self) -> None:
        if self._timer:
            self._timer.cancel()
            self._timer = None
        if self.start is not None:
            duration = time.perf_counter() - self.start
            _LOGGER.debug("Test %s completed in %.3fs", self.nodeid, duration)

    def _on_timeout(self) -> None:
        elapsed = None if self.start is None else time.perf_counter() - self.start
        _LOGGER.error(
            "Test %s exceeded timeout %.1fs (elapsed %.3fs). Dumping stack...",
            self.nodeid,
            self.timeout,
            0.0 if elapsed is None else elapsed,
        )
        faulthandler.dump_traceback(file=sys.stderr)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    timeout_value = float(item.config.getoption("--test-timeout"))
    guard = _TimeoutGuard(nodeid=item.nodeid, timeout=timeout_value)
    guard.start_timer()
    try:
        yield
    finally:
        guard.cancel()
