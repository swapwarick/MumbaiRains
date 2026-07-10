"""
simulation/drainage_interface/engine.py
----------------------------------------
DrainageInterfaceEngine connecting surface flow cells to sub-surface drain inlets.
"""

from typing import List, Dict, Any, Tuple, Optional
import numpy as np

from .types import DrainInlet
from .reports import DrainageInterfaceReport


class DrainageInterfaceEngine:
    """
    Manages the interaction between surface water depth grid and sub-surface inlets.
    Handles DEM-to-inlet cell mapping via KDTree and computes volumetric intake.
    """
    def __init__(self, inlets: List[DrainInlet], max_search_radius_m: float = 100.0) -> None:
        """
        Args:
            inlets: List of DrainInlet objects.
            max_search_radius_m: Configurable maximum distance (m) to associate a cell with an inlet.
        """
        self.inlets = {inlet.id: inlet for inlet in inlets}
        self.max_search_radius = float(max_search_radius_m)
        
        # Mapping attributes
        self.rows = 0
        self.cols = 0
        self.transform: List[float] = []
        self.inlet_lookup: Optional[np.ndarray] = None  # 2D string/object array of inlet IDs or None
        self.coverage_percentage = 0.0
        self.avg_spacing_m = 0.0

    def associate_grid(self, rows: int, cols: int, transform: List[float]) -> np.ndarray:
        """
        Maps every DEM cell (row, col) to the nearest drainage inlet within max_search_radius_m.
        Uses SciPy's KDTree for performance.
        
        Args:
            rows: Grid rows.
            cols: Grid columns.
            transform: Affine transform array [dx, 0, x0, 0, dy, y0].
            
        Returns:
            inlet_lookup: 2D object array of associated inlet IDs (empty string if no inlet nearby).
        """
        self.rows = rows
        self.cols = cols
        self.transform = transform
        
        if not self.inlets:
            self.inlet_lookup = np.full((rows, cols), "", dtype=object)
            self.coverage_percentage = 0.0
            self.avg_spacing_m = 0.0
            return self.inlet_lookup

        # 1. Compute spatial coordinates of all inlets
        inlet_list = list(self.inlets.values())
        inlet_ids = [inlet.id for inlet in inlet_list]
        
        # Calculate real-world coordinates for inlets based on their row, col
        # (Using grid transform to match cell center or node origin)
        inlet_coords = []
        for inlet in inlet_list:
            x = transform[2] + inlet.col * transform[0] + inlet.row * transform[1]
            y = transform[5] + inlet.col * transform[3] + inlet.row * transform[4]
            inlet_coords.append((x, y))
        inlet_coords = np.array(inlet_coords)  # shape: (M, 2)
        
        # Calculate average inlet spacing
        self.avg_spacing_m = self._calculate_avg_spacing(inlet_coords)

        # 2. Build grid cell coordinates
        c_coords, r_coords = np.meshgrid(np.arange(cols), np.arange(rows))
        x_grid = transform[2] + c_coords * transform[0] + r_coords * transform[1]
        y_grid = transform[5] + c_coords * transform[3] + r_coords * transform[4]
        grid_points = np.stack([x_grid.flatten(), y_grid.flatten()], axis=1)  # shape: (N, 2)

        # 3. Query nearest inlet via KDTree
        try:
            from scipy.spatial import KDTree
            kdtree = KDTree(inlet_coords)
            distances, indices = kdtree.query(grid_points)
        except ImportError:
            # Fallback chunked numpy distance broadcast
            num_points = grid_points.shape[0]
            distances = np.zeros(num_points, dtype=np.float32)
            indices = np.zeros(num_points, dtype=np.int32)
            chunk_size = 1000
            for i in range(0, num_points, chunk_size):
                end = min(i + chunk_size, num_points)
                diff = grid_points[i:end, None, :] - inlet_coords[None, :, :]
                dist_sq = np.sum(diff ** 2, axis=2)
                indices[i:end] = np.argmin(dist_sq, axis=1)
                distances[i:end] = np.sqrt(np.min(dist_sq, axis=1))

        # 4. Associate cell with inlet ID if within search radius
        associated_inlets = []
        for dist, idx in zip(distances, indices):
            if dist <= self.max_search_radius:
                associated_inlets.append(inlet_ids[idx])
            else:
                associated_inlets.append("")

        self.inlet_lookup = np.array(associated_inlets, dtype=object).reshape((rows, cols))
        
        # Coverage percentage: cells with associated inlet / total cells
        covered_cells = np.sum(self.inlet_lookup != "")
        self.coverage_percentage = float(covered_cells / (rows * cols) * 100.0)
        
        return self.inlet_lookup

    def _calculate_avg_spacing(self, coords: np.ndarray) -> float:
        if len(coords) < 2:
            return 0.0
        try:
            from scipy.spatial import KDTree
            tree = KDTree(coords)
            # Find nearest neighbor for each coordinate (excluding itself: k=2)
            dist, _ = tree.query(coords, k=2)
            return float(np.mean(dist[:, 1]))
        except ImportError:
            # Fallback simple distance matrix
            diff = coords[:, None, :] - coords[None, :, :]
            dists = np.sqrt(np.sum(diff ** 2, axis=2))
            # Set diagonal to infinity
            np.fill_diagonal(dists, np.inf)
            return float(np.mean(np.min(dists, axis=1)))

    def apply_inlet_intake(
        self,
        water_depth_grid: np.ndarray,
        cell_area: float,
        dt: float
    ) -> Tuple[np.ndarray, Dict[str, float], np.ndarray]:
        """
        Accepts surface water into the inlets up to their maximum capacity.
        Drains the surface water grid and reports intake volumes.
        
        Args:
            water_depth_grid: 2D array of current surface water depths (m).
            cell_area: Isotropic cell area (m^2).
            dt: Timestep duration (seconds).
            
        Returns:
            updated_depth_grid: 2D array of updated water depths after drainage.
            intake_report: Dict mapping inlet ID to intake volume (m^3).
            overflow_grid: 2D array representing remaining water depth (m).
        """
        if self.inlet_lookup is None:
            raise ValueError("Grid mapping not initialized. Call associate_grid() first.")
            
        updated_depth = water_depth_grid.copy().astype(np.float32)
        intake_report = {inlet_id: 0.0 for inlet_id in self.inlets}
        
        # Group cells by inlet ID to respect maximum inlet capacity
        # Loop through inlets to avoid cell-by-cell loops
        for inlet_id, inlet in self.inlets.items():
            if inlet.blocked:
                continue
                
            # Cells associated with this inlet
            mask = (self.inlet_lookup == inlet_id)
            if not np.any(mask):
                continue
                
            # Available volume in these cells (m^3)
            available_depths = updated_depth[mask]
            available_vol = float(np.sum(available_depths) * cell_area)
            
            if available_vol <= 0:
                continue
                
            # Max intake capacity of inlet for this step (m^3)
            step_capacity = inlet.capacity_m3_s * dt
            
            # Actual intake volume
            actual_intake_vol = min(available_vol, step_capacity)
            intake_report[inlet_id] = actual_intake_vol
            
            # Drain cells proportionally to their depth
            drain_fraction = actual_intake_vol / available_vol
            updated_depth[mask] -= available_depths * drain_fraction
            
        # Protect against precision errors
        updated_depth = np.maximum(updated_depth, 0.0)
        
        return updated_depth, intake_report, updated_depth

    def get_statistics(self, timestep: int) -> DrainageInterfaceReport:
        """Produces inlet statistics report for the current timestep."""
        total = len(self.inlets)
        blocked = sum(1 for inlet in self.inlets.values() if inlet.blocked)
        active = total - blocked
        total_capacity = sum(inlet.capacity_m3_s for inlet in self.inlets.values())
        
        return DrainageInterfaceReport(
            timestep=timestep,
            total_inlets=total,
            active_inlets=active,
            blocked_inlets=blocked,
            total_capacity_m3_s=total_capacity,
            total_intake_m3=0.0,  # Updated dynamically during simulation steps
            coverage_percentage=self.coverage_percentage,
            avg_spacing_m=self.avg_spacing_m
        )
