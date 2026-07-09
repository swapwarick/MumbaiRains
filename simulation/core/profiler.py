"""
simulation/core/profiler.py
---------------------------
PerformanceProfiler — provides structured metrics tracking execution duration,
memory growth, raster reads, vector queries, CPU utilization, and tile cache hits.
"""

from dataclasses import dataclass, field
from datetime import datetime
import os
import sys
import time
from typing import Dict, Any, List, Optional

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False


@dataclass
class ProfilerReport:
    """
    Strongly typed profiling report summarizing execution performance.
    """
    execution_time_ms: float
    memory_growth_mb: float
    cpu_percent: float
    raster_reads: int
    vector_queries: int
    tile_cache_hits: int
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class PerformanceProfiler:
    """
    Stateless and stateful metrics profiling tool to drive evidence-based optimization.
    """
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Resets all metrics counters."""
        self._start_time: float = 0.0
        self._end_time: float = 0.0
        self._start_mem: float = 0.0
        self._raster_reads: int = 0
        self._vector_queries: int = 0
        self._tile_cache_hits: int = 0
        self._cpu_percent_start: float = 0.0

    def start(self) -> None:
        """Starts profiling timing, memory, and CPU."""
        self.reset()
        self._start_time = time.perf_counter()
        
        if _PSUTIL:
            try:
                process = psutil.Process(os.getpid())
                self._start_mem = process.memory_info().rss / (1024.0 * 1024.0)  # RSS in MB
                self._cpu_percent_start = process.cpu_percent(interval=None)
            except Exception:
                self._start_mem = 0.0
        else:
            self._start_mem = 0.0

    def record_raster_read(self, count: int = 1) -> None:
        """Increment count of disk raster reads."""
        self._raster_reads += count

    def record_vector_query(self, count: int = 1) -> None:
        """Increment count of spatial index/vector queries."""
        self._vector_queries += count

    def record_tile_cache_hit(self, count: int = 1) -> None:
        """Increment count of tile cache hits."""
        self._tile_cache_hits += count

    def stop(self) -> ProfilerReport:
        """Stops profiling and returns a ProfilerReport."""
        self._end_time = time.perf_counter()
        execution_ms = (self._end_time - self._start_time) * 1000.0
        
        memory_growth = 0.0
        cpu_percent = 0.0
        
        if _PSUTIL:
            try:
                process = psutil.Process(os.getpid())
                current_mem = process.memory_info().rss / (1024.0 * 1024.0)
                memory_growth = max(0.0, current_mem - self._start_mem)
                cpu_percent = process.cpu_percent(interval=None)
            except Exception:
                pass
                
        return ProfilerReport(
            execution_time_ms=execution_ms,
            memory_growth_mb=memory_growth,
            cpu_percent=cpu_percent,
            raster_reads=self._raster_reads,
            vector_queries=self._vector_queries,
            tile_cache_hits=self._tile_cache_hits
        )
