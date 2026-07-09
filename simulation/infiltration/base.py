"""
simulation/infiltration/base.py
-------------------------------
Abstract Base Class defining the interface for all soil infiltration models.
"""

from abc import ABC, abstractmethod
import numpy as np


class InfiltrationModel(ABC):
    """
    Abstract interface for swappable soil infiltration models.
    """
    
    @abstractmethod
    def calculate_infiltration(
        self,
        rainfall_rate_m_s: np.ndarray,
        water_depth_m: np.ndarray,
        cumulative_infiltration_m: np.ndarray,
        manning_n: np.ndarray,
        dt_seconds: float
    ) -> np.ndarray:
        """
        Calculates the infiltration depth (m) for each cell in this timestep.

        Args:
            rainfall_rate_m_s: 2D array of current rainfall rate (m/s).
            water_depth_m: 2D array of current surface water depth (m).
            cumulative_infiltration_m: 2D array of cumulative infiltrated depth (m).
            manning_n: 2D array of Manning's roughness coefficients.
            dt_seconds: Timestep duration in seconds.

        Returns:
            A 2D array of infiltration depths (m) for the timestep.
        """
        pass
