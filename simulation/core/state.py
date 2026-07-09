"""
simulation/core/state.py
------------------------
SimulationState stores the global state of the simulation at the current timestep.
This makes the simulation deterministic, trackable, and easy to export/checkpoint.
"""

from datetime import datetime
from typing import Dict, Any, Optional
import numpy as np


class SimulationState:
    """
    Holds the complete state of a simulation run at any point in time.
    Encapsulates all dynamic grids and variables to avoid global states.
    """
    def __init__(
        self,
        rows: int,
        cols: int,
        scenario_name: str = "default",
        start_time: Optional[datetime] = None
    ) -> None:
        """
        Initializes a clean simulation state.

        Args:
            rows: Number of grid rows.
            cols: Number of grid columns.
            scenario_name: Name of the active simulation scenario.
            start_time: Clock start time. Defaults to now.
        """
        self.current_timestep: int = 0
        self.current_simulation_time: datetime = start_time or datetime.now()
        self.current_rainfall: float = 0.0  # Current rain rate (mm/hr or mm per step)
        self.current_tide: float = 0.0      # Current sea level (m)
        self.status: str = "ready"          # ready, running, paused, completed, error
        self.scenario: str = scenario_name

        # Dynamic grids (NumPy arrays for high-performance vectorized operations)
        self.water_depth_grid: np.ndarray = np.zeros((rows, cols), dtype=np.float32)
        self.velocity_x_grid: np.ndarray = np.zeros((rows, cols), dtype=np.float32)
        self.velocity_y_grid: np.ndarray = np.zeros((rows, cols), dtype=np.float32)
        self.infiltration_grid: np.ndarray = np.zeros((rows, cols), dtype=np.float32)
        self.flow_direction_grid: np.ndarray = np.zeros((rows, cols), dtype=np.float32)
        self.flood_flag_grid: np.ndarray = np.zeros((rows, cols), dtype=bool)

    def reset(self) -> None:
        """Resets all dynamic values to initial dry conditions."""
        self.current_timestep = 0
        self.current_rainfall = 0.0
        self.current_tide = 0.0
        self.status = "ready"
        
        self.water_depth_grid.fill(0.0)
        self.velocity_x_grid.fill(0.0)
        self.velocity_y_grid.fill(0.0)
        self.infiltration_grid.fill(0.0)
        self.flow_direction_grid.fill(0.0)
        self.flood_flag_grid.fill(False)

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the current state summary into a serializable dictionary.
        Excludes full raw grids to keep payloads lightweight.
        """
        return {
            "current_timestep": self.current_timestep,
            "simulation_time": self.current_simulation_time.isoformat(),
            "rainfall_rate_mm_hr": self.current_rainfall,
            "tide_level_m": self.current_tide,
            "status": self.status,
            "scenario": self.scenario,
            "max_water_depth": float(self.water_depth_grid.max()),
            "mean_water_depth": float(self.water_depth_grid.mean()),
            "flooded_area_pct": float(np.sum(self.flood_flag_grid) / self.flood_flag_grid.size * 100.0)
        }
