"""
simulation/core package
-----------------------
Core orchestration models and workflows: Cell model, SimulationState,
SimulationClock, and GridManager.
"""

from .cell import Cell
from .state import SimulationState
from .clock import SimulationClock
from .grid_manager import GridManager
from .scenario_manager import Scenario, ScenarioManager
from .results_manager import ResultsManager
from .controller import SimulationController
from .verification import (
    verify_all_physics,
    verify_no_negative_water_depth,
    verify_mass_conservation,
    verify_no_nan,
    verify_no_inf,
    verify_flow_direction_validity
)
from .profiler import PerformanceProfiler, ProfilerReport

__all__ = [
    "Cell",
    "SimulationState",
    "SimulationClock",
    "GridManager",
    "Scenario",
    "ScenarioManager",
    "ResultsManager",
    "SimulationController",
    "verify_all_physics",
    "verify_no_negative_water_depth",
    "verify_mass_conservation",
    "verify_no_nan",
    "verify_no_inf",
    "verify_flow_direction_validity",
    "PerformanceProfiler",
    "ProfilerReport",
]
