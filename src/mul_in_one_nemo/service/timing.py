"""Performance timing utilities for LLM response speed analysis.

This module provides decorators and context managers for measuring and logging
the execution time of various stages in the LLM response pipeline.

Usage:
    # Environment variable to enable timing
    export MIO_ENABLE_TIMING=1
    
    # In code:
    from mul_in_one_nemo.service.timing import timed, async_timed, TimingContext
    
    @async_timed("llm_call")
    async def call_llm():
        ...
    
    async with TimingContext("rag_retrieval") as tc:
        docs = await retriever.invoke(query)
        tc.add_metric("doc_count", len(docs))
"""

import asyncio
import functools
import logging
import os
import time
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Global flag to enable/disable timing (controlled by environment variable)
TIMING_ENABLED = os.environ.get("MIO_ENABLE_TIMING", "").lower() in ("1", "true", "yes")


@dataclass
class TimingRecord:
    """Record of a single timing measurement."""
    name: str
    duration_ms: float
    start_time: float
    end_time: float
    metrics: Dict[str, Any] = field(default_factory=dict)
    parent: Optional[str] = None


class _DummyContext:
    """Dummy context used when timing is disabled."""
    def add_metric(self, key: str, value: Any) -> None:
        pass


class _MetricsContext:
    """Context object for adding custom metrics during timing."""
    def __init__(self) -> None:
        self.metrics: Dict[str, Any] = {}
    
    def add_metric(self, key: str, value: Any) -> None:
        self.metrics[key] = value


class TimingRegistry:
    """Registry for collecting and reporting timing measurements.
    
    This is a singleton that collects timing data across the application.
    """
    
    _instance: Optional["TimingRegistry"] = None
    
    def __new__(cls) -> "TimingRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._records: List[TimingRecord] = []
            cls._instance._current_context: Optional[str] = None
        return cls._instance
    
    def record(self, record: TimingRecord) -> None:
        """Add a timing record."""
        self._records.append(record)
        
        # Log the timing
        metrics_str = ", ".join(f"{k}={v}" for k, v in record.metrics.items())
        parent_str = f" (parent: {record.parent})" if record.parent else ""
        logger.info(
            f"⏱️ TIMING [{record.name}]{parent_str}: {record.duration_ms:.2f}ms"
            + (f" | {metrics_str}" if metrics_str else "")
        )
    
    def get_records(self) -> List[TimingRecord]:
        """Get all timing records."""
        return self._records.copy()
    
    def clear(self) -> None:
        """Clear all records."""
        self._records.clear()
    
    def summary(self) -> Dict[str, Dict[str, float]]:
        """Generate a summary of timing statistics by name.
        
        Returns:
            Dict mapping name to stats (count, total_ms, avg_ms, min_ms, max_ms)
        """
        from collections import defaultdict
        
        stats: Dict[str, List[float]] = defaultdict(list)
        for r in self._records:
            stats[r.name].append(r.duration_ms)
        
        result = {}
        for name, durations in stats.items():
            result[name] = {
                "count": len(durations),
                "total_ms": sum(durations),
                "avg_ms": sum(durations) / len(durations),
                "min_ms": min(durations),
                "max_ms": max(durations),
            }
        return result


# Global registry instance
_registry = TimingRegistry()


@asynccontextmanager
async def TimingContext(name: str, parent: Optional[str] = None):
    """Async context manager for timing a block of code.
    
    Args:
        name: Name of the operation being timed
        parent: Optional parent operation name for hierarchical timing
    
    Yields:
        A context object with add_metric() method for adding custom metrics
    
    Example:
        async with TimingContext("llm_call") as ctx:
            result = await llm.invoke(prompt)
            ctx.add_metric("input_tokens", count_tokens(prompt))
            ctx.add_metric("output_tokens", count_tokens(result))
    """
    if not TIMING_ENABLED:
        yield _DummyContext()
        return
    
    ctx = _MetricsContext()
    start = time.perf_counter()
    try:
        yield ctx
    finally:
        end = time.perf_counter()
        duration_ms = (end - start) * 1000
        record = TimingRecord(
            name=name,
            duration_ms=duration_ms,
            start_time=start,
            end_time=end,
            metrics=ctx.metrics,
            parent=parent,
        )
        _registry.record(record)


@contextmanager
def sync_timing_context(name: str, parent: Optional[str] = None):
    """Sync context manager for timing a block of code.
    
    Same as TimingContext but for synchronous code.
    """
    if not TIMING_ENABLED:
        yield _DummyContext()
        return
    
    ctx = _MetricsContext()
    start = time.perf_counter()
    try:
        yield ctx
    finally:
        end = time.perf_counter()
        duration_ms = (end - start) * 1000
        record = TimingRecord(
            name=name,
            duration_ms=duration_ms,
            start_time=start,
            end_time=end,
            metrics=ctx.metrics,
            parent=parent,
        )
        _registry.record(record)


def async_timed(name: str, parent: Optional[str] = None):
    """Decorator for timing async functions.
    
    Args:
        name: Name of the operation being timed
        parent: Optional parent operation name
    
    Example:
        @async_timed("database_query")
        async def fetch_records():
            ...
    """
    def decorator(func: Callable) -> Callable:
        if not TIMING_ENABLED:
            return func
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                end = time.perf_counter()
                duration_ms = (end - start) * 1000
                record = TimingRecord(
                    name=name,
                    duration_ms=duration_ms,
                    start_time=start,
                    end_time=end,
                    parent=parent,
                )
                _registry.record(record)
        
        return wrapper
    return decorator


def timed(name: str, parent: Optional[str] = None):
    """Decorator for timing sync functions.
    
    Args:
        name: Name of the operation being timed
        parent: Optional parent operation name
    
    Example:
        @timed("compute_score")
        def calculate():
            ...
    """
    def decorator(func: Callable) -> Callable:
        if not TIMING_ENABLED:
            return func
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                end = time.perf_counter()
                duration_ms = (end - start) * 1000
                record = TimingRecord(
                    name=name,
                    duration_ms=duration_ms,
                    start_time=start,
                    end_time=end,
                    parent=parent,
                )
                _registry.record(record)
        
        return wrapper
    return decorator


def get_timing_registry() -> TimingRegistry:
    """Get the global timing registry."""
    return _registry


def log_timing_summary() -> None:
    """Log a summary of all collected timings."""
    if not TIMING_ENABLED:
        logger.debug("Timing is disabled. Set MIO_ENABLE_TIMING=1 to enable.")
        return
    
    summary = _registry.summary()
    if not summary:
        logger.info("No timing data collected.")
        return
    
    logger.info("=" * 60)
    logger.info("⏱️ TIMING SUMMARY")
    logger.info("=" * 60)
    
    # Sort by total time descending
    sorted_stats = sorted(summary.items(), key=lambda x: x[1]["total_ms"], reverse=True)
    
    for name, stats in sorted_stats:
        logger.info(
            f"  {name}: count={stats['count']}, "
            f"total={stats['total_ms']:.2f}ms, "
            f"avg={stats['avg_ms']:.2f}ms, "
            f"min={stats['min_ms']:.2f}ms, "
            f"max={stats['max_ms']:.2f}ms"
        )
    
    logger.info("=" * 60)


# Predefined timing names for consistency
class TimingNames:
    """Predefined timing names for common operations."""
    
    # Session layer
    MESSAGE_ENQUEUE = "message_enqueue"
    MESSAGE_PERSIST = "message_persist"
    HISTORY_LOAD = "history_load"
    
    # Runtime layer
    RUNTIME_INIT = "runtime_init"
    PERSONA_LOAD = "persona_load"
    SCHEDULER_DECISION = "scheduler_decision"
    
    # Persona function layer
    PROMPT_BUILD = "prompt_build"
    LLM_CALL = "llm_call"
    LLM_TTFT = "llm_ttft"  # Time to first token
    
    # Tool layer
    RAG_QUERY = "rag_query"
    RAG_EMBED = "rag_embed"
    RAG_SEARCH = "rag_search"
    WEB_SEARCH = "web_search"
    WEB_FETCH = "web_fetch"
    
    # Database layer
    DB_QUERY = "db_query"
    DB_INSERT = "db_insert"
