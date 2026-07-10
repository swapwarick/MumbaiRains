"""
tests/test_forcing.py
----------------------
Unit, integration, benchmark, and performance tests for Forcing Framework (Sprint 4).
"""

import time
import uuid
import numpy as np
import pytest

from simulation.core.state import SimulationState
from simulation.core.profiler import PerformanceProfiler
from simulation.forcing.types import ForcingType, ForcingEventType, ForcingEvent
from simulation.forcing.units import UnitConverter
from simulation.forcing.sources import RainSource, PointSource, AreaSource
from simulation.forcing.engine import ForcingEngine
from simulation.forcing.manifest import SimulationManifest
from simulation.forcing.reports import WaterBudgetReport
from benchmarks.forcing.definitions import get_forcing_benchmark

# For combined routing + forcing tests
from simulation.routing.engine import SurfaceRoutingEngine, BoundaryType


class TestUnitConverter:
    def test_rainfall_conversions(self):
        # mm/hr to m/s: 3600 mm/hr = 1.0 mm/s = 0.001 m/s
        assert np.allclose(UnitConverter.mm_hr_to_m_s(3600.0), 0.001)
        assert np.allclose(UnitConverter.m_s_to_mm_hr(0.001), 3600.0)
        
        # Array test
        arr = np.array([3600.0, 1800.0])
        res = UnitConverter.mm_hr_to_m_s(arr)
        assert np.allclose(res, [0.001, 0.0005])

    def test_depth_volume_conversions(self):
        # 0.05m over 100m^2 = 5m^3
        assert np.allclose(UnitConverter.depth_to_volume(0.05, 100.0), 5.0)
        assert np.allclose(UnitConverter.volume_to_depth(5.0, 100.0), 0.05)

        # Isotropic cell
        assert np.allclose(UnitConverter.cell_depth_to_volume(0.05, 10.0), 5.0)
        assert np.allclose(UnitConverter.cell_volume_to_depth(5.0, 10.0), 0.05)

    def test_time_conversions(self):
        assert np.allclose(UnitConverter.hours_to_seconds(1.5), 5400.0)
        assert np.allclose(UnitConverter.seconds_to_hours(5400.0), 1.5)
        assert np.allclose(UnitConverter.days_to_seconds(2.0), 172800.0)
        assert np.allclose(UnitConverter.seconds_to_days(172800.0), 2.0)


class TestSimulationManifest:
    def test_manifest_creation_serialization(self, tmp_path):
        manifest = SimulationManifest.create(
            configuration_uuid=str(uuid.uuid4()),
            random_seed=42
        )
        assert manifest.simulation_uuid is not None
        assert manifest.numpy_version is not None
        assert manifest.operating_system is not None
        assert manifest.random_seed == 42
        
        d = manifest.to_dict()
        assert d["simulation_uuid"] == manifest.simulation_uuid
        assert d["random_seed"] == 42
        
        # File save/load
        p = tmp_path / "manifest.json"
        manifest.save_to_file(str(p))
        assert p.exists()
        
        with open(p, "r") as f:
            data = json = f.read()
            assert manifest.simulation_uuid in data


class TestForcingEngineUnit:
    def test_source_management(self):
        engine = ForcingEngine(dx_m=10.0, simulation_uuid=str(uuid.uuid4()))
        
        rain = RainSource("rain_1", 20.0)
        engine.register_source(rain)
        assert "rain_1" in engine.sources
        
        # Test events
        assert len(engine.events) == 2  # SIMULATION_STARTED, SOURCE_ADDED
        assert engine.events[1].event_type == ForcingEventType.SOURCE_ADDED.value
        
        # Enable / Disable
        engine.enable_source("rain_1", False)
        assert not rain.enabled
        # Enable it again
        engine.enable_source("rain_1", True)
        assert rain.enabled
        
        # Remove
        engine.remove_source("rain_1")
        assert "rain_1" not in engine.sources
        assert engine.events[-1].event_type == ForcingEventType.SOURCE_REMOVED.value


class TestForcingBenchmarks:
    @pytest.mark.parametrize("bench_name", [
        "uniform_rain",
        "point_source",
        "area_source",
        "multiple_sources"
    ])
    def test_forcing_benchmarks(self, bench_name):
        rows, cols = 10, 10
        dx = 10.0
        bench = get_forcing_benchmark(bench_name, rows, cols, dx)
        dt = 10.0  # seconds per step
        duration = bench["duration_seconds"]
        steps = int(duration / dt)
        
        # Init state and engine
        sim_uuid = str(uuid.uuid4())
        state = SimulationState(rows, cols)
        engine = ForcingEngine(dx_m=dx, simulation_uuid=sim_uuid)
        
        # Setup source
        if bench_name == "uniform_rain":
            src = RainSource("rain_src", bench["intensity_mm_hr"])
            engine.register_source(src)
        elif bench_name == "point_source":
            src = PointSource("point_src", bench["discharge_m3_s"], bench["row"], bench["col"])
            engine.register_source(src)
        elif bench_name == "area_source":
            src = AreaSource("area_src", bench["discharge_m3_s"], bench["mask"], is_intensity=False)
            engine.register_source(src)
        elif bench_name == "multiple_sources":
            src_rain = RainSource("rain_src", bench["rain_intensity"])
            src_point = PointSource("point_src", bench["point_discharge"], bench["point_row"], bench["point_col"])
            src_area = AreaSource("area_src", bench["area_discharge"], bench["area_mask"], is_intensity=False)
            engine.register_source(src_rain)
            engine.register_source(src_point)
            engine.register_source(src_area)
            
        # Run loop
        for _ in range(steps):
            state, report = engine.advance(state, dt)
            
            # Conservation audits per step
            assert abs(report.residual_error) < 1e-3
            assert abs(report.relative_error) < 1e-5
            assert np.all(state.water_depth_grid >= 0.0)
            
        # Finish
        engine.finish()
        assert engine.events[-1].event_type == ForcingEventType.SIMULATION_FINISHED.value
        
        # Validation checks
        cell_area = dx * dx
        total_vol = state.water_depth_grid.sum() * cell_area
        
        # Check added volume
        assert np.allclose(total_vol, bench["expected_added_volume"], rtol=1e-4)
        
        if bench_name == "uniform_rain":
            assert np.allclose(state.water_depth_grid, bench["expected_water_depth"])
        elif bench_name == "point_source":
            r, c = bench["row"], bench["col"]
            assert np.allclose(state.water_depth_grid[r, c], bench["expected_cell_depth"])
        elif bench_name == "area_source":
            mask = bench["mask"]
            assert np.allclose(state.water_depth_grid[mask], bench["expected_cell_depth"])
            assert np.all(state.water_depth_grid[~mask] == 0.0)


class TestCombinedForcingRouting:
    def test_combined_conservation(self):
        """
        Verify that combined Forcing + Routing conserves mass strictly.
        """
        rows, cols = 10, 10
        dx = 10.0
        cell_area = dx * dx
        
        # 1. Setup forcing rain (20 mm/hr)
        sim_uuid = str(uuid.uuid4())
        forcing = ForcingEngine(dx_m=dx, simulation_uuid=sim_uuid)
        rain = RainSource("rain", 20.0)
        forcing.register_source(rain)
        
        # 2. Setup closed routing engine on slope
        r_coords, c_coords = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")
        downstream_r = np.clip(r_coords + 1, 0, rows - 1)
        downstream_c = c_coords.copy()
        downstream_cells = np.stack([downstream_r, downstream_c], axis=-1).astype(np.int32)
        
        routing = SurfaceRoutingEngine(
            dx_m=dx,
            downstream_cells=downstream_cells,
            transfer_fraction=0.25,
            boundary_type=BoundaryType.CLOSED
        )
        
        # 3. Simulation Loop
        state = SimulationState(rows, cols)
        dt = 5.0  # seconds
        steps = 15
        
        initial_vol = 0.0
        cumulative_added = 0.0
        
        for _ in range(steps):
            # A. Inject rain
            state, report = forcing.advance(state, dt)
            cumulative_added += report.water_added
            
            # B. Route water
            state = routing.route(state, dt)
            
            # C. Conservation audit: Storage must equal cumulative rain (closed boundaries)
            expected_storage = initial_vol + cumulative_added
            current_storage = state.water_depth_grid.sum() * cell_area
            assert np.allclose(current_storage, expected_storage, rtol=1e-4)


class TestForcingPerformance:
    @pytest.mark.parametrize("size,time_limit", [
        (100, 0.05),
        (500, 0.30),
        (1000, 1.0)
    ])
    def test_forcing_performance_limits(self, size, time_limit):
        sim_uuid = str(uuid.uuid4())
        engine = ForcingEngine(dx_m=10.0, simulation_uuid=sim_uuid)
        
        # Uniform rain source
        rain = RainSource("rain_perf", 50.0)
        engine.register_source(rain)
        
        state = SimulationState(size, size)
        
        profiler = PerformanceProfiler()
        profiler.start()
        
        # 5 steps
        for _ in range(5):
            state, report = engine.advance(state, dt=10.0)
            
        report = profiler.stop()
        avg_step_sec = (report.execution_time_ms / 1000.0) / 5.0
        print(f"Grid {size}x{size} advanced forcing in avg {avg_step_sec:.4f}s per step (Limit: {time_limit}s)")
        
        assert avg_step_sec < time_limit
