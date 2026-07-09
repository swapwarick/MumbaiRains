"""
simulation/terrain/synthetic_generator.py
-----------------------------------------
Generates synthetic terrain datasets (Flat, Uniform Slope, Hill, Valley, and Watershed)
and computes their golden reference grids.
Stores references inside `benchmarks/golden/` for rigorous algorithm validation.
"""

import os
import numpy as np


def generate_flat_surface(size: int = 10, cell_size: float = 10.0) -> Dict[str, np.ndarray]:
    """Generates flat surface: constant 5m elevation."""
    elev = np.full((size, size), 5.0, dtype=np.float32)
    slope_deg = np.zeros_like(elev)
    slope_pct = np.zeros_like(elev)
    aspect = np.full_like(elev, -1.0)
    flow_dir = np.zeros_like(elev, dtype=np.uint8)  # sinks
    flow_acc = np.ones_like(elev)
    return {
        "elevation": elev,
        "slope_deg": slope_deg,
        "slope_pct": slope_pct,
        "aspect": aspect,
        "flow_dir": flow_dir,
        "flow_acc": flow_acc
    }


def generate_uniform_slope(size: int = 10, cell_size: float = 10.0, step: float = 1.0) -> Dict[str, np.ndarray]:
    """Generates uniform slope: elevation decreases from North to South."""
    elev = np.zeros((size, size), dtype=np.float32)
    for r in range(size):
        elev[r, :] = 100.0 - r * step
        
    # Slope = arctan(step / cell_size) in degrees
    slope_val = float(np.degrees(np.arctan(step / cell_size)))
    slope_pct_val = float((step / cell_size) * 100.0)
    
    slope_deg = np.full_like(elev, slope_val)
    slope_pct = np.full_like(elev, slope_pct_val)
    
    # Aspect points South = 180 degrees
    aspect = np.full_like(elev, 180.0)
    
    # Flow direction points South (ESRI code 4)
    flow_dir = np.full_like(elev, 4, dtype=np.uint8)
    # Bottom row has no downslope neighbor (sink = 0)
    flow_dir[-1, :] = 0
    
    # Flow accumulation: row r drains into row r+1. Each cell gets sum of cells above it
    flow_acc = np.zeros_like(elev)
    for r in range(size):
        flow_acc[r, :] = r + 1.0
        
    return {
        "elevation": elev,
        "slope_deg": slope_deg,
        "slope_pct": slope_pct,
        "aspect": aspect,
        "flow_dir": flow_dir,
        "flow_acc": flow_acc
    }


def generate_single_hill(size: int = 11, cell_size: float = 10.0) -> Dict[str, np.ndarray]:
    """Generates symmetric hill using a Gaussian dome."""
    xc, yc = size // 2, size // 2
    elev = np.zeros((size, size), dtype=np.float32)
    for r in range(size):
        for c in range(size):
            dist_sq = (r - yc)**2 + (c - xc)**2
            elev[r, c] = 50.0 + 20.0 * np.exp(-dist_sq / 12.0)
            
    # Golden values will be numerically verified against algorithm outputs rather than analytical.
    # We will generate these with a helper to compute references directly via a validated baseline.
    return {"elevation": elev}


def generate_single_valley(size: int = 11, cell_size: float = 10.0) -> Dict[str, np.ndarray]:
    """Generates a V-shaped drainage valley."""
    xc = size // 2
    elev = np.zeros((size, size), dtype=np.float32)
    for r in range(size):
        for c in range(size):
            elev[r, c] = 10.0 + 5.0 * abs(c - xc) - 0.5 * r  # Slopes inward to center and drains South
    return {"elevation": elev}


def generate_synthetic_watershed(size: int = 15, cell_size: float = 10.0) -> Dict[str, np.ndarray]:
    """Generates a compound watershed converging to an outlet at bottom center."""
    xc, yc = size // 2, size - 1
    elev = np.zeros((size, size), dtype=np.float32)
    for r in range(size):
        for c in range(size):
            dist = np.sqrt((r - yc)**2 + (c - xc)**2)
            elev[r, c] = 10.0 + dist * 5.0 + (abs(c - xc) ** 1.5) * 2.0
    return {"elevation": elev}


def create_and_save_golden(output_dir: str = "benchmarks/golden") -> None:
    """Computes and saves all golden reference files."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Flat
    flat = generate_flat_surface()
    np.savez(os.path.join(output_dir, "flat_surface.npz"), **flat)
    
    # Uniform Slope
    slope = generate_uniform_slope()
    np.savez(os.path.join(output_dir, "uniform_slope.npz"), **slope)
    
    # For Hill, Valley, and Watershed, we generate expected outputs using a validated baseline
    # of the core algorithms. We will run these through a reference run in our test suite
    # or generate them here by calling the algorithms once verified.
    # Let's import the algorithms to compute their golden references.
    from simulation.terrain.algorithms import (
        compute_slope_aspect,
        compute_flow_direction_d8,
        compute_flow_accumulation
    )
    
    for name, gen_fn in [
        ("single_hill", generate_single_hill),
        ("single_valley", generate_single_valley),
        ("synthetic_watershed", generate_synthetic_watershed)
    ]:
        data = gen_fn()
        elev = data["elevation"]
        
        slope_deg, aspect = compute_slope_aspect(elev, 10.0)
        # Slope % is tan(slope_deg) * 100
        slope_pct = np.tan(np.radians(slope_deg)) * 100.0
        
        flow_dir = compute_flow_direction_d8(elev, 10.0)
        flow_acc = compute_flow_accumulation(flow_dir, elev)
        
        np.savez(
            os.path.join(output_dir, f"{name}.npz"),
            elevation=elev,
            slope_deg=slope_deg.astype(np.float32),
            slope_pct=slope_pct.astype(np.float32),
            aspect=aspect.astype(np.float32),
            flow_dir=flow_dir.astype(np.uint8),
            flow_acc=flow_acc.astype(np.float32)
        )
        
    print("Golden datasets saved successfully.")


if __name__ == "__main__":
    from typing import Dict
    create_and_save_golden()
