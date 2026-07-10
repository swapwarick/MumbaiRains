"""
simulation/plugins/registry.py
------------------------------
PluginRegistry managing registration and swappability of routing, infiltration,
hydraulics, and visualization plugins.
"""

from typing import Dict, Any, Type, Optional
from .base import RoutingPlugin, InfiltrationPlugin, HydraulicPlugin, VisualizationPlugin

class PluginRegistry:
    """
    Registry for swappable numerical and visual engine plugins.
    Allows loading and retrieval of registered plugins at runtime.
    """
    def __init__(self) -> None:
        self._routing_plugins: Dict[str, RoutingPlugin] = {}
        self._infiltration_plugins: Dict[str, InfiltrationPlugin] = {}
        self._hydraulic_plugins: Dict[str, HydraulicPlugin] = {}
        self._visualization_plugins: Dict[str, VisualizationPlugin] = {}

    def register_routing(self, name: str, plugin: RoutingPlugin) -> None:
        self._routing_plugins[name.lower().strip()] = plugin

    def register_infiltration(self, name: str, plugin: InfiltrationPlugin) -> None:
        self._infiltration_plugins[name.lower().strip()] = plugin

    def register_hydraulic(self, name: str, plugin: HydraulicPlugin) -> None:
        self._hydraulic_plugins[name.lower().strip()] = plugin

    def register_visualization(self, name: str, plugin: VisualizationPlugin) -> None:
        self._visualization_plugins[name.lower().strip()] = plugin

    def get_routing(self, name: str) -> RoutingPlugin:
        key = name.lower().strip()
        if key not in self._routing_plugins:
            raise KeyError(f"Routing plugin '{name}' is not registered.")
        return self._routing_plugins[key]

    def get_infiltration(self, name: str) -> InfiltrationPlugin:
        key = name.lower().strip()
        if key not in self._infiltration_plugins:
            raise KeyError(f"Infiltration plugin '{name}' is not registered.")
        return self._infiltration_plugins[key]

    def get_hydraulic(self, name: str) -> HydraulicPlugin:
        key = name.lower().strip()
        if key not in self._hydraulic_plugins:
            raise KeyError(f"Hydraulic plugin '{name}' is not registered.")
        return self._hydraulic_plugins[key]

    def get_visualization(self, name: str) -> VisualizationPlugin:
        key = name.lower().strip()
        if key not in self._visualization_plugins:
            raise KeyError(f"Visualization plugin '{name}' is not registered.")
        return self._visualization_plugins[key]
