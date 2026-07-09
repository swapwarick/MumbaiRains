"""simulation/rainfall.py — SHIM — logic moved to simulation/rainfall/engine.py"""
from simulation.rainfall.engine import RainfallEngine, RainfallMode  # noqa: F401
import numpy as np


def load_synthetic_hyetograph(
    duration_hours: int, intensity_mm_hr: float, time_step_min: int
) -> np.ndarray:
    """Legacy entry point."""
    return RainfallEngine().generate(
        duration_hours=duration_hours,
        intensity_mm_hr=intensity_mm_hr,
        timestep_min=time_step_min,
    ).hyetograph
