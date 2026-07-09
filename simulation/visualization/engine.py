"""
simulation/visualization/engine.py
----------------------------------
VisualizationEngine — provides helper methods to prepare arrays for map visualization
(e.g., hillshades, dynamic opacity interpolation, and legend scaling).
"""

from typing import Dict, Any, List, Tuple
import numpy as np

from backend.utils import get_logger

logger = get_logger(__name__)


class VisualizationEngine:
    """
    Utility engine that compiles numerical outputs into visual assets.
    """
    
    @staticmethod
    def get_color_interpolation_stops(
        min_depth: float = 0.001,
        max_depth: float = 2.5
    ) -> List[Tuple[float, str]]:
        """
        Returns color stops for the MapLibre water depth styling layer.
        Defines a scientific blue hazard gradient.
        """
        return [
            (0.000, "rgba(0, 0, 0, 0)"),        # Dry
            (min_depth, "rgba(96, 165, 250, 0.4)"),  # Light blue (shallow)
            (0.5 * max_depth, "rgba(29, 78, 216, 0.75)"), # Medium blue
            (max_depth, "rgba(30, 27, 75, 0.92)")     # Dark indigo (deep/extreme)
        ]

    @staticmethod
    def compile_hillshade_overlay(
        elevation: np.ndarray,
        hillshade: np.ndarray
    ) -> np.ndarray:
        """
        Combines raw elevations and hillshade grids into a styled RGB raster overlay.
        """
        # Diagnostic visualization processing helper
        # Normalise elevation to [0, 255]
        elev_norm = (elevation - elevation.min()) / max(elevation.max() - elevation.min(), 1.0)
        elev_byte = (elev_norm * 255).astype(np.uint8)
        
        # Merge elevation (green/red scale) with hillshade shading (intensity)
        # Returns an RGB image array (height, width, 3)
        h, w = elevation.shape
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        rgba[..., 0] = elev_byte                # Red channel
        rgba[..., 1] = 255 - elev_byte          # Green channel
        rgba[..., 2] = hillshade                # Blue channel (hillshade shading)
        rgba[..., 3] = 255                      # Opacity
        return rgba
