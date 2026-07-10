"""
simulation/drainage_interface/reports.py
----------------------------------------
Reports and statistics structures for the drainage interface.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any

@dataclass
class DrainageInterfaceReport:
    """
    Statistics and intake audits for the drainage interface in a timestep.
    """
    timestep: int
    total_inlets: int
    active_inlets: int
    blocked_inlets: int
    total_capacity_m3_s: float
    total_intake_m3: float
    coverage_percentage: float  # Percent of grid cells within max search radius of an inlet
    avg_spacing_m: float        # Average distance between nearest inlets

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
