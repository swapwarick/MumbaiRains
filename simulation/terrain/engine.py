"""
simulation/terrain/engine.py
-----------------------------
TerrainEngine — coordinates DEM loading, caching, numerical verification,
topological analysis, and exporting of derived grids.

Scientific References:
1. Horn, B.K.P. (1981). "Hill Shading and the Reflectance Map." Proceedings of the IEEE, 69(1), 14-47.
2. O'Callaghan, J.F., and Mark, D.M. (1984). "The Extraction of Drainage Networks from Digital Elevation Data."
   Computer Vision, Graphics, and Image Processing, 28(3), 323-344.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Dict, Any, Optional, Tuple
import numpy as np

from backend.utils import get_logger
from backend.config import settings
from backend.exceptions import TerrainException
from simulation.terrain.loader import TerrainLoader
from simulation.terrain.cache import TerrainCache
from simulation.terrain.visualizer import export_terrain_visuals
from simulation.terrain.algorithms import (
    compute_slope_aspect,
    compute_slope_percent,
    compute_flow_direction_d8_all,
    compute_flow_accumulation,
    delineate_watershed,
    compute_hillshade,
)
from simulation.core.verification import (
    verify_no_nan,
    verify_no_inf,
    verify_grid_integrity,
    verify_flow_direction_validity
)

logger = get_logger(__name__)


def validate_transform_and_crs(transform: list, crs_str: str) -> float:
    """
    Validate the complete affine transform.
    Check pixel width, pixel height, rotation terms and skew.
    Reject unsupported rotated/skewed rasters with a clear exception.
    Do not infer cell size from a single transform element.
    """
    if len(transform) != 6:
        raise TerrainException(f"Invalid affine transform length: expected 6, got {len(transform)}")
        
    a, b, c, d, e, f = [float(val) for val in transform]
    
    # 1. Check rotation and skew
    if abs(b) > 1e-7 or abs(d) > 1e-7:
        raise TerrainException(
            f"Rotated or skewed rasters are not supported. "
            f"Rotation/skew terms must be zero, got b={b}, d={d}."
        )
        
    # 2. Check signs and values
    if a <= 0:
        raise TerrainException(f"Pixel width must be positive, got {a}")
    if e >= 0:
        raise TerrainException(f"Pixel height must be negative (North-up), got {e}")
        
    # 3. Determine cell size in meters
    dy = abs(e)
    dx = a
    
    # Check if geographic (degrees) vs projected (meters)
    # A degree-based coordinate system (like EPSG:4326) will have pixel resolutions
    # in degrees, which are very small (e.g. < 0.1 degree).
    # Synthetic benchmarks use EPSG:4326 but have pixel size 10.0, which means they are flat/projected.
    is_geographic = ("4326" in crs_str or "geographic" in crs_str.lower()) and max(dx, dy) < 0.1
    
    if is_geographic:
        # Check aspect ratio of degree-based grid resolution to ensure it is not highly distorted
        aspect_ratio = dx / dy
        if aspect_ratio < 0.2 or aspect_ratio > 5.0:
            raise TerrainException(
                f"Highly distorted geographic aspect ratio (dx/dy = {aspect_ratio:.4f})."
            )
        # Use settings cell_size_m for isotropic cell size in meters
        return settings.cell_size_m
    else:
        # Projected CRS (units are in meters)
        # Verify that cells are square (isotropic cell size)
        pct_diff = abs(dx - dy) / max(dx, dy)
        if pct_diff > 0.01:  # allow up to 1% difference
            raise TerrainException(
                f"Anisotropic grid cells (non-square) are not supported. "
                f"Pixel width ({dx}m) and height ({dy}m) must be equal (got {pct_diff*100.0:.2f}% difference)."
            )
        # Do not infer cell size from a single transform element; use average of both
        return (dx + dy) / 2.0


def compute_dataset_hash(
    elevation: Optional[np.ndarray],
    meta: Dict[str, Any],
    file_path: str
) -> str:
    """
    Computes a SHA256 hash that uniquely identifies the dataset based on:
    - raster dimensions (width, height)
    - CRS
    - affine transform coefficients
    - NoData value
    - data type (dtype)
    - source file path
    - checksum of elevation data (if available)
    """
    hasher = hashlib.sha256()
    
    # 1. Raster dimensions
    width = meta.get("width", 0)
    height = meta.get("height", 0)
    hasher.update(f"dim:{width}x{height}".encode("utf-8"))
    
    # 2. CRS
    crs = str(meta.get("crs", ""))
    hasher.update(f"|crs:{crs}".encode("utf-8"))
    
    # 3. Affine transform
    transform = meta.get("transform", [])
    transform_str = ",".join(f"{val:.8f}" for val in transform)
    hasher.update(f"|transform:{transform_str}".encode("utf-8"))
    
    # 4. NoData value
    nodata = meta.get("nodata")
    nodata_str = str(nodata) if nodata is not None else "none"
    hasher.update(f"|nodata:{nodata_str}".encode("utf-8"))
    
    # 5. Data type
    dtype = str(meta.get("dtype", ""))
    hasher.update(f"|dtype:{dtype}".encode("utf-8"))
    
    # 6. Source file path
    hasher.update(f"|path:{file_path}".encode("utf-8"))
    
    # 7. Checksum of elevation data (if available)
    if elevation is not None:
        hasher.update(b"|checksum:")
        hasher.update(elevation.tobytes())
        
    return hasher.hexdigest()[:16]


@dataclass
class TerrainEngine:
    """
    Manages DEM loading, caching, verification, and derived terrain analyses.
    Uses O(1) in-memory and on-disk caches for computed products.
    """
    _loader: TerrainLoader = field(default_factory=TerrainLoader, repr=False)
    _cache: TerrainCache = field(default_factory=TerrainCache, repr=False)
    
    _elevation: Optional[np.ndarray] = field(default=None, repr=False)
    _meta: Optional[Dict[str, Any]] = field(default=None, repr=False)
    _dataset_hash: str = field(default="", repr=False)
    _file_path: str = field(default="", repr=False)
    _cell_size: Optional[float] = field(default=None, repr=False)

    # Lazy-loaded computational layers
    _slope: Optional[np.ndarray] = field(default=None, repr=False)
    _slope_pct: Optional[np.ndarray] = field(default=None, repr=False)
    _aspect: Optional[np.ndarray] = field(default=None, repr=False)
    _flow_code: Optional[np.ndarray] = field(default=None, repr=False)
    _flow_angle: Optional[np.ndarray] = field(default=None, repr=False)
    _downstream_cells: Optional[np.ndarray] = field(default=None, repr=False)
    _flow_acc: Optional[np.ndarray] = field(default=None, repr=False)
    _hillshade: Optional[np.ndarray] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self._elevation is not None and self._meta is not None:
            # Validate transform and determine cell size
            self._cell_size = validate_transform_and_crs(self._meta["transform"], self._meta["crs"])
            if not self._dataset_hash:
                path = self._file_path or str(settings.dem_path)
                self._dataset_hash = compute_dataset_hash(self._elevation, self._meta, path)

    def load(self, dem_path: str | None = None) -> "TerrainEngine":
        """
        Load DEM, calculate unique hash, and clear cached values.
        """
        path = str(dem_path or settings.dem_path)
        self._file_path = path
        self._elevation, self._meta = self._loader.load_raster(path)
        
        # Validate the affine transform and get cell size
        self._cell_size = validate_transform_and_crs(self._meta["transform"], self._meta["crs"])
        
        # Verify grid integrity of loaded DEM
        ok, errs = verify_grid_integrity(self._elevation)
        if not ok:
            raise TerrainException(f"DEM integrity check failed: {errs}")
            
        # Compute SHA256 of array data to safely index cache
        self._dataset_hash = compute_dataset_hash(self._elevation, self._meta, self._file_path)
        
        # Reset current lazy parameters
        self._slope = self._slope_pct = self._aspect = None
        self._flow_code = self._flow_angle = self._downstream_cells = None
        self._flow_acc = self._hillshade = None
        
        logger.info(
            "TerrainEngine loaded and verified DEM",
            extra={"path": path, "shape": self._elevation.shape, "hash": self._dataset_hash}
        )
        return self

    def _require_loaded(self) -> None:
        """Raises if load() has not been called."""
        if self._elevation is None:
            raise TerrainException("TerrainEngine has no data. Call load() first.")

    def _verify_grid(self, name: str, grid: np.ndarray) -> None:
        """Helper to run NaN and Inf audits on computed arrays."""
        if not verify_no_nan(grid):
            raise TerrainException(f"Grid verification failed: {name} contains NaN values.")
        if not verify_no_inf(grid):
            raise TerrainException(f"Grid verification failed: {name} contains Infinite values.")

    @property
    def elevation(self) -> np.ndarray:
        """Raw elevation grid (metres, float32)."""
        self._require_loaded()
        return self._elevation  # type: ignore[return-value]

    @property
    def meta(self) -> Dict[str, Any]:
        """DEM metadata: width, height, crs, transform, nodata."""
        self._require_loaded()
        return self._meta  # type: ignore[return-value]

    @property
    def cell_size(self) -> float:
        """Isotropic cell size in meters, validated from affine transform."""
        if self._cell_size is None:
            self._require_loaded()
            self._cell_size = validate_transform_and_crs(self._meta["transform"], self._meta["crs"])
        return self._cell_size

    @property
    def slope(self) -> np.ndarray:
        """Slope in degrees [0, 90], float32."""
        if self._slope is None:
            self._require_loaded()
            cached = self._cache.get_cached_grid("slope", self._dataset_hash)
            if cached is not None:
                self._slope = cached
            else:
                self._compute_slope_and_aspect()
        return self._slope  # type: ignore[return-value]

    @property
    def slope_percent(self) -> np.ndarray:
        """Slope in percent rise/run, float32."""
        if self._slope_pct is None:
            self._require_loaded()
            cached = self._cache.get_cached_grid("slope_pct", self._dataset_hash)
            if cached is not None:
                self._slope_pct = cached
            else:
                self._slope_pct = compute_slope_percent(self._elevation, self.cell_size)
                self._verify_grid("slope_percent", self._slope_pct)
                self._cache.cache_grid("slope_pct", self._dataset_hash, self._slope_pct)
        return self._slope_pct  # type: ignore[return-value]

    @property
    def aspect(self) -> np.ndarray:
        """Aspect in compass degrees [0, 360), float32. -1.0 = flat."""
        if self._aspect is None:
            self._require_loaded()
            cached = self._cache.get_cached_grid("aspect", self._dataset_hash)
            if cached is not None:
                self._aspect = cached
            else:
                self._compute_slope_and_aspect()
        return self._aspect  # type: ignore[return-value]

    def _compute_slope_and_aspect(self) -> None:
        """Computes, validates, and caches both slope and aspect grids."""
        self._slope, self._aspect = compute_slope_aspect(
            self._elevation, self.cell_size
        )
        self._verify_grid("slope", self._slope)
        self._verify_grid("aspect", self._aspect)
        self._cache.cache_grid("slope", self._dataset_hash, self._slope)
        self._cache.cache_grid("aspect", self._dataset_hash, self._aspect)

    @property
    def flow_direction(self) -> np.ndarray:
        """D8 flow direction ESRI code grid, uint8."""
        if self._flow_code is None:
            self._require_loaded()
            cached = self._cache.get_cached_grid("flow_code", self._dataset_hash)
            if cached is not None:
                self._flow_code = cached
            else:
                self._flow_code, self._flow_angle, self._downstream_cells = compute_flow_direction_d8_all(
                    self._elevation, self.cell_size
                )
                
                # Check flow direction validity (ESRI codes check)
                ok, errs = verify_flow_direction_validity(self._flow_code)
                if not ok:
                    raise TerrainException(f"D8 flow direction verification failed: {errs}")
                    
                self._verify_grid("flow_code", self._flow_code)
                self._cache.cache_grid("flow_code", self._dataset_hash, self._flow_code)
                self._cache.cache_grid("flow_angle", self._dataset_hash, self._flow_angle)
                self._cache.cache_grid("downstream_cells", self._dataset_hash, self._downstream_cells)
        return self._flow_code  # type: ignore[return-value]

    @property
    def flow_angle(self) -> np.ndarray:
        """D8 flow direction compass angles grid, float32."""
        if self._flow_angle is None:
            _ = self.flow_direction
        return self._flow_angle  # type: ignore[return-value]

    @property
    def downstream_cells(self) -> np.ndarray:
        """D8 downstream cells coordinates grid, int32."""
        if self._downstream_cells is None:
            _ = self.flow_direction
        return self._downstream_cells  # type: ignore[return-value]

    @property
    def flow_accumulation(self) -> np.ndarray:
        """Flow accumulation counts grid, float32."""
        if self._flow_acc is None:
            self._require_loaded()
            cached = self._cache.get_cached_grid("flow_acc", self._dataset_hash)
            if cached is not None:
                self._flow_acc = cached
            else:
                self._flow_acc = compute_flow_accumulation(
                    self.flow_direction, self._elevation
                )
                self._verify_grid("flow_accumulation", self._flow_acc)
                self._cache.cache_grid("flow_acc", self._dataset_hash, self._flow_acc)
        return self._flow_acc  # type: ignore[return-value]

    @property
    def hillshade(self) -> np.ndarray:
        """Hillshade visualization grid, uint8 [0, 255]."""
        if self._hillshade is None:
            self._require_loaded()
            cached = self._cache.get_cached_grid("hillshade", self._dataset_hash)
            if cached is not None:
                self._hillshade = cached
            else:
                self._hillshade = compute_hillshade(
                    self._elevation, self.cell_size
                )
                self._verify_grid("hillshade", self._hillshade)
                self._cache.cache_grid("hillshade", self._dataset_hash, self._hillshade)
        return self._hillshade  # type: ignore[return-value]

    def delineate_watershed_mask(self, outlet_coord: Tuple[int, int]) -> np.ndarray:
        """
        Delineates watershed boundary contributing to the specified outlet cell.
        """
        self._require_loaded()
        return delineate_watershed(self.flow_direction, outlet_coord)

    # ------------------------------------------------------------------ #
    # Exporters & Visualizers                                              #
    # ------------------------------------------------------------------ #

    def export_all(self, output_dir: str = "benchmarks/outputs") -> None:
        """
        Exports PNGs, GeoTIFFs, statistics, and histograms for all computed layers.
        """
        self._require_loaded()
        meta = self.meta
        
        export_terrain_visuals("elevation", self.elevation, meta, output_dir)
        export_terrain_visuals("slope_deg", self.slope, meta, output_dir)
        export_terrain_visuals("slope_pct", self.slope_percent, meta, output_dir)
        export_terrain_visuals("aspect", self.aspect, meta, output_dir)
        export_terrain_visuals("flow_direction", self.flow_direction, meta, output_dir)
        export_terrain_visuals("flow_accumulation", self.flow_accumulation, meta, output_dir)
        export_terrain_visuals("hillshade", self.hillshade, meta, output_dir)

    # ------------------------------------------------------------------ #
    # Summary                                                            #
    # ------------------------------------------------------------------ #

    @property
    def metadata(self) -> Dict[str, Any]:
        """
        Return lightweight metadata suitable for API responses.
        """
        self._require_loaded()
        t = self._meta["transform"]  # type: ignore[index]
        rows = self._meta["height"]  # type: ignore[index]
        cols = self._meta["width"]   # type: ignore[index]
        elev = self._elevation       # type: ignore[assignment]

        lon_w = t[2]
        lon_e = lon_w + t[0] * cols
        lat_n = t[5]
        lat_s = lat_n + t[4] * rows

        return {
            "width": cols,
            "height": rows,
            "crs": self._meta["crs"],       # type: ignore[index]
            "transform": t,
            "bounds": {
                "west": round(lon_w, 6),
                "east": round(lon_e, 6),
                "south": round(lat_s, 6),
                "north": round(lat_n, 6),
            },
            "stats": {
                "elevation": _array_stats(elev),
                "slope": _array_stats(self.slope),
            },
        }

    def full_grid(self) -> Dict[str, Any]:
        """
        Return all computed layers as nested Python lists.
        Used by the /api/terrain/grid endpoint (backward-compatible).
        """
        self._require_loaded()
        return {
            "width": self._meta["width"],        # type: ignore[index]
            "height": self._meta["height"],      # type: ignore[index]
            "crs": self._meta["crs"],            # type: ignore[index]
            "transform": self._meta["transform"],# type: ignore[index]
            "elevation": self.elevation.tolist(),
            "slope": self.slope.tolist(),
            "aspect": self.aspect.tolist(),
            "flow_direction": self.flow_direction.tolist(),
            "flow_accumulation": self.flow_accumulation.tolist(),
        }


def _array_stats(arr: np.ndarray) -> Dict[str, float]:
    """Return min/max/mean/std for a numpy array, rounded to 2 dp."""
    return {
        "min": round(float(arr.min()), 2),
        "max": round(float(arr.max()), 2),
        "mean": round(float(arr.mean()), 2),
        "std": round(float(arr.std()), 2),
    }
