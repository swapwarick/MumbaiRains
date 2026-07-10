"""
simulation/routing/benchmarks.py
---------------------------------
Benchmark datasets and verification criteria for the SurfaceRoutingEngine (Sprint 3).
Includes tests for flat, uniform slope, diagonal slope, pits, barriers, and boundaries.
"""

from typing import Dict, Any, Tuple
import numpy as np


def create_routing_benchmark(name: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Creates a benchmark routing scenario.
    
    Args:
        name: Name of the benchmark ("flat_pool", "uniform_slope", "diagonal_slope",
              "single_barrier", "pit", "ridge", "open_boundary", "closed_boundary").
              
    Returns:
        elevation: 2D float32 array
        downstream_cells: 3D int32 array of shape (rows, cols, 2)
        initial_water_depth: 2D float32 array
        metadata: dictionary with validation info and parameters
    """
    name_lower = name.lower().strip()
    rows, cols = 10, 10
    
    # Grid coordinate helper meshes
    r_coords, c_coords = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")
    
    if name_lower == "flat_pool":
        elevation = np.full((rows, cols), 5.0, dtype=np.float32)
        # All cells are sinks, so they point to themselves
        downstream_cells = np.stack([r_coords, c_coords], axis=-1).astype(np.int32)
        
        initial_water_depth = np.zeros((rows, cols), dtype=np.float32)
        initial_water_depth[3:7, 3:7] = 1.0  # pool in center
        
        meta = {
            "name": "flat_pool",
            "boundary": "closed",
            "dx": 10.0,
            "dt": 1.0,
            "steps": 10,
            "expected_behavior": "Water remains stationary in the center pool.",
            "validate_fn": lambda init, final, reports: np.allclose(init, final)
        }
        return elevation, downstream_cells, initial_water_depth, meta
        
    elif name_lower == "uniform_slope":
        # Slope decreasing North to South
        elevation = np.zeros((rows, cols), dtype=np.float32)
        for r in range(rows):
            elevation[r, :] = 10.0 - r * 1.0
            
        # Point South (row + 1, col)
        downstream_r = np.clip(r_coords + 1, 0, rows - 1)
        downstream_c = c_coords.copy()
        # Bottom row are sinks
        downstream_r[-1, :] = rows - 1
        downstream_cells = np.stack([downstream_r, downstream_c], axis=-1).astype(np.int32)
        
        initial_water_depth = np.zeros((rows, cols), dtype=np.float32)
        initial_water_depth[0:3, :] = 1.0  # water at top 3 rows
        
        meta = {
            "name": "uniform_slope",
            "boundary": "closed",
            "dx": 10.0,
            "dt": 2.0,
            "steps": 20,
            "expected_behavior": "Water flows South and accumulates on the bottom row.",
            "validate_fn": lambda init, final, reports: (
                np.sum(final[0:3, :]) < 2.0 and
                np.sum(final[-2:, :]) > np.sum(init) * 0.15
            )
        }
        return elevation, downstream_cells, initial_water_depth, meta

    elif name_lower == "diagonal_slope":
        # Slope decreasing North-West to South-East
        elevation = np.zeros((rows, cols), dtype=np.float32)
        for r in range(rows):
            for c in range(cols):
                elevation[r, c] = 20.0 - (r + c)
                
        # Point South-East (row + 1, col + 1)
        downstream_r = np.clip(r_coords + 1, 0, rows - 1)
        downstream_c = np.clip(c_coords + 1, 0, cols - 1)
        # Bottom-right corner (9,9) is sink
        downstream_r[-1, -1] = rows - 1
        downstream_c[-1, -1] = cols - 1
        
        downstream_cells = np.stack([downstream_r, downstream_c], axis=-1).astype(np.int32)
        
        initial_water_depth = np.zeros((rows, cols), dtype=np.float32)
        initial_water_depth[0:2, 0:2] = 2.0  # water at top-left corner
        
        meta = {
            "name": "diagonal_slope",
            "boundary": "closed",
            "dx": 10.0,
            "dt": 1.0,
            "steps": 25,
            "expected_behavior": "Water flows diagonally to the bottom-right corner and pools there.",
            "validate_fn": lambda init, final, reports: (
                np.sum(final[0:3, 0:3]) < 0.5 and  # Top-left has drained
                final[-1, -1] > 1.0               # Water accumulated at bottom-right corner
            )
        }
        return elevation, downstream_cells, initial_water_depth, meta

    elif name_lower == "single_barrier":
        # Slope Southwards, but row 5 is a high barrier
        elevation = np.zeros((rows, cols), dtype=np.float32)
        for r in range(rows):
            elevation[r, :] = 10.0 - r * 1.0
        elevation[5, :] = 15.0  # barrier
        
        # D8 target routing:
        # Rows 0-4 flow South to row 4 (which is a sink because row 5 is higher)
        # Row 5 flows South to row 6
        # Rows 6-9 flow South to bottom row 9 (sink)
        downstream_r = r_coords.copy()
        downstream_c = c_coords.copy()
        for r in range(rows):
            if r < 4:
                downstream_r[r, :] = r + 1
            elif r == 4:
                downstream_r[r, :] = r  # sink behind barrier
            elif r == 5:
                downstream_r[r, :] = r + 1
            elif r > 5 and r < rows - 1:
                downstream_r[r, :] = r + 1
            elif r == rows - 1:
                downstream_r[r, :] = r
        downstream_cells = np.stack([downstream_r, downstream_c], axis=-1).astype(np.int32)
        
        initial_water_depth = np.zeros((rows, cols), dtype=np.float32)
        initial_water_depth[0:3, :] = 1.0  # water at top
        
        meta = {
            "name": "single_barrier",
            "boundary": "closed",
            "dx": 10.0,
            "dt": 2.0,
            "steps": 20,
            "expected_behavior": "Water flows South and pools behind the barrier at row 4.",
            "validate_fn": lambda init, final, reports: (
                np.sum(final[5:, :]) == 0.0 and  # No water crossed the barrier
                np.sum(final[4, :]) > np.sum(init) * 0.8  # Pools at row 4
            )
        }
        return elevation, downstream_cells, initial_water_depth, meta

    elif name_lower == "pit":
        # Flat surface with a deep pit in center (5, 5)
        elevation = np.full((rows, cols), 5.0, dtype=np.float32)
        elevation[5, 5] = 0.0
        
        # Point towards (5, 5)
        downstream_r = r_coords.copy()
        downstream_c = c_coords.copy()
        for r in range(rows):
            for c in range(cols):
                if r == 5 and c == 5:
                    continue
                downstream_r[r, c] = r + np.sign(5 - r)
                downstream_c[r, c] = c + np.sign(5 - c)
        downstream_cells = np.stack([downstream_r, downstream_c], axis=-1).astype(np.int32)
        
        initial_water_depth = np.zeros((rows, cols), dtype=np.float32)
        initial_water_depth[3:8, 3:8] = 0.5
        initial_water_depth[5, 5] = 0.0
        
        meta = {
            "name": "pit",
            "boundary": "closed",
            "dx": 10.0,
            "dt": 1.0,
            "steps": 15,
            "expected_behavior": "Water drains from surrounding cells and pools in the center pit.",
            "validate_fn": lambda init, final, reports: (
                final[5, 5] > 1.0 and
                np.allclose(np.sum(final), np.sum(init))
            )
        }
        return elevation, downstream_cells, initial_water_depth, meta

    elif name_lower == "ridge":
        # Central peak ridge along col 5
        elevation = np.zeros((rows, cols), dtype=np.float32)
        for c in range(cols):
            elevation[:, c] = 10.0 - abs(c - 5) * 2.0
            
        # Point away from col 5
        downstream_r = r_coords.copy()
        downstream_c = c_coords.copy()
        for c in range(cols):
            if c < 5:
                downstream_c[:, c] = c - 1  # West
            elif c > 5:
                downstream_c[:, c] = c + 1  # East
            else:
                downstream_c[:, c] = c - 1  # Ridge peak splits West
        # Edge columns are sinks
        downstream_c[:, 0] = 0
        downstream_c[:, -1] = cols - 1
        
        downstream_cells = np.stack([downstream_r, downstream_c], axis=-1).astype(np.int32)
        
        initial_water_depth = np.zeros((rows, cols), dtype=np.float32)
        initial_water_depth[:, 5] = 2.0  # water on ridge peak
        
        meta = {
            "name": "ridge",
            "boundary": "closed",
            "dx": 10.0,
            "dt": 1.0,
            "steps": 10,
            "expected_behavior": "Water flows away from the central ridge to both boundaries.",
            "validate_fn": lambda init, final, reports: (
                np.sum(final[:, 5]) < 1.5 and
                np.sum(final[:, 0]) > 0.0
            )
        }
        return elevation, downstream_cells, initial_water_depth, meta

    elif name_lower == "open_boundary":
        # Uniform slope South, but D8 downstream_r points off-grid on row 9
        elevation = np.zeros((rows, cols), dtype=np.float32)
        for r in range(rows):
            elevation[r, :] = 10.0 - r * 1.0
            
        # Points South (row + 1, col). On bottom row, points to row 10 (off-grid)
        downstream_r = r_coords + 1
        downstream_c = c_coords.copy()
        downstream_cells = np.stack([downstream_r, downstream_c], axis=-1).astype(np.int32)
        
        initial_water_depth = np.full((rows, cols), 1.0, dtype=np.float32)
        
        meta = {
            "name": "open_boundary",
            "boundary": "open",
            "dx": 10.0,
            "dt": 2.0,
            "steps": 30,
            "expected_behavior": "Water drains off the southern open boundary, reducing total volume.",
            "validate_fn": lambda init, final, reports: (
                np.sum(final) < np.sum(init) * 0.5 and
                reports[-1].boundary_outflow > 0.0
            )
        }
        return elevation, downstream_cells, initial_water_depth, meta

    elif name_lower == "closed_boundary":
        # Uniform slope South, but D8 downstream_r points off-grid on row 9
        elevation = np.zeros((rows, cols), dtype=np.float32)
        for r in range(rows):
            elevation[r, :] = 10.0 - r * 1.0
            
        # Points South (row + 1, col). On bottom row, points to row 10 (off-grid)
        downstream_r = r_coords + 1
        downstream_c = c_coords.copy()
        downstream_cells = np.stack([downstream_r, downstream_c], axis=-1).astype(np.int32)
        
        initial_water_depth = np.full((rows, cols), 1.0, dtype=np.float32)
        
        meta = {
            "name": "closed_boundary",
            "boundary": "closed",
            "dx": 10.0,
            "dt": 2.0,
            "steps": 30,
            "expected_behavior": "Water drains South but is blocked by the closed boundary.",
            "validate_fn": lambda init, final, reports: (
                np.allclose(np.sum(final), np.sum(init)) and
                np.sum(final[-1, :]) > np.sum(init[-1, :])
            )
        }
        return elevation, downstream_cells, initial_water_depth, meta

    else:
        raise ValueError(f"Unknown routing benchmark: {name}")
