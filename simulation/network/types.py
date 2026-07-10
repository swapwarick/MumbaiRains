"""
simulation/network/types.py
---------------------------
Enums and dataclasses for the hydraulic network model.
"""

from enum import Enum
from dataclasses import dataclass, asdict
from typing import Dict, Any, List


class NodeType(Enum):
    INLET = "inlet"
    JUNCTION = "junction"
    PUMP = "pump"
    OUTFALL = "outfall"
    STORAGE = "storage"


class EdgeType(Enum):
    PIPE = "pipe"
    NULLAH = "nullah"
    RIVER = "river"


@dataclass
class NetworkNode:
    """Represents a node in the drainage network graph."""
    node_id: str
    node_type: NodeType
    x: float
    y: float
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["node_type"] = self.node_type.value
        return d


@dataclass
class NetworkEdge:
    """Represents a conduit/channel edge in the drainage network graph."""
    edge_id: str
    from_node: str
    to_node: str
    edge_type: EdgeType
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["edge_type"] = self.edge_type.value
        return d


@dataclass
class NetworkReport:
    """
    Geospatial and topological metrics for a hydraulic network.
    """
    node_count: int
    edge_count: int
    connected_components: int
    outfalls: int
    dead_ends: int
    cycles: int
    inlet_count: int
    average_inlet_spacing: float
    coverage_percentage: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
