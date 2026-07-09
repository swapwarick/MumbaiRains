"""
simulation/gis/layers.py
------------------------
Implements the abstraction layer for GIS datasets:
- LayerMetadata (Strongly typed dataclass for layer metadata)
- BaseLayer (Abstract base class for all spatial layers)
- RasterLayer (Represents grid-based elevation or index datasets)
- VectorLayer (Represents vector features like roads, buildings, waterways)

References:
1. OSGeo/GDAL Data Model specifications.
2. Shapely and Rasterio geometry standard conventions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
import os
from typing import Dict, Any, Tuple, List, Optional
import numpy as np

from simulation.gis.validation import ValidationReport

try:
    import rasterio
    from rasterio.windows import from_bounds
    _RASTERIO = True
except ImportError:
    _RASTERIO = False

try:
    from shapely.geometry import shape as shapely_shape
    from shapely.validation import explain_validity
    from shapely.strtree import STRtree
    _SHAPELY = True
except ImportError:
    _SHAPELY = False


@dataclass
class LayerMetadata:
    """
    Strongly typed metadata model for spatial layers.
    """
    name: str
    description: str
    source: str
    crs: str
    extent: Tuple[float, float, float, float]  # (xmin, ymin, xmax, ymax)
    resolution: Tuple[float, float]
    bands: int
    dtype: str
    nodata: Optional[float]
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class BaseLayer(ABC):
    """
    Abstract Base Class representing a spatial GIS dataset layer.
    """
    def __init__(self, name: str, crs: str, bounds: Tuple[float, float, float, float]) -> None:
        """
        Initializes a base GIS layer.

        Args:
            name: Layer identifier name.
            crs: Coordinate Reference System string (e.g. 'EPSG:4326').
            bounds: Bounding box as (xmin, ymin, xmax, ymax).
        """
        self.name: str = name
        self.crs: str = crs
        self.bounds: Tuple[float, float, float, float] = bounds  # xmin, ymin, xmax, ymax
        self.metadata: Optional[LayerMetadata] = None

    @abstractmethod
    def validate(self) -> ValidationReport:
        """
        Runs validation checks on the layer data and returns a ValidationReport.
        """
        pass


class RasterLayer(BaseLayer):
    """
    Represents a grid-based spatial dataset (e.g. DEM GeoTIFF).
    Supports windowed reading and dynamic tile rendering without loading the entire raster.
    """
    def __init__(
        self,
        name: str,
        crs: str,
        bounds: Tuple[float, float, float, float],
        shape: Tuple[int, int],
        transform: List[float],
        resolution: Tuple[float, float],
        nodata: Optional[float] = None,
        file_path: Optional[str] = None
    ) -> None:
        super().__init__(name, crs, bounds)
        self.shape: Tuple[int, int] = shape  # (rows, cols)
        self.transform: List[float] = transform  # Affine transform coefficients
        self.resolution: Tuple[float, float] = resolution  # (dx, dy)
        self.nodata: Optional[float] = nodata
        self.file_path: Optional[str] = file_path
        self._cached_statistics: Dict[int, Dict[str, float]] = {}

    @property
    def band_count(self) -> int:
        """Returns the number of bands in the raster file."""
        if not self.file_path:
            return 1
        if not _RASTERIO:
            return 1
        with rasterio.open(self.file_path) as src:
            return int(src.count)

    def read_band(self, band_idx: int = 1) -> np.ndarray:
        """
        Reads a single full band from the raster dataset.
        """
        if not self.file_path or not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Raster back-file missing: {self.file_path}")
        if not _RASTERIO:
            raise ImportError("rasterio is required to read raster bands.")
        with rasterio.open(self.file_path) as src:
            return src.read(band_idx).astype(np.float32)

    def read_bands(self, band_indices: List[int]) -> np.ndarray:
        """
        Reads multiple bands from the raster dataset.
        """
        if not self.file_path or not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Raster back-file missing: {self.file_path}")
        if not _RASTERIO:
            raise ImportError("rasterio is required to read raster bands.")
        with rasterio.open(self.file_path) as src:
            return src.read(band_indices).astype(np.float32)

    def read_window(self, window_bounds: Tuple[float, float, float, float], band_idx: int = 1) -> np.ndarray:
        """
        Reads a subset window of the raster from disk using bounding coordinates.
        Never loads the whole raster unless requested.

        Args:
            window_bounds: Bounding box coordinates (xmin, ymin, xmax, ymax) to extract.
            band_idx: Index of the band to read.

        Returns:
            A 2D NumPy array containing the windowed cell values.
        """
        if not self.file_path:
            raise ValueError(f"Raster layer '{self.name}' is not backed by a file on disk.")

        if not _RASTERIO:
            raise ImportError("rasterio is required for windowed reading of raster files.")

        from rasterio.windows import from_bounds
        xmin, ymin, xmax, ymax = window_bounds
        with rasterio.open(self.file_path) as src:
            # Calculate window using rasterio helper
            window = from_bounds(xmin, ymin, xmax, ymax, src.transform)
            # Read only the windowed grid block
            data = src.read(band_idx, window=window).astype(np.float32)
            return data

    def read_tile(self, tile_x: int, tile_y: int, zoom: int, tile_size: int = 256, band_idx: int = 1) -> np.ndarray:
        """
        Reads a specific tile using XYZ web mapping coordinate windows.
        Converts XYZ tile coords to bounds, and reads that window.
        """
        # Calculate Web Mercator bounds of tile
        # Earth radius constant: 6378137.0
        initial_resolution = 2.0 * np.pi * 6378137.0 / tile_size
        res = initial_resolution / (2 ** zoom)
        tile_merc_size = res * tile_size
        
        xmin_m = -np.pi * 6378137.0 + tile_x * tile_merc_size
        xmax_m = xmin_m + tile_merc_size
        ymax_m = np.pi * 6378137.0 - tile_y * tile_merc_size
        ymin_m = ymax_m - tile_merc_size
        
        # Convert mercator to WGS-84
        def _to_wgs84(x: float, y: float) -> Tuple[float, float]:
            lon = (x / (np.pi * 6378137.0)) * 180.0
            lat = (y / (np.pi * 6378137.0)) * 180.0
            lat = 180.0 / np.pi * (2.0 * np.arctan(np.exp(lat * np.pi / 180.0)) - np.pi / 2.0)
            return lon, lat
            
        lon_min, lat_min = _to_wgs84(xmin_m, ymin_m)
        lon_max, lat_max = _to_wgs84(xmax_m, ymax_m)
        
        tile_bounds_wgs84 = (lon_min, lat_min, lon_max, lat_max)
        
        # If raster is EPSG:4326, we can read directly using these geographic bounds
        # Clip to raster bounds to avoid reading outside of extent
        xmin, ymin, xmax, ymax = self.bounds
        clip_xmin = max(lon_min, xmin)
        clip_xmax = min(lon_max, xmax)
        clip_ymin = max(lat_min, ymin)
        clip_ymax = min(lat_max, ymax)
        
        if clip_xmin >= clip_xmax or clip_ymin >= clip_ymax:
            # Entirely out of bounds
            return np.full((tile_size, tile_size), self.nodata or 0.0, dtype=np.float32)
            
        window_data = self.read_window((clip_xmin, clip_ymin, clip_xmax, clip_ymax), band_idx)
        return window_data

    def statistics(self, band_idx: int = 1, grid_data: Optional[np.ndarray] = None) -> Dict[str, float]:
        """
        Computes or retrieves cached raster grid statistics for the given band.
        """
        if band_idx in self._cached_statistics and grid_data is None:
            return self._cached_statistics[band_idx]

        data = grid_data if grid_data is not None else self.read_band(band_idx)
        mask = (data != self.nodata) if self.nodata is not None else np.ones_like(data, dtype=bool)
        valid_vals = data[mask]
        
        stats = {}
        if valid_vals.size > 0:
            stats = {
                "min": float(valid_vals.min()),
                "max": float(valid_vals.max()),
                "mean": float(valid_vals.mean()),
                "std": float(valid_vals.std())
            }
        else:
            stats = {"min": 0.0, "max": 0.0, "mean": 0.0, "std": 0.0}
            
        if grid_data is None:
            self._cached_statistics[band_idx] = stats
        return stats

    def histogram(self, band_idx: int = 1, bins: int = 256) -> Tuple[np.ndarray, np.ndarray]:
        """
        Computes the histogram of the raster band values.
        """
        grid_data = self.read_band(band_idx)
        mask = (grid_data != self.nodata) if self.nodata is not None else np.ones_like(grid_data, dtype=bool)
        valid_vals = grid_data[mask]
        return np.histogram(valid_vals, bins=bins)

    def nodata_mask(self, band_idx: int = 1) -> np.ndarray:
        """
        Returns a boolean mask where True indicates NoData values.
        """
        grid_data = self.read_band(band_idx)
        if self.nodata is None:
            return np.zeros_like(grid_data, dtype=bool)
        return grid_data == self.nodata

    def overview_levels(self, band_idx: int = 1) -> List[int]:
        """
        Returns the overview downsampling levels available in the raster file.
        """
        if not self.file_path or not _RASTERIO:
            return []
        with rasterio.open(self.file_path) as src:
            return list(src.overviews(band_idx))

    def validate(self) -> ValidationReport:
        errors = []
        warnings = []
        nodata_stats = {}

        # 1. Validate Resolution
        dx, dy = self.resolution
        if dx <= 0 or dy == 0:
            errors.append(f"Invalid raster resolution values: {self.resolution}")
        
        # 2. Validate Bounds alignment
        xmin, ymin, xmax, ymax = self.bounds
        if xmin >= xmax or ymin >= ymax:
            errors.append(f"Invalid bounding box boundaries: {self.bounds}")
            
        # 3. Validate file existence if path provided
        if self.file_path and not os.path.exists(self.file_path):
            errors.append(f"Raster back-file path does not exist: {self.file_path}")

        # 4. Compute NoData stats if file exists
        if self.file_path and os.path.exists(self.file_path):
            try:
                grid = self.read_band(1)
                if self.nodata is not None:
                    nodata_count = int(np.sum(grid == self.nodata))
                    total_cells = grid.size
                    nodata_stats = {
                        "nodata_value": self.nodata,
                        "nodata_count": nodata_count,
                        "nodata_percentage": float(nodata_count / total_cells * 100.0)
                    }
            except Exception as exc:
                warnings.append(f"Could not compute NoData statistics: {exc}")

        return ValidationReport(
            dataset_name=self.name,
            crs_status="Valid" if self.crs else "Missing",
            geometry_status="N/A - Raster Layer",
            raster_alignment="Aligned",
            nodata_statistics=nodata_stats,
            extent=self.bounds,
            resolution=self.resolution,
            warnings=warnings,
            errors=errors,
            result=(len(errors) == 0)
        )


class VectorLayer(BaseLayer):
    """
    Represents vector spatial geometries (e.g. roads, buildings, waterways).
    Supports spatial indexing and geometry topology validation checks.
    """
    def __init__(
        self,
        name: str,
        crs: str,
        bounds: Tuple[float, float, float, float],
        features: List[Dict[str, Any]]
    ) -> None:
        super().__init__(name, crs, bounds)
        self.features: List[Dict[str, Any]] = features
        self.spatial_index: Optional[STRtree] = None

    def build_spatial_index(self) -> None:
        """
        Builds a R-tree spatial index (using shapely STRtree) over vector features
        for extremely fast spatial overlap queries.
        """
        if not _SHAPELY:
            return

        geoms = []
        for feat in self.features:
            geom_data = feat.get("geometry")
            if geom_data:
                geoms.append(shapely_shape(geom_data))
        
        if geoms:
            self.spatial_index = STRtree(geoms)

    def validate(self) -> ValidationReport:
        """
        Performs topology, invalid polygons, empty geometries, and duplicate features checks.
        """
        errors = []
        warnings = []
        
        if not _SHAPELY:
            errors.append("Shapely is required for geometry validation.")
            return ValidationReport(
                dataset_name=self.name,
                crs_status="Valid" if self.crs else "Missing",
                geometry_status="Failed to run checks (Missing Shapely)",
                raster_alignment="N/A - Vector Layer",
                extent=self.bounds,
                resolution=(0.0, 0.0),
                warnings=warnings,
                errors=errors,
                result=False
            )

        seen_geometries = set()
        for idx, feat in enumerate(self.features):
            geom_data = feat.get("geometry")
            if not geom_data:
                errors.append(f"Feature {idx}: Empty geometry payload.")
                continue

            try:
                geom = shapely_shape(geom_data)
                
                # Check for empty geometry
                if geom.is_empty:
                    errors.append(f"Feature {idx}: Geometry is empty.")
                    
                # Check for invalid geometry / topology errors
                if not geom.is_valid:
                    validity_reason = explain_validity(geom)
                    errors.append(f"Feature {idx}: Invalid topology ({validity_reason}).")

                # Check for duplicate geometries
                wkb = geom.wkb
                if wkb in seen_geometries:
                    warnings.append(f"Feature {idx}: Duplicate geometry detected.")
                else:
                    seen_geometries.add(wkb)
            except Exception as exc:
                errors.append(f"Feature {idx}: Failed to parse geometry: {exc}")

        return ValidationReport(
            dataset_name=self.name,
            crs_status="Valid" if self.crs else "Missing",
            geometry_status="Valid" if not errors else "Invalid",
            raster_alignment="N/A - Vector Layer",
            extent=self.bounds,
            resolution=(0.0, 0.0),
            warnings=warnings,
            errors=errors,
            result=(len(errors) == 0)
        )
