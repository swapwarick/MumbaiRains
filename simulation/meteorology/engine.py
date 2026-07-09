"""
simulation/meteorology/engine.py
--------------------------------
MeteorologyEngine — handles rainfall inputs, historical records, and spatial interpolation.
Exposes a unified interface for hyetograph and rainfall grid generation.
"""

from abc import ABC, abstractmethod
import numpy as np
from typing import Dict, Any, List, Optional
from backend.utils import get_logger
from backend.config import settings

logger = get_logger(__name__)


class MeteorologyEngine(ABC):
    """
    Abstract interface for meteorological inputs (rainfall grids, storm profiles).
    All rainfall source adapters (historical, real-time, synthetic) must implement this.
    """
    
    @abstractmethod
    def generate_hyetograph(self) -> np.ndarray:
        """
        Generates a 1-D time series of rainfall depths (mm) per simulation timestep.
        """
        pass

    @abstractmethod
    def get_spatial_rainfall_grid(self, step_idx: int) -> np.ndarray:
        """
        Generates a 2-D spatial grid of rainfall rate (m/s) for the given step.
        """
        pass


class SyntheticMeteorologyEngine(MeteorologyEngine):
    """
    Implementation for synthetic uniform rainfall design storms (e.g. constant intensity, alternating block).
    Supports spatial interpolation stubs.
    """
    def __init__(
        self,
        rows: int,
        cols: int,
        duration_hours: float,
        intensity_mm_hr: float,
        dt_minutes: float,
        mode: str = "constant"
    ) -> None:
        self.rows = rows
        self.cols = cols
        self.duration_hours = duration_hours
        self.intensity_mm_hr = intensity_mm_hr
        self.dt_minutes = dt_minutes
        self.mode = mode.lower().strip()
        self.n_steps = int((duration_hours * 60.0) / dt_minutes)
        self._hyetograph: Optional[np.ndarray] = None

    def generate_hyetograph(self) -> np.ndarray:
        rain_per_step = (self.intensity_mm_hr * self.dt_minutes) / 60.0  # mm
        
        if self.mode == "constant":
            self._hyetograph = np.full(self.n_steps, rain_per_step, dtype=np.float32)
        elif self.mode == "synthetic":
            # Alternating Block Method
            self._hyetograph = self._alternating_block(self.n_steps, rain_per_step)
        else:
            raise NotImplementedError(f"Rainfall mode '{self.mode}' is not implemented for synthetic storms.")
        
        return self._hyetograph

    def get_spatial_rainfall_grid(self, step_idx: int) -> np.ndarray:
        if self._hyetograph is None:
            self.generate_hyetograph()
        
        # Get step rain depth in mm
        rain_mm = self._hyetograph[step_idx] # type: ignore[index]
        
        # Convert mm to depth rate in m/s: rain_m / (dt_minutes * 60)
        dt_seconds = self.dt_minutes * 60.0
        rain_m_s = (rain_mm / 1000.0) / dt_seconds
        
        # Uniform spatial distribution for this synthetic engine
        return np.full((self.rows, self.cols), rain_m_s, dtype=np.float32)

    def _alternating_block(self, n_steps: int, rain_per_step: float) -> np.ndarray:
        increments = np.full(n_steps, rain_per_step, dtype=np.float32)
        sorted_inc = np.sort(increments)[::-1]
        result = np.zeros(n_steps, dtype=np.float32)
        center = n_steps // 2
        result[center] = sorted_inc[0]
        
        left_offset, right_offset = 1, 1
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


class HistoricalMeteorologyEngine(MeteorologyEngine):
    """
    Interface/stub for loading historical rainfall datasets (e.g. IMD station gauges or NetCDF radar grids).
    """
    def __init__(self, dataset_path: str) -> None:
        self.dataset_path = dataset_path

    def generate_hyetograph(self) -> np.ndarray:
        raise NotImplementedError("Historical rainfall dataset ingestion is not implemented yet.")

    def get_spatial_rainfall_grid(self, step_idx: int) -> np.ndarray:
        raise NotImplementedError("Historical spatial interpolation is not implemented yet.")


class RealTimeMeteorologyEngine(MeteorologyEngine):
    """
    Interface/stub for fetching and interpolating real-time telemetric rain gauges in Mumbai.
    """
    def generate_hyetograph(self) -> np.ndarray:
        raise NotImplementedError("Real-time gauge telemetry is not implemented yet.")

    def get_spatial_rainfall_grid(self, step_idx: int) -> np.ndarray:
        raise NotImplementedError("Real-time spatial interpolation is not implemented yet.")
