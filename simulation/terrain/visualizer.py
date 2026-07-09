"""
simulation/terrain/visualizer.py
--------------------------------
Visualizer — exports computed terrain grids as PNG visualizations,
GeoTIFF files, statistics text, and histograms.
Gracefully handles missing matplotlib and rasterio dependencies.
"""

import os
from typing import Dict, Any, Optional
import numpy as np

from backend.utils import get_logger

logger = get_logger(__name__)

try:
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend
    import matplotlib.pyplot as plt
    _MATPLOTLIB = True
except ImportError:
    _MATPLOTLIB = False
    logger.warning("matplotlib not installed — PNG and histogram exports will be skipped")

try:
    import rasterio
    _RASTERIO = True
except ImportError:
    _RASTERIO = False
    logger.warning("rasterio not installed — GeoTIFF exports will be skipped")


def export_terrain_visuals(
    name: str,
    grid: np.ndarray,
    meta: Dict[str, Any],
    output_dir: str = "benchmarks/outputs"
) -> None:
    """
    Exports a computed grid as a PNG, GeoTIFF, statistics file, and histogram.

    Args:
        name: Name of the layer (e.g. 'slope_deg', 'flow_accumulation').
        grid: 2D NumPy array of computed grid values.
        meta: Metadata dictionary (transform, crs, nodata).
        output_dir: Base directory for outputting visualization files.
    """
    os.makedirs(output_dir, exist_ok=True)
    basename = os.path.join(output_dir, f"{name.lower()}")

    # 1. Export Statistics
    stats_path = f"{basename}_stats.txt"
    try:
        nodata = meta.get("nodata")
        mask = (grid != nodata) if nodata is not None else np.ones_like(grid, dtype=bool)
        valid_data = grid[mask]
        
        if valid_data.size > 0:
            stats_text = (
                f"Layer: {name}\n"
                f"Shape: {grid.shape}\n"
                f"Min: {float(valid_data.min()):.4f}\n"
                f"Max: {float(valid_data.max()):.4f}\n"
                f"Mean: {float(valid_data.mean()):.4f}\n"
                f"Std: {float(valid_data.std()):.4f}\n"
                f"Valid Cells: {valid_data.size} / {grid.size}\n"
            )
        else:
            stats_text = f"Layer: {name}\nNo valid values.\n"
            
        with open(stats_path, "w") as f:
            f.write(stats_text)
        logger.info(f"Saved stats file: {stats_path}")
    except Exception as exc:
        logger.error(f"Failed to save statistics for {name}: {exc}")

    # 2. Export Histogram (if matplotlib is available)
    if _MATPLOTLIB:
        hist_path = f"{basename}_histogram.png"
        try:
            if valid_data.size > 0:
                plt.figure(figsize=(6, 4))
                plt.hist(valid_data.ravel(), bins=50, color="skyblue", edgecolor="black")
                plt.title(f"Histogram: {name}")
                plt.xlabel("Value")
                plt.ylabel("Frequency")
                plt.tight_layout()
                plt.savefig(hist_path, dpi=150)
                plt.close()
                logger.info(f"Saved histogram: {hist_path}")
        except Exception as exc:
            logger.error(f"Failed to save histogram for {name}: {exc}")
    else:
        logger.debug(f"Skipping histogram for {name} (matplotlib missing)")

    # 3. Export PNG Visualization (if matplotlib is available)
    if _MATPLOTLIB:
        png_path = f"{basename}_vis.png"
        try:
            plt.figure(figsize=(6, 6))
            cmap = "terrain"
            if "slope" in name.lower():
                cmap = "YlOrRd"
            elif "aspect" in name.lower():
                cmap = "twilight"
            elif "flow_direction" in name.lower():
                cmap = "tab10"
            elif "accumulation" in name.lower():
                cmap = "Blues"
                
            plt.imshow(grid, cmap=cmap)
            plt.colorbar(label=name)
            plt.title(f"Visualisation: {name}")
            plt.tight_layout()
            plt.savefig(png_path, dpi=150)
            plt.close()
            logger.info(f"Saved PNG visual: {png_path}")
        except Exception as exc:
            logger.error(f"Failed to save PNG visual for {name}: {exc}")
    else:
        logger.debug(f"Skipping PNG visual for {name} (matplotlib missing)")

    # 4. Export GeoTIFF (if rasterio is available)
    if _RASTERIO:
        tiff_path = f"{basename}.tif"
        try:
            from rasterio.transform import Affine
            t_coeff = meta.get("transform")
            transform = Affine(t_coeff[0], t_coeff[1], t_coeff[2], t_coeff[3], t_coeff[4], t_coeff[5])
            
            with rasterio.open(
                tiff_path,
                "w",
                driver="GTiff",
                height=grid.shape[0],
                width=grid.shape[1],
                count=1,
                dtype=str(grid.dtype),
                crs=meta.get("crs"),
                transform=transform,
                nodata=meta.get("nodata")
            ) as dst:
                dst.write(grid, 1)
            logger.info(f"Saved GeoTIFF: {tiff_path}")
        except Exception as exc:
            logger.error(f"Failed to save GeoTIFF for {name}: {exc}")
    else:
        logger.debug(f"Skipping GeoTIFF for {name} (rasterio missing)")
