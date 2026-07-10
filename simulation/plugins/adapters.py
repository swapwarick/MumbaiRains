"""
simulation/plugins/adapters.py
-----------------------------
Adapters implementing the plugin interfaces by wrapping existing engine classes (Task 3).
"""

from typing import Dict, Any, Tuple
import numpy as np

from .base import RoutingPlugin, InfiltrationPlugin, HydraulicPlugin, VisualizationPlugin
from simulation.routing.engine import FlowRoutingEngine
from simulation.infiltration.engine import InfiltrationEngine
from simulation.hydraulic.routing import KinematicRoutingStrategy
from simulation.core.results_manager import ResultsManager

class RoutingPluginAdapter(RoutingPlugin):
    """Adapts FlowRoutingEngine to the RoutingPlugin interface."""
    def __init__(self, engine: FlowRoutingEngine) -> None:
        self.engine = engine

    def route_water(
        self,
        elevation: np.ndarray,
        water_depth: np.ndarray,
        manning_n: np.ndarray,
        dx_m: float,
        dt_seconds: float
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        return self.engine.route(
            elevation=elevation,
            water_depth=water_depth,
            manning_n=manning_n,
            dx_m=dx_m,
            dt_seconds=dt_seconds
        )


class InfiltrationPluginAdapter(InfiltrationPlugin):
    """Adapts InfiltrationEngine to the InfiltrationPlugin interface."""
    def __init__(self, engine: InfiltrationEngine) -> None:
        self.engine = engine

    def compute_loss(
        self,
        rainfall_rate_m_s: np.ndarray,
        water_depth_m: np.ndarray,
        manning_n: np.ndarray,
        dt_seconds: float
    ) -> np.ndarray:
        return self.engine.compute_infiltration(
            rainfall_rate_m_s=rainfall_rate_m_s,
            water_depth_m=water_depth_m,
            manning_n=manning_n,
            dt_seconds=dt_seconds
        )


class HydraulicPluginAdapter(HydraulicPlugin):
    """Adapts KinematicRoutingStrategy/HydraulicRoutingEngine to the HydraulicPlugin interface."""
    def __init__(self, strategy: KinematicRoutingStrategy) -> None:
        self.strategy = strategy

    def route_conduits(
        self,
        pipes: Dict[str, Any],
        junctions: Dict[str, Any],
        state: Any,
        inflows: Dict[str, float],
        dt: float,
        current_time_seconds: float
    ) -> Tuple[Any, float]:
        return self.strategy.route_step(
            pipes=pipes,
            junctions=junctions,
            state=state,
            inflows=inflows,
            dt=dt,
            current_time_seconds=current_time_seconds
        )


class VisualizationPluginAdapter(VisualizationPlugin):
    """Adapts ResultsManager to the VisualizationPlugin interface."""
    def __init__(self, manager: ResultsManager) -> None:
        self.manager = manager

    def export_output(self, filename: str, grid_data: np.ndarray, meta: Dict[str, Any]) -> str:
        path = self.manager.export_geotiff(filename, grid_data, meta)
        return str(path)
