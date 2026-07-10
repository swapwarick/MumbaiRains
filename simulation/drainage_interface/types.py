"""
simulation/drainage_interface/types.py
--------------------------------------
Type definitions and data models for drainage inlets.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any

@dataclass
class DrainInlet:
    """
    Represents a physical storm water drain inlet on the surface.
    Connects the surface flow grid to a node in the sub-surface hydraulic network.
    """
    id: str
    row: int
    col: int
    elevation: float
    capacity_m3_s: float
    invert_level: float
    blocked: bool = False
    connected_node_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
