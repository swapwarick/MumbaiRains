"""
simulation/forcing/reports.py
-----------------------------
Water budget and mass conservation reports.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any

@dataclass
class WaterBudgetReport:
    timestep: int
    initial_water: float      # m^3
    water_added: float        # m^3
    boundary_loss: float      # m^3
    current_storage: float     # m^3
    residual_error: float     # m^3
    relative_error: float     # fraction
    max_depth: float          # m
    min_depth: float          # m

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
