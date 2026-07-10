"""
simulation/forcing/sources.py
-----------------------------
Forcing sources (RainSource, PointSource, AreaSource) that compute water depth additions.
"""

from abc import ABC, abstractmethod
import numpy as np
from typing import Optional
from .types import ForcingType
from .units import UnitConverter


class ForcingSource(ABC):
    """
    Abstract base class for all external water inputs.
    """
    def __init__(self, source_id: str, forcing_type: ForcingType) -> None:
        self.source_id = source_id
        self.forcing_type = forcing_type
        self.enabled = True

    @abstractmethod
    def get_water_input(self, rows: int, cols: int, dx: float, dt: float) -> np.ndarray:
        """
        Calculates the depth of water (in meters) to be added to each grid cell
        during a timestep dt.
        
        Returns:
            depth_grid: 2D float32 array of shape (rows, cols) in meters.
        """
        pass


class RainSource(ForcingSource):
    """
    Represents uniform grid-wide rainfall forcing.
    """
    def __init__(self, source_id: str, intensity_mm_hr: float) -> None:
        super().__init__(source_id, ForcingType.RAIN)
        self.intensity = float(intensity_mm_hr)

    def get_water_input(self, rows: int, cols: int, dx: float, dt: float) -> np.ndarray:
        # mm/hr to m/s
        rate_m_s = UnitConverter.mm_hr_to_m_s(self.intensity)
        # depth in meters for dt seconds
        depth_m = rate_m_s * dt
        return np.full((rows, cols), depth_m, dtype=np.float32)


class PointSource(ForcingSource):
    """
    Represents localized point discharge water input (e.g. outfall, pipeline, boundary inflow).
    """
    def __init__(self, source_id: str, discharge_m3_s: float, row: int, col: int) -> None:
        super().__init__(source_id, ForcingType.POINT)
        self.discharge = float(discharge_m3_s)
        self.row = int(row)
        self.col = int(col)

    def get_water_input(self, rows: int, cols: int, dx: float, dt: float) -> np.ndarray:
        grid = np.zeros((rows, cols), dtype=np.float32)
        if 0 <= self.row < rows and 0 <= self.col < cols:
            # Volume added in dt: Q * dt (m^3)
            vol_m3 = self.discharge * dt
            # Convert cell volume to depth in cell
            depth_m = UnitConverter.cell_volume_to_depth(vol_m3, dx)
            grid[self.row, self.col] = depth_m
        return grid


class AreaSource(ForcingSource):
    """
    Represents uniform water input over a specified spatial mask (e.g. sub-catchment, benchmark area).
    """
    def __init__(self, source_id: str, rate: float, mask: np.ndarray, is_intensity: bool = True) -> None:
        """
        Args:
            source_id: Unique string identifier.
            rate: Either rainfall intensity (mm/hr) if is_intensity=True, or volumetric discharge (m^3/s) if is_intensity=False.
            mask: 2D boolean array of shape matching the grid.
            is_intensity: Whether rate is intensity (mm/hr) or volume flux (m^3/s).
        """
        super().__init__(source_id, ForcingType.AREA)
        self.rate = float(rate)
        self.mask = mask.astype(bool)
        self.is_intensity = is_intensity

    def get_water_input(self, rows: int, cols: int, dx: float, dt: float) -> np.ndarray:
        grid = np.zeros((rows, cols), dtype=np.float32)
        
        # Verify mask dimensions match request
        if self.mask.shape != (rows, cols):
            raise ValueError(f"AreaSource mask shape {self.mask.shape} does not match grid {(rows, cols)}.")
            
        num_cells = np.sum(self.mask)
        if num_cells == 0:
            return grid
            
        if self.is_intensity:
            # mm/hr to m/s
            rate_m_s = UnitConverter.mm_hr_to_m_s(self.rate)
            depth_m = rate_m_s * dt
            grid[self.mask] = depth_m
        else:
            # Discharge rate Q (m^3/s) -> Total volume Q * dt (m^3)
            vol_m3 = self.rate * dt
            # Distribute volume uniformly among all masked cells
            vol_per_cell = vol_m3 / num_cells
            # Convert to depth
            depth_m = UnitConverter.cell_volume_to_depth(vol_per_cell, dx)
            grid[self.mask] = depth_m
            
        return grid
