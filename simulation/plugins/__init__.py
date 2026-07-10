"""
simulation/plugins package
--------------------------
Exposes plugin base interfaces, adapters, and registry (Task 3).
"""

from .base import RoutingPlugin, InfiltrationPlugin, HydraulicPlugin, VisualizationPlugin
from .registry import PluginRegistry
from .adapters import (
    RoutingPluginAdapter,
    InfiltrationPluginAdapter,
    HydraulicPluginAdapter,
    VisualizationPluginAdapter
)

# Global registry instance
registry = PluginRegistry()

# Register default plugins
from simulation.routing.engine import FlowRoutingEngine
from simulation.infiltration.engine import InfiltrationEngine
from simulation.hydraulic.routing import KinematicRoutingStrategy
from simulation.core.results_manager import ResultsManager

registry.register_routing("diffusion", RoutingPluginAdapter(FlowRoutingEngine(solver_type="diffusion")))
registry.register_infiltration("constant", InfiltrationPluginAdapter(InfiltrationEngine(200, 200, "constant")))
registry.register_hydraulic("kinematic", HydraulicPluginAdapter(KinematicRoutingStrategy()))
registry.register_visualization("geotiff", VisualizationPluginAdapter(ResultsManager()))

__all__ = [
    "RoutingPlugin",
    "InfiltrationPlugin",
    "HydraulicPlugin",
    "VisualizationPlugin",
    "PluginRegistry",
    "registry",
    "RoutingPluginAdapter",
    "InfiltrationPluginAdapter",
    "HydraulicPluginAdapter",
    "VisualizationPluginAdapter",
]
