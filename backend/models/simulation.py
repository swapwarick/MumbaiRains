"""
backend/models/simulation.py
-----------------------------
Pydantic request and response models for the simulation API.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from simulation.rainfall.engine import RainfallMode


class SimulationRequest(BaseModel):
    """Request body for POST /api/simulation/run."""
    duration_hours: int = Field(
        default=4,
        ge=1, le=72,
        description="Storm duration in hours",
    )
    intensity_mm_hr: float = Field(
        default=30.0,
        ge=0.0, le=500.0,
        description="Rainfall intensity in mm/hr",
    )
    time_step_min: int = Field(
        default=15,
        ge=5, le=60,
        description="Simulation timestep in minutes",
    )
    rainfall_mode: RainfallMode = Field(
        default=RainfallMode.CONSTANT,
        description="Hyetograph distribution model",
    )


class SimulationMetadata(BaseModel):
    """Grid and CRS metadata embedded in a simulation response."""
    width: int
    height: int
    crs: str
    transform: List[float]


class SimulationResponse(BaseModel):
    """Response body for POST /api/simulation/run."""
    metadata: SimulationMetadata
    time_steps_min: int
    rainfall_hyetograph_mm: List[float]
    depth_history: List[List[List[float]]]


class SimulationStatus(BaseModel):
    """Response body for GET /api/simulation/status."""
    status: str
    simulation_phase: int
    message: str
