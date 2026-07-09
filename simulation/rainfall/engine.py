"""
simulation/rainfall/engine.py
------------------------------
RainfallEngine — generates and manages rainfall time series.

Currently supported modes:
    - CONSTANT : uniform intensity throughout storm duration
    - SYNTHETIC : Alternating Block Method design storm (future)
    - HISTORICAL: load from CSV/NetCDF (future)

The engine produces a hyetograph — an array of rainfall depths (mm) per timestep.
"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
import numpy as np

from backend.utils import get_logger
from backend.config import settings
from backend.exceptions import RainfallException

logger = get_logger(__name__)


class RainfallMode(str, Enum):
    CONSTANT   = "constant"
    SYNTHETIC  = "synthetic"
    HISTORICAL = "historical"


@dataclass
class RainfallEngine:
    """
    Generates rainfall hyetographs for use by HydrologyEngine.

    A hyetograph is a numpy array of length ``n_steps`` where each value
    is the rainfall depth (mm) that falls during that timestep.

    Attributes:
        _hyetograph: Computed hyetograph array.
        _mode:       Active rainfall mode.
        _intensity:  Storm intensity (mm/hr).
        _duration:   Storm duration (hours).
        _timestep:   Timestep length (minutes).
    """

    _hyetograph: Optional[np.ndarray] = field(default=None, repr=False)
    _mode: RainfallMode = field(default=RainfallMode.CONSTANT, repr=True)
    _intensity: float = field(default=0.0, repr=True)
    _duration: int = field(default=0, repr=True)
    _timestep: int = field(default=0, repr=True)

    def generate(
        self,
        duration_hours: int | None = None,
        intensity_mm_hr: float | None = None,
        timestep_min: int | None = None,
        mode: RainfallMode = RainfallMode.CONSTANT,
    ) -> "RainfallEngine":
        """
        Generate a hyetograph.

        Args:
            duration_hours:   Total storm duration. Defaults to ``settings.default_duration_hours``.
            intensity_mm_hr:  Rainfall intensity. Defaults to ``settings.default_intensity_mm_hr``.
            timestep_min:     Length of each timestep. Defaults to ``settings.default_timestep_min``.
            mode:             Rainfall distribution mode.

        Returns:
            Self — enables chaining: ``engine.generate().hyetograph``.

        Raises:
            RainfallException: If parameters are invalid.
        """
        dur = duration_hours    if duration_hours    is not None else settings.default_duration_hours
        inten = intensity_mm_hr if intensity_mm_hr   is not None else settings.default_intensity_mm_hr
        dt = timestep_min       if timestep_min       is not None else settings.default_timestep_min

        if dur <= 0:
            raise RainfallException(f"duration_hours must be > 0, got {dur}")
        if inten < 0:
            raise RainfallException(f"intensity_mm_hr must be >= 0, got {inten}")
        if dt <= 0:
            raise RainfallException(f"timestep_min must be > 0, got {dt}")

        self._intensity = float(inten)
        self._duration = int(dur)
        self._timestep = int(dt)
        self._mode = mode

        n_steps = int((dur * 60) / dt)
        rain_per_step = inten * dt / 60.0  # mm per timestep

        if mode == RainfallMode.CONSTANT:
            self._hyetograph = np.full(n_steps, rain_per_step, dtype=np.float32)

        elif mode == RainfallMode.SYNTHETIC:
            # Alternating Block Method — peak centred, decreasing outward
            self._hyetograph = self._alternating_block(n_steps, rain_per_step)

        elif mode == RainfallMode.HISTORICAL:
            raise RainfallException(
                "HISTORICAL mode not yet implemented. "
                "Provide a CSV loader in a future phase."
            )
        else:
            raise RainfallException(f"Unknown rainfall mode: {mode}")

        logger.info(
            "Hyetograph generated",
            extra={
                "mode": mode.value,
                "steps": n_steps,
                "total_mm": round(float(self._hyetograph.sum()), 2),
            },
        )
        return self

    @property
    def hyetograph(self) -> np.ndarray:
        """Rainfall depth (mm) per timestep."""
        if self._hyetograph is None:
            raise RainfallException("No hyetograph generated. Call generate() first.")
        return self._hyetograph

    @property
    def n_steps(self) -> int:
        """Number of timesteps in the current hyetograph."""
        return len(self.hyetograph)

    @property
    def total_rainfall_mm(self) -> float:
        """Total cumulative rainfall for the storm (mm)."""
        return float(self.hyetograph.sum())

    # ---------------------------------------------------------------------- #
    # Private helpers                                                          #
    # ---------------------------------------------------------------------- #

    @staticmethod
    def _alternating_block(n_steps: int, rain_per_step: float) -> np.ndarray:
        """
        Generate an Alternating Block Method hyetograph.
        The largest increment is placed in the centre; remaining blocks
        alternate left/right in decreasing order.
        """
        if n_steps == 0:
            return np.array([], dtype=np.float32)

        # Uniform increments as starting point (future: IDF-derived intensities)
        increments = np.full(n_steps, rain_per_step, dtype=np.float32)
        # Sort descending and rearrange in alternating-block pattern
        sorted_inc = np.sort(increments)[::-1]
        result = np.zeros(n_steps, dtype=np.float32)
        
        center = n_steps // 2
        result[center] = sorted_inc[0]
        
        left_offset = 1
        right_offset = 1
        for i in range(1, n_steps):
            if i % 2 == 1:
                if center + right_offset < n_steps:
                    result[center + right_offset] = sorted_inc[i]
                    right_offset += 1
                else:
                    result[center - left_offset] = sorted_inc[i]
                    left_offset += 1
            else:
                if center - left_offset >= 0:
                    result[center - left_offset] = sorted_inc[i]
                    left_offset += 1
                else:
                    result[center + right_offset] = sorted_inc[i]
                    right_offset += 1
                    
        return result
