"""
simulation/core/clock.py
------------------------
SimulationClock manages the timeline and time progression of the simulation.
Supports variable timesteps (Courant-Friedrichs-Lewy condition adjustments).
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from backend.utils import get_logger

logger = get_logger(__name__)


class SimulationClock:
    """
    Timeline synchronization clock for the digital twin simulation.
    Handles advancement, timeline tracking, and active status.
    """
    def __init__(
        self,
        start_time: Optional[datetime] = None,
        default_dt_seconds: float = 900.0  # Default 15 minutes
    ) -> None:
        """
        Initializes the clock.

        Args:
            start_time: The start datetime of the simulation.
            default_dt_seconds: Default timestep size in seconds.
        """
        self.start_time: datetime = start_time or datetime.now()
        self.current_time: datetime = self.start_time
        self.dt_seconds: float = default_dt_seconds
        self.elapsed_seconds: float = 0.0
        self.is_running: bool = False

    def start(self) -> None:
        """Starts or resumes the simulation timeline."""
        self.is_running = True
        logger.info("Simulation clock started", extra={"time": self.current_time.isoformat()})

    def pause(self) -> None:
        """Pauses the simulation timeline."""
        self.is_running = False
        logger.info("Simulation clock paused", extra={"elapsed_seconds": self.elapsed_seconds})

    def resume(self) -> None:
        """Resumes the simulation timeline."""
        self.is_running = True
        logger.info("Simulation clock resumed", extra={"time": self.current_time.isoformat()})

    def advance_timestep(self, custom_dt: Optional[float] = None) -> datetime:
        """
        Advances the clock by one timestep.

        Args:
            custom_dt: Optional variable timestep in seconds (e.g. calculated from CFL condition).

        Returns:
            The new current datetime.
        """
        dt = custom_dt if custom_dt is not None else self.dt_seconds
        self.current_time += timedelta(seconds=dt)
        self.elapsed_seconds += dt
        logger.debug(
            "Clock advanced",
            extra={"current_time": self.current_time.isoformat(), "dt_seconds": dt}
        )
        return self.current_time

    def reset(self) -> None:
        """Resets the clock back to the start time."""
        self.current_time = self.start_time
        self.elapsed_seconds = 0.0
        self.is_running = False
        logger.info("Simulation clock reset", extra={"start_time": self.start_time.isoformat()})

    def set_timestep(self, dt_seconds: float) -> None:
        """
        Sets a new default timestep size.

        Args:
            dt_seconds: Timestep size in seconds.
        """
        if dt_seconds <= 0:
            raise ValueError("Timestep must be greater than zero")
        self.dt_seconds = dt_seconds
        logger.info("Simulation clock timestep size updated", extra={"dt_seconds": dt_seconds})

    def to_dict(self) -> Dict[str, Any]:
        """Returns a summary of the clock state."""
        return {
            "start_time": self.start_time.isoformat(),
            "current_time": self.current_time.isoformat(),
            "elapsed_seconds": self.elapsed_seconds,
            "dt_seconds": self.dt_seconds,
            "is_running": self.is_running
        }
