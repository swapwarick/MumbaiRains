"""
tests/test_routing.py
----------------------
Unit, integration, benchmark validation, and performance tests for the SurfaceRoutingEngine (Sprint 3).
"""

import time
import numpy as np
import pytest

from simulation.core.state import SimulationState
from simulation.core.profiler import PerformanceProfiler
from simulation.routing.engine import SurfaceRoutingEngine, BoundaryType, MassBalanceReport
from simulation.routing.benchmarks import create_routing_benchmark


class TestSurfaceRoutingUnit:
    def test_parameter_verification(self):
        # Invalid dx
        with pytest.raises(ValueError):
            SurfaceRoutingEngine(dx_m=0.0, downstream_cells=np.zeros((3, 3, 2)))
        # Invalid transfer fraction
        with pytest.raises(ValueError):
            SurfaceRoutingEngine(dx_m=10.0, downstream_cells=np.zeros((3, 3, 2)), transfer_fraction=1.5)
        # Invalid downstream cells shape
        with pytest.raises(ValueError):
            SurfaceRoutingEngine(dx_m=10.0, downstream_cells=np.zeros((3, 3)))

    def test_unsupported_boundaries(self):
        downstream = np.zeros((3, 3, 2), dtype=np.int32)
        state = SimulationState(3, 3)
        
        # Test that OUTFLOW raises NotImplementedError
        engine = SurfaceRoutingEngine(dx_m=10.0, downstream_cells=downstream, boundary_type=BoundaryType.OUTFLOW)
        with pytest.raises(NotImplementedError):
            engine.route(state, dt=1.0)

    def test_negative_depth_prevention(self):
        downstream = np.zeros((3, 3, 2), dtype=np.int32)
        engine = SurfaceRoutingEngine(dx_m=10.0, downstream_cells=downstream, transfer_fraction=0.5, boundary_type=BoundaryType.CLOSED)
        
        state = SimulationState(3, 3)
        state.water_depth_grid.fill(-0.5)  # Inject invalid state manually
        
        # SRE.route should clip negative values to 0.0 or raise an error depending on verification
        # Let's verify it cleans it up or handles it:
        # Actually, new_water = np.maximum(new_water, 0.0) is performed on the updated water depth.
        # But if the input already has negative values, we verified that in __init__ it raises ValueError if initial has negatives.
        # Wait, if we manually change it after init, let's see:
        state.water_depth_grid[1, 1] = -1.0
        # When we route: potential_outflow will be negative, but np.maximum(new_water, 0.0) protects it at the end.
        updated_state = engine.route(state, dt=1.0)
        assert np.all(updated_state.water_depth_grid >= 0.0)


class TestSurfaceRoutingBenchmarks:
    @pytest.mark.parametrize("bench_name", [
        "flat_pool",
        "uniform_slope",
        "diagonal_slope",
        "single_barrier",
        "pit",
        "ridge",
        "open_boundary",
        "closed_boundary"
    ])
    def test_benchmark_scenarios(self, bench_name):
        """
        Runs the specified routing benchmark, verifying mass balance,
        numerical sanity, and physical behavior criteria.
        """
        # 1. Load benchmark datasets
        elev, downstream, init_depth, meta = create_routing_benchmark(bench_name)
        rows, cols = elev.shape
        
        # 2. Determine boundary enum
        b_type = BoundaryType.OPEN if meta["boundary"] == "open" else BoundaryType.CLOSED
        
        # 3. Initialize engine
        engine = SurfaceRoutingEngine(
            dx_m=meta["dx"],
            downstream_cells=downstream,
            transfer_fraction=0.25,
            boundary_type=b_type
        )
        
        # 4. Initialize simulation state
        state = SimulationState(rows, cols)
        state.water_depth_grid = init_depth.copy()
        
        # 5. Run simulation loop
        dt = meta["dt"]
        steps = meta["steps"]
        
        for _ in range(steps):
            state = engine.route(state, dt)
            
        # 6. Verify numerical constraints
        final_depth = state.water_depth_grid
        assert not np.any(np.isnan(final_depth)), "Water depth contains NaNs"
        assert not np.any(np.isinf(final_depth)), "Water depth contains Infs"
        assert np.all(final_depth >= 0.0), "Water depth contains negative values"
        
        # 7. Check mass balance reports
        reports = engine.mass_balance_history
        assert len(reports) == steps
        
        for r in reports:
            if b_type == BoundaryType.CLOSED:
                # Closed boundary should conserve mass exactly (up to float32 precision)
                assert abs(r.absolute_error) < 1e-2, f"Mass balance error: {r.absolute_error}"
                assert abs(r.relative_error) < 1e-5, f"Relative mass balance error: {r.relative_error}"
            else:
                # Open boundary should change storage exactly by outflow (up to float32 precision)
                expected_error = r.current_storage - (r.initial_water - r.boundary_outflow)
                assert abs(expected_error) < 1e-2, f"Mass conservation check failed: {expected_error}"
                
        # 8. Assert benchmark physical routing validation
        assert meta["validate_fn"](init_depth, final_depth, reports), f"Benchmark {bench_name} validation failed"


class TestSurfaceRoutingPerformance:
    def test_routing_performance_limits(self):
        """
        Verify that routing operations on a large 500x500 grid run within acceptable limits.
        """
        size = 500
        # Setup uniform downstream routing
        r_coords, c_coords = np.meshgrid(np.arange(size), np.arange(size), indexing="ij")
        downstream_r = np.clip(r_coords + 1, 0, size - 1)
        downstream_c = c_coords.copy()
        downstream_cells = np.stack([downstream_r, downstream_c], axis=-1).astype(np.int32)
        
        engine = SurfaceRoutingEngine(
            dx_m=10.0,
            downstream_cells=downstream_cells,
            transfer_fraction=0.25,
            boundary_type=BoundaryType.CLOSED
        )
        
        state = SimulationState(size, size)
        state.water_depth_grid.fill(1.0)
        
        profiler = PerformanceProfiler()
        profiler.start()
        
        # Run 10 routing steps
        for _ in range(10):
            state = engine.route(state, dt=1.0)
            
        report = profiler.stop()
        avg_step_ms = report.execution_time_ms / 10.0
        print(f"500x500 Grid routed in avg {avg_step_ms:.2f}ms per step")
        
        # Ensure it is well below the target limit of 150ms per step
        assert avg_step_ms < 150.0
