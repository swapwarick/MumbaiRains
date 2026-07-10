"""
simulation/forcing/units.py
----------------------------
Central UnitConverter for deterministic physical computations.
All unit conversions are restricted to this module.
"""

import numpy as np
from typing import Union

class UnitConverter:
    """
    Handles all deterministic unit conversions between standard hydrological
    units (e.g. mm/hr, mm, m, m^2, m^3, seconds, hours, days, cell dimensions).
    Supports both scalar values and NumPy arrays.
    """
    
    @staticmethod
    def mm_hr_to_m_s(val: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Convert rainfall intensity from mm/hr to m/s."""
        return val / 3600000.0

    @staticmethod
    def m_s_to_mm_hr(val: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Convert velocity or discharge flux from m/s to mm/hr equivalence."""
        return val * 3600000.0

    @staticmethod
    def mm_to_m(val: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Convert millimeters to meters."""
        return val / 1000.0

    @staticmethod
    def m_to_mm(val: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Convert meters to millimeters."""
        return val * 1000.0

    @staticmethod
    def depth_to_volume(depth_m: Union[float, np.ndarray], area_m2: float) -> Union[float, np.ndarray]:
        """Convert depth in meters over a specific area to volume in cubic meters."""
        return depth_m * area_m2

    @staticmethod
    def volume_to_depth(volume_m3: Union[float, np.ndarray], area_m2: float) -> Union[float, np.ndarray]:
        """Convert volume in cubic meters over a specific area to depth in meters."""
        return volume_m3 / area_m2 if area_m2 > 0 else 0.0

    @staticmethod
    def cell_depth_to_volume(depth_m: Union[float, np.ndarray], dx: float) -> Union[float, np.ndarray]:
        """Convert cell depth in meters to cell volume in cubic meters for isotropic cell size dx."""
        return depth_m * (dx * dx)

    @staticmethod
    def cell_volume_to_depth(volume_m3: Union[float, np.ndarray], dx: float) -> Union[float, np.ndarray]:
        """Convert cell volume in cubic meters to cell depth in meters for isotropic cell size dx."""
        return volume_m3 / (dx * dx) if dx > 0 else 0.0

    @staticmethod
    def hours_to_seconds(hours: float) -> float:
        """Convert hours to seconds."""
        return hours * 3600.0

    @staticmethod
    def seconds_to_hours(seconds: float) -> float:
        """Convert seconds to hours."""
        return seconds / 3600.0

    @staticmethod
    def days_to_seconds(days: float) -> float:
        """Convert days to seconds."""
        return days * 86400.0

    @staticmethod
    def seconds_to_days(seconds: float) -> float:
        """Convert seconds to days."""
        return seconds / 86400.0
