"""
simulation/terrain.py — SHIM
------------------------------
This module is preserved for backward compatibility only.
All terrain logic now lives in simulation/terrain/ subpackage.

DO NOT add new code here. Import from simulation.terrain.* directly.
"""
# Re-export the public API that old callers expect
from simulation.terrain.loader import load_dem          # noqa: F401
from simulation.terrain.engine import TerrainEngine     # noqa: F401
from simulation.terrain.algorithms import (
    compute_slope_aspect    as calculate_slope_and_aspect,    # noqa: F401
    compute_flow_direction_d8 as calculate_flow_direction_d8, # noqa: F401
    compute_flow_accumulation as calculate_flow_accumulation_d8, # noqa: F401
)
import numpy as np
from typing import Dict, Any


def process_terrain(dem_path: str, cell_size: float = 30.0) -> Dict[str, Any]:
    """Legacy entry point — delegates to TerrainEngine."""
    engine = TerrainEngine().load(dem_path)
    return {
        "elevation": engine.elevation,
        "slope": engine.slope,
        "aspect": engine.aspect,
        "flow_direction": engine.flow_direction,
        "flow_accumulation": engine.flow_accumulation,
        "meta": engine.meta,
    }
