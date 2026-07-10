"""
simulation/network package
--------------------------
Hydraulic Network connectivity and topology engine.
"""

from .types import NodeType, EdgeType, NetworkNode, NetworkEdge, NetworkReport
from .engine import HydraulicNetworkEngine
from .benchmarks import create_network_benchmark

__all__ = [
    "NodeType",
    "EdgeType",
    "NetworkNode",
    "NetworkEdge",
    "NetworkReport",
    "HydraulicNetworkEngine",
    "create_network_benchmark",
]
