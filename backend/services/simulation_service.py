"""
backend/services/simulation_service.py
----------------------------------------
SimulationService — service layer wrapping the SimulationController.
Connects FastAPI requests to the modular simulation pipeline.
"""

from typing import Dict, Any

from backend.config import settings
from backend.utils import get_logger
from backend.exceptions import SimulationException
from simulation.core.controller import SimulationController

logger = get_logger(__name__)


class SimulationService:
    """
    SimulationService delegates uvicorn API request payloads to the SimulationController
    to run deterministic GIS flood scenarios.
    """
    def __init__(self) -> None:
        self.controller: Optional[SimulationController] = None

    def run(
        self,
        duration_hours: float,
        intensity_mm_hr: float,
        time_step_min: int,
        rainfall_mode: str = "constant",
        scenario_name: str = "synthetic"
    ) -> Dict[str, Any]:
        """
        Executes a dynamic flood simulation run.
        """
        logger.info(
            "Executing simulation service run",
            extra={"scenario": scenario_name, "intensity": intensity_mm_hr, "duration_h": duration_hours}
        )
        
        self.controller = SimulationController(scenario_name=scenario_name)
        self.controller.initialize(
            dem_path=str(settings.dem_path),
            gpkg_path=str(settings.gpkg_path),
            duration_hours=duration_hours,
            intensity_mm_hr=intensity_mm_hr,
            timestep_min=float(time_step_min)
        )
        
        depth_history = self.controller.run_all()
        
        # Prepare response dict compatible with frontend dashboard metadata expectation
        meta = self.controller.grid_manager.meta  # type: ignore[union-attr]
        hyetograph = self.controller.meteorology.generate_hyetograph()  # type: ignore[union-attr]
        
        return {
            "metadata": {
                "width": meta["width"],
                "height": meta["height"],
                "crs": meta["crs"],
                "transform": meta["transform"],
            },
            "time_steps_min": time_step_min,
            "rainfall_hyetograph_mm": hyetograph.tolist(),
            "depth_history": depth_history,
        }

    def reset(self) -> Dict[str, str]:
        """Resets the simulation controller state."""
        if self.controller:
            self.controller.reset()
        logger.info("Simulation service states reset")
        return {"status": "success", "message": "Simulation states reset successfully."}

    def status(self) -> Dict[str, Any]:
        """Returns the readiness status of the simulation controller."""
        if self.controller and self.controller.clock and self.controller.clock.is_running:
            return {
                "status": "running",
                "simulation_phase": 2,
                "message": "Simulation runs in progress."
            }
        return {
            "status": "ready",
            "simulation_phase": 2,
            "message": "Simulation engine is active."
        }


# Module-level singleton
simulation_service = SimulationService()
