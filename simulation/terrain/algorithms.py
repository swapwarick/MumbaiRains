"""
simulation/terrain/algorithms.py
---------------------------------
Vectorized terrain analysis algorithms for slope, aspect, D8 flow direction,
flow accumulation, hillshade, and watershed delineation.

Scientific References:
1. Horn, B.K.P. (1981). "Hill Shading and the Reflectance Map." Proceedings of the IEEE, 69(1), 14-47.
2. O'Callaghan, J.F., and Mark, D.M. (1984). "The Extraction of Drainage Networks from Digital Elevation Data."
   Computer Vision, Graphics, and Image Processing, 28(3), 323-344.
3. Tarboton, D.G. (1997). "A new method for the determination of flow directions and upslope areas in grid digital elevation models."
   Water Resources Research, 33(2), 309-319.
"""

from typing import Tuple, Dict, Any, List
import numpy as np


def compute_slope_aspect(
    elevation: np.ndarray,
    cell_size: float = 30.0,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute slope and aspect using Horn's (1981) 3×3 weighted gradient method.
    Fully vectorized — operates on the entire grid simultaneously.

    Args:
        elevation: 2-D float32 array of elevations in metres.
        cell_size: Ground resolution in metres per cell.

    Returns:
        slope:  float32 array, slope in degrees [0, 90].
        aspect: float32 array, aspect in compass degrees [0, 360).
                -1.0 marks flat cells (rise_run < 1e-4).
    """
    # Pad once — avoids edge artifacts
    pad = np.pad(elevation, 1, mode="edge")

    # Extract the 8 neighbouring slices from the padded array
    z1 = pad[:-2, :-2];  z2 = pad[:-2, 1:-1]; z3 = pad[:-2, 2:]
    z4 = pad[1:-1, :-2]                       ; z6 = pad[1:-1, 2:]
    z7 = pad[2:,  :-2];  z8 = pad[2:,  1:-1]; z9 = pad[2:,  2:]

    # Horn's partial derivatives (vectorized)
    dz_dx = ((z3 + 2 * z6 + z9) - (z1 + 2 * z4 + z7)) / (8.0 * cell_size)
    dz_dy = ((z7 + 2 * z8 + z9) - (z1 + 2 * z2 + z3)) / (8.0 * cell_size)

    rise_run = np.sqrt(dz_dx ** 2 + dz_dy ** 2)
    slope = np.degrees(np.arctan(rise_run)).astype(np.float32)

    # Aspect — -1.0 for flat cells
    aspect = np.full_like(slope, -1.0)
    steep = rise_run > 1e-4
    aspect_rad = np.where(steep, np.arctan2(dz_dy, -dz_dx), 0.0)
    aspect_deg = np.where(steep, 270.0 - np.degrees(aspect_rad), -1.0)
    aspect = (aspect_deg % 360.0).astype(np.float32)
    # Restore -1 for flat cells
    aspect[~steep] = -1.0

    return slope, aspect


def compute_slope_percent(elevation: np.ndarray, cell_size: float = 30.0) -> np.ndarray:
    """
    Computes slope in percent rise/run using Horn's (1981) partial derivatives.
    Formula: slope_pct = (rise / run) * 100
    """
    pad = np.pad(elevation, 1, mode="edge")

    z1 = pad[:-2, :-2];  z2 = pad[:-2, 1:-1]; z3 = pad[:-2, 2:]
    z4 = pad[1:-1, :-2]                       ; z6 = pad[1:-1, 2:]
    z7 = pad[2:,  :-2];  z8 = pad[2:,  1:-1]; z9 = pad[2:,  2:]

    dz_dx = ((z3 + 2 * z6 + z9) - (z1 + 2 * z4 + z7)) / (8.0 * cell_size)
    dz_dy = ((z7 + 2 * z8 + z9) - (z1 + 2 * z2 + z3)) / (8.0 * cell_size)

    rise_run = np.sqrt(dz_dx ** 2 + dz_dy ** 2)
    return (rise_run * 100.0).astype(np.float32)


def compute_flow_direction_d8(
    elevation: np.ndarray,
    cell_size: float = 30.0,
) -> np.ndarray:
    """
    Backward compatible helper returning only the D8 flow direction code grid.
    """
    flow_code, _, _ = compute_flow_direction_d8_all(elevation, cell_size)
    return flow_code


def compute_flow_direction_d8_all(
    elevation: np.ndarray,
    cell_size: float = 30.0,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute D8 flow direction details for each cell.
    D8 flow codes (ESRI convention):
        1=E, 2=SE, 4=S, 8=SW, 16=W, 32=NW, 64=N, 128=NE, 0=sink

    Args:
        elevation: 2-D float32 elevation grid.
        cell_size: Metres per cell.

    Returns:
        flow_code: uint8 array of D8 codes.
        flow_angle: float32 array of flow angles in compass degrees (0=N, 90=E, 180=S, 270=W, -1=sink).
        downstream_cells: int32 array of shape (rows, cols, 2) containing [target_row, target_col].
    """
    rows, cols = elevation.shape
    pad = np.pad(elevation, 1, mode="edge")

    # (row_offset, col_offset, d8_code, distance_factor, compass_angle)
    neighbours = [
        ( 0,  1,   1, 1.0,        90.0),   # E
        ( 1,  1,   2, np.sqrt(2), 135.0),  # SE
        ( 1,  0,   4, 1.0,        180.0),  # S
        ( 1, -1,   8, np.sqrt(2), 225.0),  # SW
        ( 0, -1,  16, 1.0,        270.0),  # W
        (-1, -1,  32, np.sqrt(2), 315.0),  # NW
        (-1,  0,  64, 1.0,          0.0),  # N
        (-1,  1, 128, np.sqrt(2),  45.0),  # NE
    ]

    centre = elevation
    slopes = np.stack([
        (centre - pad[1 + dr : rows + 1 + dr, 1 + dc : cols + 1 + dc]) / (cell_size * dist)
        for dr, dc, _, dist, _ in neighbours
    ])  # shape: (8, rows, cols)

    codes = np.array([n[2] for n in neighbours], dtype=np.uint8)
    angles = np.array([n[4] for n in neighbours], dtype=np.float32)

    best_idx = np.argmax(slopes, axis=0)
    max_slope = slopes[best_idx, np.arange(rows)[:, None], np.arange(cols)[None, :]]

    flow_code = codes[best_idx]
    flow_angle = angles[best_idx]
    
    # Identify flat cells/sinks (max slope <= 0)
    sinks = max_slope <= 0
    flow_code[sinks] = 0
    flow_angle[sinks] = -1.0

    # Build downstream cell indices
    r_coords, c_coords = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")
    downstream_r = r_coords.copy()
    downstream_c = c_coords.copy()

    # D8 code → offset mapping
    for dr, dc, code, _, _ in neighbours:
        mask = (flow_code == code)
        downstream_r[mask] = r_coords[mask] + dr
        downstream_c[mask] = c_coords[mask] + dc

    downstream_cells = np.stack([downstream_r, downstream_c], axis=-1).astype(np.int32)

    return flow_code.astype(np.uint8), flow_angle.astype(np.float32), downstream_cells


def compute_flow_accumulation(
    flow_direction: np.ndarray,
    elevation: np.ndarray,
) -> np.ndarray:
    """
    Compute flow accumulation (number of upstream cells draining into each cell).
    Uses a topological descending-elevation sort to avoid recursion and support large rasters.

    Args:
        flow_direction: uint8 D8 flow direction grid.
        elevation: float32 elevation grid.

    Returns:
        accumulation: float32 grid where value = count of upstream cells + 1.
    """
    rows, cols = flow_direction.shape
    accumulation = np.ones((rows, cols), dtype=np.float32)

    code_to_offset = {
        1:   ( 0,  1),
        2:   ( 1,  1),
        4:   ( 1,  0),
        8:   ( 1, -1),
        16:  ( 0, -1),
        32:  (-1, -1),
        64:  (-1,  0),
        128: (-1,  1),
    }

    # Process cells from highest to lowest elevation
    flat_order = np.argsort(-elevation.ravel())
    row_idx, col_idx = np.unravel_index(flat_order, (rows, cols))

    for r, c in zip(row_idx.tolist(), col_idx.tolist()):
        code = int(flow_direction[r, c])
        offset = code_to_offset.get(code)
        if offset is None:
            continue
        nr, nc = r + offset[0], c + offset[1]
        if 0 <= nr < rows and 0 <= nc < cols:
            accumulation[nr, nc] += accumulation[r, c]

    return accumulation


def delineate_watershed(
    flow_direction: np.ndarray,
    outlet_coord: Tuple[int, int]
) -> np.ndarray:
    """
    Delineates watershed boundary contributing to the specified outlet cell.
    Traces upstream using non-recursive breadth-first traversal.

    Args:
        flow_direction: 2D D8 flow direction code grid.
        outlet_coord: Tuple of (outlet_row, outlet_col).

    Returns:
        watershed_mask: 2D boolean mask indicating cells draining to the outlet.
    """
    rows, cols = flow_direction.shape
    watershed = np.zeros((rows, cols), dtype=bool)
    
    out_r, out_c = outlet_coord
    if not (0 <= out_r < rows and 0 <= out_c < cols):
        return watershed

    code_to_offset = {
        1:   ( 0,  1),
        2:   ( 1,  1),
        4:   ( 1,  0),
        8:   ( 1, -1),
        16:  ( 0, -1),
        32:  (-1, -1),
        64:  (-1,  0),
        128: (-1,  1),
    }

    queue = [(out_r, out_c)]
    watershed[out_r, out_c] = True
    
    # 8-connected neighbor offsets
    neighbors = [
        (-1, -1), (-1, 0), (-1, 1),
        ( 0, -1),          ( 0, 1),
        ( 1, -1), ( 1, 0), ( 1, 1)
    ]

    while queue:
        r, c = queue.pop(0)
        for dr, dc in neighbors:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                if not watershed[nr, nc]:
                    code = int(flow_direction[nr, nc])
                    offset = code_to_offset.get(code)
                    if offset:
                        # Does neighbor drain into current cell?
                        if (nr + offset[0] == r) and (nc + offset[1] == c):
                            watershed[nr, nc] = True
                            queue.append((nr, nc))

    return watershed


def compute_hillshade(
    elevation: np.ndarray,
    cell_size: float = 30.0,
    azimuth: float = 315.0,
    altitude: float = 45.0,
) -> np.ndarray:
    """
    Compute hillshade for visualisation (Lambertian reflectance model).

    Args:
        elevation: 2-D float32 elevation array.
        cell_size: Metres per cell.
        azimuth:   Sun azimuth in degrees (0 = N, clockwise).
        altitude:  Sun altitude above horizon in degrees.

    Returns:
        hillshade: uint8 array in range [0, 255].
    """
    slope, aspect = compute_slope_aspect(elevation, cell_size)

    slope_rad = np.radians(slope)
    aspect_rad = np.radians(aspect)
    zenith_rad = np.radians(90.0 - altitude)
    az_rad = np.radians(360.0 - azimuth + 90.0)

    shade = (
        np.cos(zenith_rad) * np.cos(slope_rad)
        + np.sin(zenith_rad) * np.sin(slope_rad) * np.cos(az_rad - aspect_rad)
    )
    shade = np.clip(shade, 0.0, 1.0)
    return (shade * 255).astype(np.uint8)
