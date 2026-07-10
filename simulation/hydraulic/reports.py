"""
simulation/hydraulic/reports.py
------------------------------
Cumulative water budget reporting and accounting for the hydraulic network.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class HydraulicReport:
    """
    Cumulative and step-wise water budget metrics for mass conservation audits.
    """
    timestep: int
    initial_water_m3: float
    water_added_m3: float
    boundary_loss_m3: float
    current_storage_m3: float
    residual_error_m3: float
    relative_error: float
    
    # Cumulative balances
    cumulative_inflow_m3: float
    cumulative_outflow_m3: float
    cumulative_overflow_m3: float
    cumulative_boundary_loss_m3: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
