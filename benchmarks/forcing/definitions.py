"""
benchmarks/forcing/definitions.py
----------------------------------
Definitions and analytical verification keys for Sprint 4 forcing benchmarks.
"""

from typing import Dict, Any, Tuple
import numpy as np


def get_forcing_benchmark(name: str, rows: int = 10, cols: int = 10, dx: float = 10.0) -> Dict[str, Any]:
    """
    Returns benchmark parameters, inputs, and analytical keys for forcing verification.
    
    Args:
        name: Name of forcing benchmark ("uniform_rain", "point_source", "area_source", "multiple_sources").
        rows: Grid row dimension.
        cols: Grid column dimension.
        dx: Cell size in meters.
        
    Returns:
        benchmark_dict: Dictionary containing analytical inputs and expected metrics.
    """
    name_lower = name.lower().strip()
    cell_area = dx * dx
    grid_area = rows * cols * cell_area

    if name_lower == "uniform_rain":
        # 50 mm/hr rainfall over 1 hour (3600 seconds)
        intensity = 50.0
        duration = 3600.0
        expected_added_volume = (intensity / 1000.0) * grid_area  # 50 mm = 0.05m * grid_area
        expected_water_depth = 0.05  # m
        
        return {
            "name": "uniform_rain",
            "intensity_mm_hr": intensity,
            "duration_seconds": duration,
            "expected_added_volume": expected_added_volume,
            "expected_water_depth": expected_water_depth,
            "expected_conservation_error": 1e-6
        }

    elif name_lower == "point_source":
        # Point source of 2.5 m^3/s at cell (5, 5) for 10 seconds
        discharge = 2.5
        duration = 10.0
        row, col = 5, 5
        expected_added_volume = discharge * duration  # 25 m^3
        
        # Depth in single cell: 25.0 / cell_area
        expected_cell_depth = 25.0 / cell_area
        
        return {
            "name": "point_source",
            "discharge_m3_s": discharge,
            "duration_seconds": duration,
            "row": row,
            "col": col,
            "expected_added_volume": expected_added_volume,
            "expected_cell_depth": expected_cell_depth,
            "expected_conservation_error": 1e-6
        }

    elif name_lower == "area_source":
        # Area source over a 4x4 center patch (rows 3:7, cols 3:7)
        # Inflow rate of 10.0 m^3/s for 20 seconds
        discharge = 10.0
        duration = 20.0
        mask = np.zeros((rows, cols), dtype=bool)
        mask[3:7, 3:7] = True
        num_cells = np.sum(mask)
        expected_added_volume = discharge * duration  # 200 m^3
        
        # Depth per cell in mask: 200.0 / (num_cells * cell_area)
        expected_cell_depth = 200.0 / (num_cells * cell_area)
        
        return {
            "name": "area_source",
            "discharge_m3_s": discharge,
            "duration_seconds": duration,
            "mask": mask,
            "expected_added_volume": expected_added_volume,
            "expected_cell_depth": expected_cell_depth,
            "expected_conservation_error": 1e-6
        }

    elif name_lower == "multiple_sources":
        # Simulates multiple inputs:
        # 1. uniform rain of 20 mm/hr for 60 seconds
        # 2. point source of 1.5 m^3/s at (2, 2) for 60 seconds
        # 3. area source of 5.0 m^3/s at rows 7:9, cols 7:9 for 60 seconds
        rain_intensity = 20.0
        point_discharge = 1.5
        point_row, point_col = 2, 2
        area_discharge = 5.0
        area_mask = np.zeros((rows, cols), dtype=bool)
        area_mask[7:9, 7:9] = True
        
        duration = 60.0
        
        vol_rain = (rain_intensity / 1000.0 / 3600.0 * duration) * grid_area
        vol_point = point_discharge * duration
        vol_area = area_discharge * duration
        
        expected_added_volume = vol_rain + vol_point + vol_area
        
        return {
            "name": "multiple_sources",
            "rain_intensity": rain_intensity,
            "point_discharge": point_discharge,
            "point_row": point_row,
            "point_col": point_col,
            "area_discharge": area_discharge,
            "area_mask": area_mask,
            "duration_seconds": duration,
            "expected_added_volume": expected_added_volume,
            "expected_conservation_error": 1e-6
        }
    else:
        raise ValueError(f"Unknown forcing benchmark: {name}")
