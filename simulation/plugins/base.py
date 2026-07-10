"""
simulation/plugins/base.py
--------------------------
Abstract base interfaces for the plugin framework (Task 3).
Allows swappable solvers to be loaded without modifying the main controllers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
import numpy as np

class RoutingPlugin(ABC):
    """
    Interface for 2D surface water routing plugins.
    """
    @abstractmethod
    def route_water(
        self,
        elevation: np.ndarray,
        water_depth: np.ndarray,
        manning_n: np.ndarray,
        dx_m: float,
        dt_seconds: float
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Routes water over the surface.
        Returns (new_depth_grid, velocity_x, velocity_y).
        """
        pass


class InfiltrationPlugin(ABC):
    """
    Interface for soil infiltration plugins.
    """
    @abstractmethod
    def compute_loss(
        self,
        rainfall_rate_m_s: np.ndarray,
        water_depth_m: np.ndarray,
        manning_n: np.ndarray,
        dt_seconds: float
    ) -> np.ndarray:
        """
        Computes infiltration losses (m) during dt.
        Returns infiltration_depth_grid.
        """
        pass


class HydraulicPlugin(ABC):
    """
    Interface for 1D sub-surface hydraulic pipe routing plugins.
    """
    @abstractmethod
    def route_conduits(
        self,
        pipes: Dict[str, Any],
        junctions: Dict[str, Any],
        state: Any,
        inflows: Dict[str, float],
        dt: float,
        current_time_seconds: float
    ) -> Tuple[Any, float]:
        """
        Routes water through junctions and pipes.
        Returns (new_hydraulic_state, added_water_m3).
        """
        pass


class VisualizationPlugin(ABC):
    """
    Interface for post-simulation or runtime visualization output plugins.
    """
    @abstractmethod
    def export_output(self, filename: str, grid_data: np.ndarray, meta: Dict[str, Any]) -> str:
        """Exports grid visualisations or rasters to disk."""
        pass
