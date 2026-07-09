"""
tests/test_simulation.py
-------------------------
Integration and unit tests for the updated simulation pipeline.
Uses a tiny 10x10 DEM and synthetic settings for fast execution.
"""

import numpy as np
import pytest
from simulation.core.simulation_engine import SimulationEngine
from simulation.routing.engine import FlowRoutingEngine
from simulation.flood.engine import FloodEngine
from backend.exceptions import SimulationException


class TestFlowRoutingEngine:
    def test_routing_depth_nonnegative(self, tiny_dem):
        engine = FlowRoutingEngine(solver_type="diffusion")
        water_depth = np.ones_like(tiny_dem, dtype=np.float32) * 0.1
        manning_n = np.full_like(tiny_dem, 0.03, dtype=np.float32)
        
        new_depth, vx, vy = engine.route(
            elevation=tiny_dem,
            water_depth=water_depth,
            manning_n=manning_n,
            dx_m=30.0,
            dt_seconds=60.0
        )
        assert np.all(new_depth >= 0.0)
        assert vx.shape == tiny_dem.shape
        assert vy.shape == tiny_dem.shape

    def test_mass_conservation(self, tiny_dem):
        """Total water volume should be approximately conserved after routing."""
        engine = FlowRoutingEngine(solver_type="diffusion")
        water_depth = np.ones_like(tiny_dem, dtype=np.float32) * 0.1
        manning_n = np.full_like(tiny_dem, 0.03, dtype=np.float32)
        
        volume_before = float(water_depth.sum())
        new_depth, _, _ = engine.route(
            elevation=tiny_dem,
            water_depth=water_depth,
            manning_n=manning_n,
            dx_m=30.0,
            dt_seconds=60.0
        )
        volume_after = float(new_depth.sum())
        assert abs(volume_after - volume_before) / volume_before < 1e-3


class TestFloodEngine:
    def test_initial_metrics_zero(self, tiny_dem):
        rows, cols = tiny_dem.shape
        engine = FloodEngine(rows, cols)
        assert np.all(engine.flood_duration_seconds == 0.0)
        assert np.all(engine.hazard_rating == 0.0)
        assert np.all(engine.hazard_class == 0)

    def test_hazard_rating_updates(self, tiny_dem):
        rows, cols = tiny_dem.shape
        engine = FloodEngine(rows, cols)
        
        water_depth = np.ones((rows, cols), dtype=np.float32) * 0.5
        vx = np.ones((rows, cols), dtype=np.float32) * 1.0
        vy = np.zeros((rows, cols), dtype=np.float32)
        
        flooded_mask, hazard_rating, hazard_class = engine.update_metrics(
            water_depth_m=water_depth,
            velocity_x_m_s=vx,
            velocity_y_m_s=vy,
            dt_seconds=10.0
        )
        assert np.all(flooded_mask == True)
        # HR = d * (v + 0.5) + DF = 0.5 * (1.0 + 0.5) + 0.5 = 0.75 + 0.5 = 1.25
        assert np.all(hazard_rating == 1.25)
        # HR >= 1.25 corresponds to hazard class 3
        assert np.all(hazard_class == 3)

    def test_duration_increments(self, tiny_dem):
        rows, cols = tiny_dem.shape
        engine = FloodEngine(rows, cols)
        
        water_depth = np.ones((rows, cols), dtype=np.float32) * 0.1
        vx = np.zeros((rows, cols), dtype=np.float32)
        vy = np.zeros((rows, cols), dtype=np.float32)
        
        engine.update_metrics(water_depth, vx, vy, dt_seconds=60.0)
        assert np.all(engine.flood_duration_seconds == 60.0)


class TestSimulationEngine:
    def test_run_returns_required_keys(self, tmp_path):
        result = SimulationEngine().run(
            dem_path=str(tmp_path / "x.tif"),
            gpkg_path=str(tmp_path / "x.gpkg"),
            duration_hours=1,
            intensity_mm_hr=50.0,
            timestep_min=30,
        )
        for key in ("metadata", "time_steps_min", "rainfall_hyetograph_mm", "depth_history"):
            assert key in result

    def test_depth_history_length(self, tmp_path):
        result = SimulationEngine().run(
            dem_path=str(tmp_path / "x.tif"),
            gpkg_path=str(tmp_path / "x.gpkg"),
            duration_hours=1,
            intensity_mm_hr=50.0,
            timestep_min=30,
        )
        n_steps = len(result["rainfall_hyetograph_mm"])
        assert len(result["depth_history"]) == n_steps + 1

    def test_depth_nonnegative(self, tmp_path):
        result = SimulationEngine().run(
            dem_path=str(tmp_path / "x.tif"),
            gpkg_path=str(tmp_path / "x.gpkg"),
            duration_hours=1,
            intensity_mm_hr=60.0,
            timestep_min=30,
        )
        for grid in result["depth_history"]:
            for row in grid:
                assert all(v >= 0.0 for v in row)

    def test_flood_increases_over_time(self, tmp_path):
        result = SimulationEngine().run(
            dem_path=str(tmp_path / "x.tif"),
            gpkg_path=str(tmp_path / "x.gpkg"),
            duration_hours=2,
            intensity_mm_hr=100.0,
            timestep_min=60,
        )
        h = result["depth_history"]
        total_first = sum(v for row in h[1] for v in row)
        total_last  = sum(v for row in h[-1] for v in row)
        assert total_last > total_first
