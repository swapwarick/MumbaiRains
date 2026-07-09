"""
simulation/core/simulation_engine.py — LEGACY DELEGATE SHIM
-----------------------------------------------------------
This module is preserved as a delegate shim for backward compatibility with old scripts/tests.
Internally delegates all calls to the new SimulationController.
"""

from typing import Dict, Any, List
from simulation.core.controller import SimulationController
from simulation.rainfall.engine import RainfallMode


class SimulationEngine:
    """
    Legacy wrapper delegating to SimulationController.
    """
    def run(
        self,
        dem_path: str | None = None,
        gpkg_path: str | None = None,
        duration_hours: int | None = None,
        intensity_mm_hr: float | None = None,
        timestep_min: int | None = None,
        rainfall_mode: RainfallMode = RainfallMode.CONSTANT,
    ) -> Dict[str, Any]:
        
        # Configure and run the controller
        controller = SimulationController(scenario_name="synthetic")
        controller.initialize(
            dem_path=dem_path or "",
            gpkg_path=gpkg_path or "",
            duration_hours=float(duration_hours) if duration_hours is not None else None,
            intensity_mm_hr=float(intensity_mm_hr) if intensity_mm_hr is not None else None,
            timestep_min=float(timestep_min) if timestep_min is not None else None
        )
        
        depth_history = controller.run_all()
        meta = controller.grid_manager.meta  # type: ignore[union-attr]
        hyetograph = controller.meteorology.generate_hyetograph()  # type: ignore[union-attr]
        
        return {
            "metadata": {
                "width": meta["width"],
                "height": meta["height"],
                "crs": meta["crs"],
                "transform": meta["transform"],
            },
            "time_steps_min": timestep_min or int(controller.clock.dt_seconds / 60.0),  # type: ignore[union-attr]
            "rainfall_hyetograph_mm": hyetograph.tolist(),
            "depth_history": depth_history,
        }
