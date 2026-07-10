"""
simulation/hydraulic/engine.py
------------------------------
Primary entry points and interfaces for Hydraulic Routing Engine (Sprint 6).
"""

from .routing import HydraulicRoutingEngine, KinematicRoutingStrategy, RoutingStrategy
from .pipe import Pipe
from .junction import Junction
from .state import HydraulicState, OverflowEvent, DischargeRequest
from .reports import HydraulicReport

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
]
