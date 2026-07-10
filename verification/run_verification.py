"""
verification/run_verification.py
--------------------------------
Stage 1: Scientific Verification harness. Generates the 7 verification topologies,
runs the simulations, compares against golden references in verification/golden/,
and evaluates PASS/FAIL.
"""

import os
import sys
import json
import argparse
import numpy as np
from typing import Dict, Any, Tuple, List

# Add project root to python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from simulation.core.controller import SimulationController
from simulation.core.grid_manager import GridManager
from backend.config import settings

GOLDEN_DIR = os.path.join(os.path.dirname(__file__), "golden")
OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "outputs")

os.makedirs(GOLDEN_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)


def generate_flat_plane() -> Tuple[np.ndarray, Dict[str, Any]]:
    elev = np.full((20, 20), 10.0, dtype=np.float32)
    meta = {
        "transform": [0.001, 0.0, 72.80, 0.0, -0.001, 19.20],
        "crs": "EPSG:4326"
    }
    return elev, meta


def generate_single_slope() -> Tuple[np.ndarray, Dict[str, Any]]:
    elev = np.zeros((20, 20), dtype=np.float32)
    for c in range(20):
        elev[:, c] = 20.0 - (c * 0.5)  # slopes down from col 0 (20m) to col 19 (10.5m)
    meta = {
        "transform": [0.001, 0.0, 72.80, 0.0, -0.001, 19.20],
        "crs": "EPSG:4326"
    }
    return elev, meta


def generate_bowl() -> Tuple[np.ndarray, Dict[str, Any]]:
    elev = np.zeros((20, 20), dtype=np.float32)
    for r in range(20):
        for c in range(20):
            dist = np.sqrt((r - 9.5)**2 + (c - 9.5)**2)
            elev[r, c] = 5.0 + (dist * 1.5)  # lowest in center (5m), high at edges (~25m)
    meta = {
        "transform": [0.001, 0.0, 72.80, 0.0, -0.001, 19.20],
        "crs": "EPSG:4326"
    }
    return elev, meta


def generate_ridge() -> Tuple[np.ndarray, Dict[str, Any]]:
    elev = np.zeros((20, 20), dtype=np.float32)
    for c in range(20):
        dist = abs(c - 9.5)
        elev[:, c] = 20.0 - (dist * 1.0)  # highest in center column (20m) sloping down
    meta = {
        "transform": [0.001, 0.0, 72.80, 0.0, -0.001, 19.20],
        "crs": "EPSG:4326"
    }
    return elev, meta


def generate_blocked_drain() -> Tuple[np.ndarray, Dict[str, Any]]:
    # Similar to bowl, but we will configure the controller to have clogging=0.8
    return generate_bowl()


def generate_river_valley() -> Tuple[np.ndarray, Dict[str, Any]]:
    elev = np.zeros((20, 20), dtype=np.float32)
    for r in range(20):
        for c in range(20):
            # Distance from diagonal r == c
            dist = abs(r - c) / np.sqrt(2.0)
            elev[r, c] = 5.0 + (dist * 1.5)  # diagonal corridor trough (5m)
    meta = {
        "transform": [0.001, 0.0, 72.80, 0.0, -0.001, 19.20],
        "crs": "EPSG:4326"
    }
    return elev, meta


def generate_urban_block() -> Tuple[np.ndarray, Dict[str, Any], np.ndarray]:
    elev, meta = generate_flat_plane()
    # 6x6 concrete buildings block in center
    building_mask = np.zeros((20, 20), dtype=bool)
    building_mask[7:13, 7:13] = True
    return elev, meta, building_mask


def run_benchmark(
    name: str,
    elev: np.ndarray,
    meta: Dict[str, Any],
    building_mask: Optional[np.ndarray] = None,
    clogging_factor: float = 0.0
) -> Tuple[np.ndarray, Dict[str, Any], List[np.ndarray], List[Dict[str, Any]]]:
    # Configure custom GridManager
    grid_mgr = GridManager()
    
    # Optional masks
    b_mask = building_mask if building_mask is not None else np.zeros(elev.shape, dtype=bool)
    
    grid_mgr.initialize_grid_from_data(
        elevation=elev,
        meta=meta,
        building_masks=b_mask
    )

    # Initialize Controller
    ctrl = SimulationController(scenario_name="synthetic", grid_manager=grid_mgr)
    
    # Overwrite scenario properties
    ctrl.scenario.clogging_factor = clogging_factor
    ctrl.scenario.rainfall_duration = 2.0  # 2 hours
    ctrl.scenario.rainfall_intensity = 40.0 # 40 mm/hr
    
    ctrl.initialize(
        duration_hours=2.0,
        intensity_mm_hr=40.0,
        timestep_min=15.0
    )
    
    # Run the entire simulation, capturing depth history per step
    depth_history = []
    mass_balance_history = []
    
    # Store initial state
    depth_history.append(ctrl.state.water_depth_grid.copy())
    
    steps = len(ctrl.meteorology.generate_hyetograph())
    for _ in range(steps):
        ctrl.step()
        depth_history.append(ctrl.state.water_depth_grid.copy())
        mass_balance_history.append(ctrl.mass_balance_history[-1].copy())

    final_depth = ctrl.state.water_depth_grid.copy()
    final_balance = ctrl.mass_balance_history[-1] if ctrl.mass_balance_history else {}
    
    return final_depth, final_balance, depth_history, mass_balance_history


def save_golden(name: str, depth: np.ndarray, balance: Dict[str, Any]) -> None:
    depth_path = os.path.join(GOLDEN_DIR, f"{name}_depth.npy")
    balance_path = os.path.join(GOLDEN_DIR, f"{name}_balance.json")
    
    np.save(depth_path, depth)
    with open(balance_path, "w", encoding="utf-8") as f:
        json.dump(balance, f, indent=2)
    print(f"  Saved golden reference for '{name}'.")


def load_golden(name: str) -> Tuple[np.ndarray, Dict[str, Any]]:
    depth_path = os.path.join(GOLDEN_DIR, f"{name}_depth.npy")
    balance_path = os.path.join(GOLDEN_DIR, f"{name}_balance.json")
    
    if not os.path.exists(depth_path) or not os.path.exists(balance_path):
        raise FileNotFoundError(f"Golden files missing for {name}.")
        
    depth = np.load(depth_path)
    with open(balance_path, "r", encoding="utf-8") as f:
        balance = json.load(f)
    return depth, balance


def compare_to_golden(
    name: str,
    depth: np.ndarray,
    balance: Dict[str, Any]
) -> Tuple[bool, str]:
    try:
        g_depth, g_balance = load_golden(name)
    except FileNotFoundError:
        return False, "Golden files not found. Run with --generate-golden first."

    # Tolerances
    mass_tol = 1e-4
    depth_tol = 1e-3
    
    # 1. Mass error check
    abs_mass_err = float(balance.get("absolute_error", 0.0))
    if abs(abs_mass_err) > mass_tol:
        return False, f"Mass conservation error {abs_mass_err:.3e} exceeds tolerance {mass_tol:.1e}."

    # 2. Comparison with golden depth grid
    max_diff = float(np.max(np.abs(depth - g_depth)))
    if max_diff > depth_tol:
        return False, f"Water depth mismatch {max_diff:.4f}m exceeds tolerance {depth_tol:.1e}."

    return True, "Passed validation matches golden references."


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate-golden", action="store_true", help="Generate golden references")
    args = parser.parse_args()

    benchmarks = {
        "flat_plane": lambda: generate_flat_plane(),
        "single_slope": lambda: generate_single_slope(),
        "bowl": lambda: generate_bowl(),
        "ridge": lambda: generate_ridge(),
        "blocked_drain": lambda: (generate_blocked_drain()[0], generate_blocked_drain()[1], None, 0.8),
        "river_valley": lambda: generate_river_valley(),
        "urban_block": lambda: generate_urban_block()
    }

    results = {}
    all_passed = True

    print("=" * 80)
    print("STAGE 1: RUNNING SCIENTIFIC VERIFICATION BENCHMARKS")
    print("=" * 80)

    for name, gen_fn in benchmarks.items():
        print(f"\nRunning benchmark: {name}...")
        
        # Parse generator outputs
        gen_out = gen_fn()
        if len(gen_out) == 2:
            elev, meta = gen_out
            b_mask = None
            clogging = 0.0
        elif len(gen_out) == 3:
            elev, meta, b_mask = gen_out
            clogging = 0.0
        else:
            elev, meta, b_mask, clogging = gen_out

        # Run simulation
        final_depth, final_balance, depth_history, balance_history = run_benchmark(
            name=name,
            elev=elev,
            meta=meta,
            building_mask=b_mask,
            clogging_factor=clogging
        )

        # Track results
        max_depth = float(final_depth.max())
        flooded_cells = int(np.sum(final_depth > 0.05))
        flooded_pct = float(flooded_cells / final_depth.size * 100.0)
        mass_err = float(final_balance.get("absolute_error", 0.0))

        # Save outputs for plotter
        np.save(os.path.join(OUTPUTS_DIR, f"{name}_depth_final.npy"), final_depth)
        np.save(os.path.join(OUTPUTS_DIR, f"{name}_elev.npy"), elev)
        
        # Save step lists for graphing
        with open(os.path.join(OUTPUTS_DIR, f"{name}_history.json"), "w") as f:
            json.dump({
                "max_depths": [float(h.max()) for h in depth_history],
                "flooded_pcts": [float(np.sum(h > 0.05) / h.size * 100.0) for h in depth_history],
                "mass_balance": balance_history
            }, f)

        if args.generate_golden:
            save_golden(name, final_depth, final_balance)
            status = "GOLDEN"
            msg = "Golden references generated successfully."
        else:
            passed, msg = compare_to_golden(name, final_depth, final_balance)
            status = "PASS" if passed else "FAIL"
            if not passed:
                all_passed = False
            print(f"  Status: {status} — {msg}")

        results[name] = {
            "status": status,
            "message": msg,
            "max_depth_m": max_depth,
            "flooded_area_pct": flooded_pct,
            "absolute_mass_error": mass_err
        }

    results_path = os.path.join(os.path.dirname(__file__), "verification_results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 80)
    print("VERIFICATION RUN COMPLETE")
    print(f"Summary saved to: {results_path}")
    print("=" * 80)
    
    if not all_passed and not args.generate_golden:
        sys.exit(1)


if __name__ == "__main__":
    main()
