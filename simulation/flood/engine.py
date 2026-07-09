"""
simulation/flood/engine.py
--------------------------
FloodEngine — computes flood depth, extent, duration, and hazard classifications.
NOTE: This engine does NOT generate rainfall or route water. It only analyses
the water depth and velocity grids for post-processing and risk assessment.

References:
1. UK Defra/Environment Agency, 2006. Flood Risks to People (FD2321/TR2).
   Hazard Rating formula: HR = d * (v + 0.5) + DF (debris factor).
"""

from typing import Dict, Any, Tuple
import numpy as np

from backend.utils import get_logger

logger = get_logger(__name__)


class FloodEngine:
    """
    Computes diagnostic and hazard mapping metrics from flood simulation states.
    Keeps track of flood extent, cumulative duration, and safety classification.
    """
    def __init__(self, rows: int, cols: int, flood_threshold_m: float = 0.05) -> None:
        self.rows = rows
        self.cols = cols
        self.threshold = flood_threshold_m
        
        # Grid metrics tracking
        self.flood_duration_seconds: np.ndarray = np.zeros((rows, cols), dtype=np.float32)
        self.hazard_rating: np.ndarray = np.zeros((rows, cols), dtype=np.float32)
        self.hazard_class: np.ndarray = np.zeros((rows, cols), dtype=np.uint8) # 0=Dry, 1=Low, 2=Moderate, 3=High, 4=Extreme
        
        logger.info("FloodEngine initialised", extra={"flood_threshold_m": flood_threshold_m})

    def update_metrics(
        self,
        water_depth_m: np.ndarray,
        velocity_x_m_s: np.ndarray,
        velocity_y_m_s: np.ndarray,
        dt_seconds: float
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Updates flood duration, hazard ratings, and hazard classification grids.

        Hazard rating (HR) formula based on Defra FD2321:
            HR = d * (v + 0.5) + DF
            where:
                d = depth (m)
                v = velocity magnitude (m/s) = sqrt(vx^2 + vy^2)
                DF = debris factor (assumed 0.5 for urban areas with depths > 0.1m, else 0.0)

        Hazard Classes (HR thresholds):
            0: HR < 0.75      -> Low Hazard (Caution)
            1: 0.75 <= HR < 1.25 -> Moderate Hazard (Danger for some)
            2: 1.25 <= HR < 2.5  -> Significant Hazard (Danger for most)
            3: HR >= 2.5      -> Extreme Hazard (Danger for all)
        """
        # 1. Flood duration tracking
        flooded_mask = water_depth_m > self.threshold
        self.flood_duration_seconds[flooded_mask] += dt_seconds
        
        # 2. Hazard rating calculation
        velocity_mag = np.sqrt(velocity_x_m_s**2 + velocity_y_m_s**2)
        debris_factor = np.where(water_depth_m > 0.1, 0.5, 0.0)
        
        # Defra HR equation
        self.hazard_rating = water_depth_m * (velocity_mag + 0.5) + debris_factor
        
        # 3. Hazard classification
        # Initialize with dry / zero hazard
        new_class = np.zeros_like(self.hazard_rating, dtype=np.uint8)
        
        # Apply classifications based on FD2321 thresholds
        new_class[water_depth_m > 0.0] = 1        # Low hazard (Caution)
        new_class[self.hazard_rating >= 0.75] = 2  # Moderate (Danger for some)
        new_class[self.hazard_rating >= 1.25] = 3  # High (Danger for most)
        new_class[self.hazard_rating >= 2.5] = 4   # Extreme (Danger for all)
        
        # Mask out dry cells
        new_class[~flooded_mask] = 0
        self.hazard_class = new_class

        logger.debug(
            "Flood diagnostics updated",
            extra={"max_hazard_rating": float(self.hazard_rating.max()), "flooded_cells": int(np.sum(flooded_mask))}
        )
        return flooded_mask, self.hazard_rating, self.hazard_class

    def get_hazard_statistics(self) -> Dict[str, Any]:
        """Returns statistical counts of cells in each hazard classification."""
        total = self.rows * self.cols
        return {
            "dry_pct": float(np.sum(self.hazard_class == 0) / total * 100.0),
            "low_pct": float(np.sum(self.hazard_class == 1) / total * 100.0),
            "moderate_pct": float(np.sum(self.hazard_class == 2) / total * 100.0),
            "high_pct": float(np.sum(self.hazard_class == 3) / total * 100.0),
            "extreme_pct": float(np.sum(self.hazard_class == 4) / total * 100.0)
        }

    def reset(self) -> None:
        """Resets all cumulative metrics."""
        self.flood_duration_seconds.fill(0.0)
        self.hazard_rating.fill(0.0)
        self.hazard_class.fill(0)
