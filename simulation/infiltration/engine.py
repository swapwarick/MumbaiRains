"""
simulation/infiltration/engine.py
---------------------------------
InfiltrationEngine — acts as the service wrapper for swappable infiltration models.
Simulation modules query the engine, unaware of which model is currently running.
"""

from typing import Dict, Any, Optional
import numpy as np

from backend.utils import get_logger
from simulation.infiltration.base import InfiltrationModel
from simulation.infiltration.models import ConstantInfiltration, GreenAmptInfiltration, HortonInfiltration, CurveNumberInfiltration

logger = get_logger(__name__)


class InfiltrationEngine:
    """
    Plugin-based Infiltration service wrapper.
    Tracks cell-level cumulative infiltration states.
    """
    def __init__(self, rows: int, cols: int, model_name: str = "constant") -> None:
        """
        Initializes the infiltration engine.

        Args:
            rows: Grid rows count.
            cols: Grid cols count.
            model_name: Name of the active model ("constant", "green_ampt", "horton", "curve_number").
        """
        self.rows = rows
        self.cols = cols
        self.cumulative_infiltration: np.ndarray = np.zeros((rows, cols), dtype=np.float32)
        
        # Load the selected model
        self.model: InfiltrationModel = self._load_model(model_name)
        logger.info("InfiltrationEngine initialised", extra={"model": model_name, "grid": (rows, cols)})

    def set_model(self, model_name: str) -> None:
        """Swaps the active infiltration model at runtime."""
        self.model = self._load_model(model_name)
        logger.info("Infiltration model swapped", extra={"model": model_name})

    def compute_infiltration(
        self,
        rainfall_rate_m_s: np.ndarray,
        water_depth_m: np.ndarray,
        manning_n: np.ndarray,
        dt_seconds: float
    ) -> np.ndarray:
        """
        Calculates and updates cell infiltration depth (m) for the timestep.

        Args:
            rainfall_rate_m_s: 2D array of rainfall rate (m/s).
            water_depth_m: 2D surface water depth (m).
            manning_n: 2D Manning's n roughness coefficients.
            dt_seconds: Timestep size in seconds.

        Returns:
            2D grid of infiltration depths (m) computed in this timestep.
        """
        infil_m = self.model.calculate_infiltration(
            rainfall_rate_m_s=rainfall_rate_m_s,
            water_depth_m=water_depth_m,
            cumulative_infiltration_m=self.cumulative_infiltration,
            manning_n=manning_n,
            dt_seconds=dt_seconds
        )
        
        # Update cumulative records
        self.cumulative_infiltration += infil_m
        return infil_m

    def reset(self) -> None:
        """Resets cumulative infiltration memory."""
        self.cumulative_infiltration.fill(0.0)

    def _load_model(self, model_name: str) -> InfiltrationModel:
        """Factory method to load the concrete infiltration model."""
        name = model_name.lower().strip()
        if name == "constant":
            return ConstantInfiltration()
        elif name == "green_ampt":
            return GreenAmptInfiltration()
        elif name == "horton":
            return HortonInfiltration()
        elif name == "curve_number":
            return CurveNumberInfiltration()
        else:
            logger.warning(f"Infiltration model '{name}' not found. Defaulting to constant.")
            return ConstantInfiltration()
