"""
simulation/hydraulic package
----------------------------
Hydraulic Routing Engine and swappable routing strategies (Sprint 6).
"""

from .routing import HydraulicRoutingEngine, KinematicRoutingStrategy, RoutingStrategy
from .pipe import Pipe
from .junction import Junction
from .state import HydraulicState, OverflowEvent, DischargeRequest
from .reports import HydraulicReport
from .benchmarks import create_hydraulic_benchmark

__all__ = [
    "HydraulicRoutingEngine",
    "KinematicRoutingStrategy",
    "RoutingStrategy",
    "Pipe",
    "Junction",
    "HydraulicState",
    "OverflowEvent",
    "DischargeRequest",
    "HydraulicReport",
    "create_hydraulic_benchmark",
]
