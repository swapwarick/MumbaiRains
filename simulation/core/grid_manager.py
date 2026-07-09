"""
simulation/core/grid_manager.py
-------------------------------
GridManager handles grid definitions, cell mappings, spatial transformations,
raster indexing, coordinate conversions, and neighbour lookups.
It is the sole class responsible for loading and querying raster data.
"""

from typing import Dict, Any, List, Tuple, Optional
import numpy as np

from backend.utils import get_logger
from backend.config import settings
from backend.exceptions import TerrainException
from simulation.core.cell import Cell
from simulation.terrain.loader import load_dem

logger = get_logger(__name__)


class GridManager:
    """
    Manages the computational grid and acts as the gatekeeper to all cell states.
    Converts between spatial coordinates (latitude/longitude) and raster grid indices.
    """
    def __init__(self) -> None:
        self.elevation: Optional[np.ndarray] = None
        self.meta: Optional[Dict[str, Any]] = None
        self.rows: int = 0
        self.cols: int = 0
        self.transform: List[float] = []
        self.grid: Optional[List[List[Cell]]] = None

    def initialize_grid(
        self,
        dem_path: str,
        land_cover_types: Optional[np.ndarray] = None,
        roughness_coefficients: Optional[np.ndarray] = None,
        building_masks: Optional[np.ndarray] = None,
        road_masks: Optional[np.ndarray] = None,
        river_masks: Optional[np.ndarray] = None,
        soil_types: Optional[np.ndarray] = None
    ) -> None:
        """
        Loads the DEM raster and constructs the Cell grid.

        Args:
            dem_path: Path to the GeoTIFF DEM file.
            land_cover_types: Optional classification array.
            roughness_coefficients: Optional Manning's n array.
            building_masks: Optional building footprint array.
            road_masks: Optional road centerline array.
            river_masks: Optional river mask array.
            soil_types: Optional soil classification array.
        """
        # 1. Load DEM
        self.elevation, self.meta = load_dem(dem_path)
        self.rows, self.cols = self.elevation.shape
        self.transform = self.meta["transform"]

        # Initialize optional arrays if not provided
        lc = land_cover_types if land_cover_types is not None else np.full(self.elevation.shape, "concrete", dtype=object)
        n = roughness_coefficients if roughness_coefficients is not None else np.full(self.elevation.shape, settings.default_cn, dtype=np.float32)
        b_mask = building_masks if building_masks is not None else np.zeros(self.elevation.shape, dtype=bool)
        rd_mask = road_masks if road_masks is not None else np.zeros(self.elevation.shape, dtype=bool)
        rv_mask = river_masks if river_masks is not None else np.zeros(self.elevation.shape, dtype=bool)
        soil = soil_types if soil_types is not None else np.full(self.elevation.shape, "C", dtype=object)
        
        # Default drain capacity (e.g. 0.05 m3/s per cell inlet)
        drain_cap = np.full(self.elevation.shape, 0.05, dtype=np.float32)

        # 2. Build 2D grid of Cells
        temp_grid: List[List[Cell]] = []
        for r in range(self.rows):
            row_cells: List[Cell] = []
            for c in range(self.cols):
                cell = Cell(
                    row=r,
                    col=c,
                    elevation=float(self.elevation[r, c]),
                    land_cover=str(lc[r, c]),
                    surface_roughness=float(n[r, c]),
                    building_mask=bool(b_mask[r, c]),
                    road_mask=bool(rd_mask[r, c]),
                    river_mask=bool(rv_mask[r, c]),
                    drain_capacity=float(drain_cap[r, c]),
                    soil_type=str(soil[r, c])
                )
                row_cells.append(cell)
            temp_grid.append(row_cells)
        
        self.grid = temp_grid
        logger.info(
            "Grid cells initialized",
            extra={"rows": self.rows, "cols": self.cols, "total_cells": self.rows * self.cols}
        )

    def get_cell(self, row: int, col: int) -> Cell:
        """
        Retrieves a Cell by its row and column indices.

        Args:
            row: Row index.
            col: Column index.

        Returns:
            The Cell instance.
        """
        if self.grid is None:
            raise TerrainException("Grid has not been initialized.")
        if not (0 <= row < self.rows and 0 <= col < self.cols):
            raise IndexError(f"Cell index ({row}, {col}) out of range (0-{self.rows-1}, 0-{self.cols-1}).")
        return self.grid[row][col]

    def get_cell_by_coords(self, lon: float, lat: float) -> Cell:
        """
        Retrieves a Cell using geospatial latitude and longitude.

        Args:
            lon: Longitude in decimal degrees.
            lat: Latitude in decimal degrees.

        Returns:
            The Cell instance matching the coordinates.
        """
        row, col = self.coords_to_index(lon, lat)
        return self.get_cell(row, col)

    def coords_to_index(self, lon: float, lat: float) -> Tuple[int, int]:
        """
        Converts WGS-84 longitude and latitude to grid row and column.
        Uses GDAL/rasterio affine transformation coefficients:
        x_pixel = (lon - transform[2]) / transform[0]
        y_pixel = (lat - transform[5]) / transform[4]
        
        Args:
            lon: Longitude.
            lat: Latitude.

        Returns:
            A tuple of (row, col).
        """
        if not self.transform:
            raise TerrainException("Grid transform coefficients are not set.")

        dx, _, lon_start, _, dy, lat_start = self.transform
        col = int((lon - lon_start) / dx)
        row = int((lat - lat_start) / dy)

        # Clamp to grid bounds
        col = max(0, min(col, self.cols - 1))
        row = max(0, min(row, self.rows - 1))
        return row, col

    def index_to_coords(self, row: int, col: int) -> Tuple[float, float]:
        """
        Converts grid row and column to geospatial center coordinates (longitude, latitude).

        Args:
            row: Grid row index.
            col: Grid column index.

        Returns:
            A tuple of (lon, lat) representing the cell center.
        """
        if not self.transform:
            raise TerrainException("Grid transform coefficients are not set.")

        dx, _, lon_start, _, dy, lat_start = self.transform
        # Center of pixel offset by 0.5
        lon = lon_start + (col + 0.5) * dx
        lat = lat_start + (row + 0.5) * dy
        return lon, lat

    def get_neighbours(self, row: int, col: int, connectivity: int = 4) -> List[Cell]:
        """
        Returns neighbouring cells for lookup.

        Args:
            row: Row index.
            col: Column index.
            connectivity: 4-connected (N, S, E, W) or 8-connected (includes diagonals).

        Returns:
            A list of neighbouring Cell instances.
        """
        if self.grid is None:
            raise TerrainException("Grid has not been initialized.")

        offsets = []
        if connectivity == 4:
            offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        elif connectivity == 8:
            offsets = [
                (-1, 0), (1, 0), (0, -1), (0, 1),
                (-1, -1), (-1, 1), (1, -1), (1, 1)
            ]
        else:
            raise ValueError("Connectivity must be 4 or 8.")

        neighbours = []
        for dr, dc in offsets:
            nr, nc = row + dr, col + dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                neighbours.append(self.grid[nr][nc])
        return neighbours

    def extract_window(self, start_row: int, end_row: int, start_col: int, end_col: int) -> List[List[Cell]]:
        """
        Extracts a subset window of the computational grid.

        Args:
            start_row: Start row index (inclusive).
            end_row: End row index (exclusive).
            start_col: Start col index (inclusive).
            end_col: End col index (exclusive).

        Returns:
            A 2D list of Cell instances.
        """
        if self.grid is None:
            raise TerrainException("Grid has not been initialized.")

        # Clip values to bounds
        s_r = max(0, start_row)
        e_r = min(end_row, self.rows)
        s_c = max(0, start_col)
        e_c = min(end_col, self.cols)

        return [row[s_c:e_c] for row in self.grid[s_r:e_r]]

    def partition_grid(self, num_partitions_x: int, num_partitions_y: int) -> List[Dict[str, Any]]:
        """
        Partitions the grid into sub-windows for parallel or windowed processing stubs.

        Args:
            num_partitions_x: Number of divisions along X axis (cols).
            num_partitions_y: Number of divisions along Y axis (rows).

        Returns:
            A list of dictionary descriptors representing partitions (start_row, end_row, etc.).
        """
        partitions = []
        row_step = self.rows // num_partitions_y
        col_step = self.cols // num_partitions_x

        for py in range(num_partitions_y):
            s_r = py * row_step
            e_r = (py + 1) * row_step if py < num_partitions_y - 1 else self.rows
            for px in range(num_partitions_x):
                s_c = px * col_step
                e_c = (px + 1) * col_step if px < num_partitions_x - 1 else self.cols
                partitions.append({
                    "partition_id": f"P_x{px}_y{py}",
                    "start_row": s_r,
                    "end_row": e_r,
                    "start_col": s_c,
                    "end_col": e_c,
                    "rows": e_r - s_r,
                    "cols": e_c - s_c
                })
        return partitions
