"""
simulation/flood.py — SHIM
----------------------------
Preserved for backward compatibility. Logic is in simulation/flood/engine.py.
"""
from simulation.flood.engine import FloodEngine as FloodSimulation  # noqa: F401
from simulation.core.simulation_engine import SimulationEngine as _SimEng
from simulation.rainfall.engine import RainfallMode
from typing import Dict, Any


def run_simulation(
    dem_path: str,
    gpkg_path: str,
    duration_hours: int,
    intensity_mm_hr: float,
    time_step_min: int = 15,
) -> Dict[str, Any]:
    """Legacy entry point — delegates to SimulationEngine."""
    return _SimEng().run(
        dem_path=dem_path,
        gpkg_path=gpkg_path,
        duration_hours=duration_hours,
        intensity_mm_hr=intensity_mm_hr,
        timestep_min=time_step_min,
        rainfall_mode=RainfallMode.CONSTANT,
    )
