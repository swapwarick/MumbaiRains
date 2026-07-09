"""
tests/test_verification.py
--------------------------
Tests the Numerical Verification and Performance Profiling frameworks.
"""

import numpy as np
import pytest
from backend.exceptions import SimulationException
from simulation.core.verification import (
    verify_no_negative_water_depth,
    verify_mass_conservation,
    verify_grid_integrity,
    verify_nan_values,
    verify_boundary_conditions,
    verify_timestep_stability,
    verify_flow_balance,
    verify_all_physics
)
from simulation.core.profiler import PerformanceProfiler, ProfilerReport


class TestNumericalVerification:
    def test_verify_no_negative_water_depth(self):
        # Valid grid
        valid = np.zeros((3, 3), dtype=np.float32)
        valid[1, 1] = 0.5
        ok, errs = verify_no_negative_water_depth(valid)
        assert ok is True
        assert not errs

        # Invalid grid (violating tolerance)
        invalid = np.zeros((3, 3), dtype=np.float32)
        invalid[1, 1] = -1.0
        ok, errs = verify_no_negative_water_depth(invalid)
        assert ok is False
        assert len(errs) == 1
        assert "Negative water depth detected" in errs[0]

    def test_verify_mass_conservation(self):
        # Balanced volume
        ok, errs = verify_mass_conservation(
            initial_volume=100.0,
            current_volume=120.0,
            total_inflow=30.0,
            total_outflow=10.0
        )
        assert ok is True
        assert not errs

        # Imbalanced volume
        ok, errs = verify_mass_conservation(
            initial_volume=100.0,
            current_volume=150.0,  # 30m3 gap
            total_inflow=30.0,
            total_outflow=10.0
        )
        assert ok is False
        assert len(errs) == 1
        assert "Mass conservation violation" in errs[0]

    def test_verify_grid_integrity(self):
        # Valid DEM
        valid = np.ones((3, 3), dtype=np.float32) * 15.0
        ok, errs = verify_grid_integrity(valid)
        assert ok is True

        # Empty grid
        empty = np.array([])
        ok, errs = verify_grid_integrity(empty)
        assert ok is False
        assert "empty" in errs[0]

        # Spike grid
        spike = np.ones((3, 3), dtype=np.float32) * 10000.0
        ok, errs = verify_grid_integrity(spike)
        assert ok is False
        assert "Extreme" in errs[0]

    def test_verify_nan_values(self):
        grid = np.zeros((3, 3), dtype=np.float32)
        ok, errs = verify_nan_values(grid)
        assert ok is True

        # Has NaN
        nan_grid = np.zeros((3, 3), dtype=np.float32)
        nan_grid[1, 1] = np.nan
        ok, errs = verify_nan_values(nan_grid)
        assert ok is False
        assert "NaN" in errs[0]

        # Has Inf
        inf_grid = np.zeros((3, 3), dtype=np.float32)
        inf_grid[1, 1] = np.inf
        ok, errs = verify_nan_values(inf_grid)
        assert ok is False
        assert "Infinite" in errs[0]

    def test_verify_boundary_conditions(self):
        grid = np.zeros((3, 3), dtype=np.float32)
        ok, errs = verify_boundary_conditions(grid, 0.0, 0.0)
        assert ok is True

    def test_verify_timestep_stability(self):
        u = np.ones((3, 3), dtype=np.float32) * 2.0
        v = np.zeros((3, 3), dtype=np.float32)
        # Stable: dt=0.1, dx=1.0, dy=1.0 -> CFL = 0.1 * 2 / 1 = 0.2 <= 1.0
        ok, errs = verify_timestep_stability(u, v, 1.0, 1.0, 0.1)
        assert ok is True

        # Unstable: dt=10.0, dx=1.0, dy=1.0 -> CFL = 10 * 2 / 1 = 20.0 > 1.0
        ok, errs = verify_timestep_stability(u, v, 1.0, 1.0, 10.0)
        assert ok is False
        assert "CFL" in errs[0]

    def test_verify_flow_balance(self):
        # Stable flow change
        ok, errs = verify_flow_balance(
            change_in_storage=10.0,
            inflow_rate=5.0,
            outflow_rate=3.0,
            dt=5.0
        )
        assert ok is True

        # Mismatch
        ok, errs = verify_flow_balance(
            change_in_storage=100.0,
            inflow_rate=5.0,
            outflow_rate=3.0,
            dt=5.0
        )
        assert ok is False

    def test_verify_all_physics(self):
        depth = np.zeros((3, 3), dtype=np.float32)
        dem = np.ones((3, 3), dtype=np.float32) * 5.0
        u = np.zeros((3, 3), dtype=np.float32)
        v = np.zeros((3, 3), dtype=np.float32)

        res = verify_all_physics(
            depth_grid=depth,
            dem_grid=dem,
            initial_volume=0.0,
            current_volume=0.0,
            total_inflow=0.0,
            total_outflow=0.0,
            u_velocity=u,
            v_velocity=v,
            dx=1.0,
            dy=1.0,
            dt=1.0
        )
        assert res["verified"] is True
        assert not res["violations"]

        # Failure raises exception when requested
        depth_neg = np.ones((3, 3), dtype=np.float32) * -1.0
        with pytest.raises(SimulationException):
            verify_all_physics(
                depth_grid=depth_neg,
                dem_grid=dem,
                initial_volume=0.0,
                current_volume=0.0,
                total_inflow=0.0,
                total_outflow=0.0,
                u_velocity=u,
                v_velocity=v,
                dx=1.0,
                dy=1.0,
                dt=1.0,
                raise_on_error=True
            )


class TestPerformanceProfiler:
    def test_profiler_lifecycle(self):
        profiler = PerformanceProfiler()
        profiler.start()
        
        profiler.record_raster_read(2)
        profiler.record_vector_query(5)
        profiler.record_tile_cache_hit(10)
        
        report = profiler.stop()
        assert isinstance(report, ProfilerReport)
        assert report.raster_reads == 2
        assert report.vector_queries == 5
        assert report.tile_cache_hits == 10
        assert report.execution_time_ms >= 0.0
        assert report.memory_growth_mb >= 0.0
        assert report.cpu_percent >= 0.0
