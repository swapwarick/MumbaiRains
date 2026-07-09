"""
backend/api/simulation.py
--------------------------
Simulation API router.
"""

from fastapi import APIRouter, HTTPException
from backend.utils import get_logger
from backend.exceptions import SimulationException, RainfallException
from backend.models.simulation import SimulationRequest
from backend.services.simulation_service import simulation_service
from backend.services.rainfall_service import rainfall_service

logger = get_logger(__name__)
router = APIRouter(prefix="/api/simulation", tags=["Simulation"])


@router.get("/status", summary="Get simulation engine status")
def get_simulation_status() -> dict:
    """Return current readiness status of the simulation engine."""
    return simulation_service.status()


@router.post("/run", summary="Run a flood simulation")
def run_simulation(req: SimulationRequest) -> dict:
    """
    Execute a flood simulation for the specified storm profile.
    Returns full depth history for animated playback.
    """
    try:
        return simulation_service.run(
            duration_hours=req.duration_hours,
            intensity_mm_hr=req.intensity_mm_hr,
            time_step_min=req.time_step_min,
            rainfall_mode=req.rainfall_mode,
        )
    except (SimulationException, RainfallException) as exc:
        logger.error(f"Simulation run error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/reset", summary="Reset simulation state")
def reset_simulation() -> dict:
    """Reset the simulation to its initial (dry) state."""
    return simulation_service.reset()


@router.get("/rainfall/modes", summary="List available rainfall modes")
def get_rainfall_modes() -> dict:
    """Return available rainfall distribution modes."""
    return {"modes": rainfall_service.get_available_modes()}
