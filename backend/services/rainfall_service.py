"""
backend/services/rainfall_service.py
--------------------------------------
RainfallService — application service for rainfall profile management.

Currently exposes available rainfall modes and validates parameters.
In Phase 3 this will integrate with IMD historical rainfall datasets.
"""

from __future__ import annotations

from typing import Dict, Any, List

from backend.utils import get_logger
from backend.config import settings
from backend.exceptions import RainfallException
from simulation.rainfall.engine import RainfallEngine, RainfallMode

logger = get_logger(__name__)


class RainfallService:
    """
    Service for rainfall data access and hyetograph generation.
    """

    def get_available_modes(self) -> List[Dict[str, str]]:
        """Return a list of supported rainfall modes."""
        return [
            {
                "id": RainfallMode.CONSTANT.value,
                "name": "Constant Intensity",
                "description": "Uniform rainfall throughout the storm duration",
            },
            {
                "id": RainfallMode.SYNTHETIC.value,
                "name": "Synthetic (Alternating Block)",
                "description": "Design storm using the Alternating Block Method",
            },
            {
                "id": RainfallMode.HISTORICAL.value,
                "name": "Historical (IMD)",
                "description": "Historical rainfall from IMD station data (Phase 3)",
            },
        ]

    def generate_preview(
        self,
        duration_hours: int,
        intensity_mm_hr: float,
        timestep_min: int,
        mode: RainfallMode = RainfallMode.CONSTANT,
    ) -> Dict[str, Any]:
        """
        Generate a hyetograph preview without running a full simulation.

        Returns:
            dict with n_steps, total_mm, and hyetograph list.
        """
        try:
            engine = RainfallEngine().generate(
                duration_hours=duration_hours,
                intensity_mm_hr=intensity_mm_hr,
                timestep_min=timestep_min,
                mode=mode,
            )
            return {
                "n_steps": engine.n_steps,
                "total_rainfall_mm": engine.total_rainfall_mm,
                "timestep_min": timestep_min,
                "hyetograph_mm": engine.hyetograph.tolist(),
            }
        except RainfallException:
            raise
        except Exception as exc:
            raise RainfallException(f"Failed to generate hyetograph: {exc}") from exc


# Module-level singleton
rainfall_service = RainfallService()
