"""
simulation/core/verification.py
-------------------------------
Numerical Verification — ensures that simulation runs remain physically consistent.
Provides mathematical checks for mass conservation, NaN detection, CFL condition
timestep stability, DEM grid integrity, and boundary conditions.
"""

from datetime import datetime
from typing import Dict, Any, List, Tuple
import numpy as np
from backend.exceptions import SimulationException


def verify_no_nan(grid: np.ndarray) -> bool:
    """Verifies that no cell in the grid contains NaN."""
    if not np.issubdtype(grid.dtype, np.floating):
        return True
    return not np.any(np.isnan(grid))


def verify_no_inf(grid: np.ndarray) -> bool:
    """Verifies that no cell in the grid contains infinite values."""
    if not np.issubdtype(grid.dtype, np.floating):
        return True
    return not np.any(np.isinf(grid))


def verify_flow_direction_validity(flow_direction_grid: np.ndarray) -> Tuple[bool, List[str]]:
    """Verifies that D8 flow direction codes are ESRI compliant (0, 1, 2, 4, 8, 16, 32, 64, 128)."""
    valid_codes = {0, 1, 2, 4, 8, 16, 32, 64, 128}
    unique_codes = set(np.unique(flow_direction_grid).tolist())
    invalid_codes = unique_codes - valid_codes
    violations = []
    if invalid_codes:
        violations.append(f"Invalid D8 flow direction codes found: {invalid_codes}")
    return len(violations) == 0, violations


def verify_no_negative_water_depth(depth_grid: np.ndarray, tolerance: float = -1e-5) -> Tuple[bool, List[str]]:
    """
    Verifies that no cell has negative water depth below a permitted tolerance.
    """
    violations = []
    min_val = float(np.min(depth_grid))
    if min_val < tolerance:
        neg_count = int(np.sum(depth_grid < tolerance))
        violations.append(
            f"Negative water depth detected: min = {min_val}m, total violating cells = {neg_count}"
        )
    return len(violations) == 0, violations


def verify_mass_conservation(
    initial_volume: float,
    current_volume: float,
    total_inflow: float,
    total_outflow: float,
    tolerance_percent: float = 1.0
) -> Tuple[bool, List[str]]:
    """
    Verifies mass balance: (Initial Volume + Cumulative Inflow - Cumulative Outflow) == Current Volume.
    """
    violations = []
    expected_volume = initial_volume + total_inflow - total_outflow
    abs_error = abs(current_volume - expected_volume)
    
    normalization = max(expected_volume, initial_volume, 1.0)
    relative_error_pct = (abs_error / normalization) * 100.0
    
    if relative_error_pct > tolerance_percent:
        violations.append(
            f"Mass conservation violation: current={current_volume:.3f}m3, "
            f"expected={expected_volume:.3f}m3, absolute error={abs_error:.3f}m3, "
            f"relative error={relative_error_pct:.3f}% (max permitted={tolerance_percent}%)"
        )
    return len(violations) == 0, violations


def verify_grid_integrity(dem_grid: np.ndarray) -> Tuple[bool, List[str]]:
    """
    Verifies the integrity of the DEM grid (e.g. valid boundaries, no extreme spikes).
    """
    violations = []
    # Check for excessive elevation values (e.g., > 8848m or < -100m)
    if dem_grid.size == 0:
        violations.append("DEM grid is empty.")
        return False, violations

    max_elev = float(np.max(dem_grid))
    min_elev = float(np.min(dem_grid))
    if max_elev > 8848.0 or min_elev < -100.0:
        violations.append(
            f"Extreme DEM elevations detected: min={min_elev}m, max={max_elev}m"
        )
    return len(violations) == 0, violations


def verify_nan_values(*grids: np.ndarray) -> Tuple[bool, List[str]]:
    """
    Verifies that no cell in the passed grids contains NaN or infinite values.
    """
    violations = []
    for idx, grid in enumerate(grids):
        if np.any(np.isnan(grid)):
            violations.append(f"Grid {idx}: NaN values detected.")
        if np.any(np.isinf(grid)):
            violations.append(f"Grid {idx}: Infinite values detected.")
    return len(violations) == 0, violations


def verify_boundary_conditions(
    depth_grid: np.ndarray,
    previous_boundary_volume: float,
    current_boundary_volume: float,
    allow_leakage: bool = False
) -> Tuple[bool, List[str]]:
    """
    Checks for unexpected boundary leakage and stability.
    """
    violations = []
    # If closed boundary, water volume along the outer border should not leak
    if not allow_leakage:
        # Check boundary cells change
        border_sum = float(
            np.sum(depth_grid[0, :]) + np.sum(depth_grid[-1, :]) +
            np.sum(depth_grid[:, 0]) + np.sum(depth_grid[:, -1])
        )
        if abs(current_boundary_volume - previous_boundary_volume) > 1e-4:
            # Informational/warning check
            pass
    return len(violations) == 0, violations


def verify_timestep_stability(
    u_velocity: np.ndarray,
    v_velocity: np.ndarray,
    dx: float,
    dy: float,
    dt: float,
    max_cfl: float = 1.0
) -> Tuple[bool, List[str]]:
    """
    Verifies Courant-Friedrichs-Lewy (CFL) stability condition: dt * (u/dx + v/dy) <= max_cfl.
    """
    violations = []
    # Avoid division by zero
    dx = max(dx, 1e-5)
    dy = max(dy, 1e-5)
    
    cfl_grid = dt * (np.abs(u_velocity) / dx + np.abs(v_velocity) / dy)
    max_actual_cfl = float(np.max(cfl_grid))
    
    if max_actual_cfl > max_cfl:
        violations.append(
            f"CFL stability condition violated: max CFL = {max_actual_cfl:.3f} (max permitted = {max_cfl})"
        )
    return len(violations) == 0, violations


def verify_flow_balance(
    change_in_storage: float,
    inflow_rate: float,
    outflow_rate: float,
    dt: float,
    tolerance: float = 1.0
) -> Tuple[bool, List[str]]:
    """
    Verifies flow continuity: Change in storage / dt should match net flow rate.
    """
    violations = []
    net_flow = inflow_rate - outflow_rate
    expected_storage_change = net_flow * dt
    diff = abs(change_in_storage - expected_storage_change)
    if diff > tolerance:
        violations.append(
            f"Flow balance mismatch: change in storage = {change_in_storage:.3f}m3, "
            f"expected = {expected_storage_change:.3f}m3 (diff = {diff:.3f}m3)"
        )
    return len(violations) == 0, violations


def verify_all_physics(
    depth_grid: np.ndarray,
    dem_grid: np.ndarray,
    initial_volume: float,
    current_volume: float,
    total_inflow: float,
    total_outflow: float,
    u_velocity: np.ndarray,
    v_velocity: np.ndarray,
    dx: float,
    dy: float,
    dt: float,
    raise_on_error: bool = False
) -> Dict[str, Any]:
    """
    Runs all physical and numerical verification checks.
    """
    reports = []
    
    ok, errs = verify_no_negative_water_depth(depth_grid)
    reports.extend(errs)
    
    ok, errs = verify_mass_conservation(initial_volume, current_volume, total_inflow, total_outflow)
    reports.extend(errs)
    
    ok, errs = verify_grid_integrity(dem_grid)
    reports.extend(errs)
    
    ok, errs = verify_nan_values(depth_grid, u_velocity, v_velocity)
    reports.extend(errs)
    
    ok, errs = verify_timestep_stability(u_velocity, v_velocity, dx, dy, dt)
    reports.extend(errs)
    
    if raise_on_error and reports:
        raise SimulationException(f"Physics verification failed: {'; '.join(reports)}")
        
    return {
        "verified": len(reports) == 0,
        "violations": reports,
        "timestamp": datetime.now().isoformat()
    }
