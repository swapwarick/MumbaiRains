"""
simulation/tide/engine.py
-------------------------
TideEngine — simulates sea level boundaries, high/low tide astronomical cycles,
storm surges, and coastal backwater effects.

References:
1. Pugh, D.T., 1987. Tides, surges and mean sea-level. John Wiley & Sons.
2. FEMA Coastal Flood Insurance Study guidelines for storm surge boundary modeling.
"""

from typing import Dict, Any, Optional
import numpy as np
from datetime import datetime

from backend.utils import get_logger

logger = get_logger(__name__)


class TideEngine:
    """
    Simulates tidal boundary conditions along Mumbai's coastline.
    Predicts astronomical water levels and storm surges.
    """
    def __init__(
        self,
        mean_sea_level_m: float = 0.0,
        tidal_range_m: float = 4.5,         # Typical spring tide range for Mumbai (approx 4-5m)
        tide_period_hours: float = 12.42,   # Semidiurnal tide M2 component period
        storm_surge_m: float = 0.0
    ) -> None:
        self.msl = mean_sea_level_m
        self.amplitude = tidal_range_m / 2.0
        self.period = tide_period_hours
        self.surge = storm_surge_m
        
        logger.info("TideEngine initialised", extra={"tidal_range_m": tidal_range_m, "msl_m": mean_sea_level_m})

    def get_sea_level(self, elapsed_seconds: float, current_datetime: Optional[datetime] = None) -> float:
        """
        Computes the current sea level (m) relative to Chart Datum / Mean Sea Level.
        Uses a standard semidiurnal harmonic cosine approximation:
        H(t) = MSL + Amplitude * cos(2 * pi * t / Period) + Surge
        
        Args:
            elapsed_seconds: Seconds elapsed since the start of the simulation.
            current_datetime: Optional datetime for future INCOIS tide table lookups.

        Returns:
            Sea level elevation in meters.
        """
        if current_datetime is not None:
            # Future Phase 3: Ingest real-time astronomical tide predictions (INCOIS datasets)
            pass

        # Convert semidiurnal period to seconds
        period_seconds = self.period * 3600.0
        
        # Astronomical tide component
        tide = self.amplitude * np.cos(2.0 * np.pi * elapsed_seconds / period_seconds)
        
        # Total sea level includes surge
        total_sea_level = self.msl + tide + self.surge
        
        logger.debug(
            "Tidal boundary calculation",
            extra={"elapsed_seconds": elapsed_seconds, "tide_elevation_m": total_sea_level}
        )
        return float(total_sea_level)

    def set_storm_surge(self, surge_m: float) -> None:
        """Sets storm surge height in meters (e.g. from cyclonic wind setup)."""
        self.surge = surge_m
        logger.info("Storm surge level updated", extra={"surge_m": surge_m})
