"""
simulation/hydrology/engine.py
-------------------------------
HydrologyEngine — manages surface runoff and spatial water distribution.

Responsibilities:
    - Apply SCS Curve Number runoff per timestep
    - Apply elevation-based flood susceptibility weighting
    - Apply drainage capacity factor
    - Convert rainfall (mm) to spatially-distributed runoff (m)

This engine does NOT move water between cells — that is the FloodEngine's job.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Optional

from backend.utils import get_logger
from backend.config import settings
from backend.exceptions import SimulationException
from simulation.hydrology.runoff import calculate_scs_runoff

logger = get_logger(__name__)


@dataclass
class HydrologyEngine:
    """
    Computes spatially-distributed surface runoff from rainfall input.

    The engine pre-computes elevation-derived weights on initialisation
    so that per-timestep runoff calculation is fast (pure NumPy).

    Attributes:
        _cn_grid:        SCS Curve Number grid (float32).
        _flood_weight:   Elevation-based flood susceptibility [0, ∞].
        _drainage_factor: Drainage efficiency [0, 1] per cell.
        _accumulated_rain: Cumulative rainfall depth this simulation run (mm).
    """

    _cn_grid: Optional[np.ndarray] = field(default=None, repr=False)
    _flood_weight: Optional[np.ndarray] = field(default=None, repr=False)
    _drainage_factor: Optional[np.ndarray] = field(default=None, repr=False)
    _accumulated_rain: float = field(default=0.0, repr=False)

    def initialise(self, elevation: np.ndarray, cn_value: float | None = None) -> "HydrologyEngine":
        """
        Pre-compute elevation-derived spatial weights.

        Args:
            elevation: 2-D float32 elevation grid.
            cn_value:  Uniform SCS Curve Number. Defaults to ``settings.default_cn``.

        Returns:
            Self — enables chaining.
        """
        cn = cn_value if cn_value is not None else settings.default_cn
        self._cn_grid = np.full_like(elevation, cn, dtype=np.float32)

        elev_min = float(elevation.min())
        elev_max = float(elevation.max())
        elev_range = max(elev_max - elev_min, 1.0)
        elev_norm = (elevation - elev_min) / elev_range  # 0 (lowest) → 1 (highest)

        # Low-lying areas collect more water; hilltops shed water quickly.
        # weight ≈ 1.0 at minimum elevation, ≈ 0.05 at maximum elevation.
        weight = np.exp(-3.0 * elev_norm)
        self._flood_weight = (weight / weight.mean()).astype(np.float32)

        # Urban valleys have overwhelmed drains (low drainage factor = high retention).
        # Natural high ground drains well (high drainage factor = low retention).
        self._drainage_factor = (0.05 + 0.45 * elev_norm).astype(np.float32)

        self._accumulated_rain = 0.0
        logger.info(
            "HydrologyEngine initialised",
            extra={"cn": cn, "shape": elevation.shape},
        )
        return self

    def reset(self) -> None:
        """Reset accumulated rainfall counter for a new simulation run."""
        self._accumulated_rain = 0.0

    def compute_runoff(self, rain_mm: float) -> np.ndarray:
        """
        Calculate incremental spatially-distributed runoff for one timestep.

        Args:
            rain_mm: Rainfall depth for this timestep (mm).

        Returns:
            runoff_m: float32 grid of runoff depth in metres per cell.

        Raises:
            SimulationException: If initialise() was not called first.
        """
        if self._cn_grid is None:
            raise SimulationException(
                "HydrologyEngine not initialised. Call initialise(elevation) first."
            )

        prev_rain = self._accumulated_rain
        self._accumulated_rain += rain_mm

        # Total cumulative runoff before and after this step
        total_after = calculate_scs_runoff(
            np.array([self._accumulated_rain]), self._cn_grid
        )
        incremental: np.ndarray
        if prev_rain > 0:
            total_before = calculate_scs_runoff(np.array([prev_rain]), self._cn_grid)
            incremental = np.maximum(total_after - total_before, 0.0)
        else:
            incremental = np.maximum(total_after, 0.0)

        # Convert mm → m, apply spatial weighting, subtract drainage capacity
        runoff_m = (incremental / 1000.0) * self._flood_weight
        runoff_m = runoff_m * (1.0 - self._drainage_factor)
        return runoff_m.astype(np.float32)
