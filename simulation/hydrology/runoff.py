"""
simulation/hydrology/runoff.py
-------------------------------
Surface runoff calculation methods.
Moved from the old flat simulation/runoff.py — no logic changed.
"""

import numpy as np


def calculate_scs_runoff(
    rainfall: np.ndarray,
    curve_number: np.ndarray,
) -> np.ndarray:
    """
    Calculate direct runoff depth using the SCS Curve Number method.

    Formula:
        S  = (25400 / CN) - 254        [storage potential, mm]
        Ia = 0.2 * S                   [initial abstraction, mm]
        Q  = (P - Ia)² / (P - Ia + S)  for P > Ia, else 0

    Args:
        rainfall:     Accumulated rainfall in mm. May be a scalar-wrapped
                      array (shape (1,)) or a full 2-D spatial grid.
        curve_number: CN grid (same spatial shape as output). Values 1–100.

    Returns:
        Runoff depth grid in mm, same shape as ``curve_number``.
    """
    S = (25400.0 / np.maximum(curve_number, 1.0)) - 254.0
    Ia = 0.2 * S

    # Broadcast scalar rainfall onto the CN grid
    if isinstance(rainfall, np.ndarray) and rainfall.ndim == 1 and len(rainfall) == 1:
        rain_grid = np.full_like(curve_number, float(rainfall[0]))
    else:
        rain_grid = rainfall

    runoff = np.zeros_like(curve_number, dtype=np.float32)
    mask = rain_grid > Ia
    if np.any(mask):
        excess = rain_grid[mask] - Ia[mask]
        runoff[mask] = (excess ** 2) / (excess + S[mask])

    return runoff


def green_ampt_infiltration(
    suction_head: float,
    hydraulic_conductivity: float,
    moisture_deficit: float,
    cumulative_infiltration: float,
    pond_depth: float = 0.0,
) -> float:
    """
    Calculate infiltration rate using the Green-Ampt equation.

    f = Ks * [1 + (ψ + h) * Δθ / F]

    Args:
        suction_head:           Wetting front suction head ψ (mm).
        hydraulic_conductivity: Saturated hydraulic conductivity Ks (mm/hr).
        moisture_deficit:       Initial soil moisture deficit Δθ (dimensionless).
        cumulative_infiltration: Cumulative infiltration F (mm).
        pond_depth:             Ponded water depth h (mm), default 0.

    Returns:
        Infiltration rate in mm/hr.
    """
    if cumulative_infiltration <= 0:
        return hydraulic_conductivity
    return hydraulic_conductivity * (
        1.0 + (suction_head + pond_depth) * moisture_deficit / cumulative_infiltration
    )
