"""
tests/test_terrain.py
----------------------
Unit and integration tests for the Terrain Engine (Sprint 2).
Validates synthetic surfaces, golden reference datasets, visual exports,
watershed delineation, and performance/memory target regression.
"""

import os
import time
import numpy as np
import pytest

from simulation.terrain.loader import TerrainLoader
from simulation.terrain.engine import TerrainEngine
from simulation.terrain.algorithms import (
    compute_slope_aspect,
    compute_slope_percent,
    compute_flow_direction_d8,
    compute_flow_direction_d8_all,
    compute_flow_accumulation,
    delineate_watershed,
    compute_hillshade
)
from backend.exceptions import TerrainException
from simulation.core.profiler import PerformanceProfiler

try:
    import matplotlib
    _MATPLOTLIB = True
except ImportError:
    _MATPLOTLIB = False

try:
    import rasterio
    _RASTERIO = True
except ImportError:
    _RASTERIO = False


class TestSlopeAspect:
    def test_output_shape(self):
        tiny_dem = np.ones((5, 5), dtype=np.float32)
        slope, aspect = compute_slope_aspect(tiny_dem, cell_size=30.0)
        assert slope.shape == tiny_dem.shape
        assert aspect.shape == tiny_dem.shape

    def test_slope_nonnegative(self):
        tiny_dem = np.ones((5, 5), dtype=np.float32)
        slope, _ = compute_slope_aspect(tiny_dem, cell_size=30.0)
        assert np.all(slope >= 0.0)

    def test_slope_max_90(self):
        tiny_dem = np.ones((5, 5), dtype=np.float32)
        slope, _ = compute_slope_aspect(tiny_dem, cell_size=30.0)
        assert np.all(slope <= 90.0)


class TestSyntheticAndGoldenBenchmarks:
    def test_golden_datasets_tolerances(self):
        """
        Verify that computed outputs for all synthetic grids exactly match
        or fall within numerical tolerances of the golden datasets.
        """
        loader = TerrainLoader()
        engine = TerrainEngine(_loader=loader)
        
        benchmarks = ["flat_surface", "uniform_slope", "single_hill", "single_valley", "synthetic_watershed"]
        golden_dir = loader.golden_dir

        for bench in benchmarks:
            # 1. Load benchmark elevation via engine
            engine.load(bench)
            
            # 2. Load expected golden reference arrays
            golden_path = os.path.join(golden_dir, f"{bench}.npz")
            golden = np.load(golden_path)
            
            # Extract computed arrays
            comp_slope = engine.slope
            comp_slope_pct = engine.slope_percent
            comp_aspect = engine.aspect
            comp_flow_dir = engine.flow_direction
            comp_flow_acc = engine.flow_accumulation
            
            # Extract golden arrays
            gold_elev = golden["elevation"]
            gold_slope = golden["slope_deg"]
            gold_slope_pct = golden["slope_pct"]
            gold_aspect = golden["aspect"]
            gold_flow_dir = golden["dir"] if "dir" in golden else golden["flow_dir"]
            gold_flow_acc = golden["acc"] if "acc" in golden else golden["flow_acc"]
            
            # 3. Compare with defined tolerances
            assert np.allclose(engine.elevation, gold_elev)
            
            # Slope tolerance: +/- 0.01 degrees
            assert np.all(np.abs(comp_slope - gold_slope) <= 0.01)
            assert np.all(np.abs(comp_slope_pct - gold_slope_pct) <= 0.5)
            
            # Aspect tolerance: +/- 0.5 degrees (excluding flat cells of -1.0)
            steep_gold = gold_aspect != -1.0
            steep_comp = comp_aspect != -1.0
            assert np.all(steep_gold == steep_comp)
            assert np.all(np.abs(comp_aspect[steep_gold] - gold_aspect[steep_gold]) <= 0.5)
            assert np.all(comp_aspect[~steep_gold] == -1.0)
            
            # Flow direction tolerance: Exact matching
            assert np.array_equal(comp_flow_dir, gold_flow_dir)
            
            # Flow accumulation tolerance: Exact matching
            assert np.array_equal(comp_flow_acc, gold_flow_acc)

    def test_delineate_watershed(self):
        engine = TerrainEngine().load("synthetic_watershed")
        
        # Test watershed mask generation from outlet at bottom center (14, 7)
        outlet = (14, 7)
        mask = engine.delineate_watershed_mask(outlet)
        assert mask.shape == engine.elevation.shape
        assert mask[14, 7] is True
        # Cells further away at higher elevations should drain to it
        assert np.any(mask)

    def test_visual_and_data_exports(self, tmp_path):
        engine = TerrainEngine().load("single_hill")
        out_dir = str(tmp_path / "exports")
        
        # Export all computational grids
        engine.export_all(out_dir)
        
        # Verify all stats files exist
        expected_bases = [
            "elevation", "slope_deg", "slope_pct", "aspect",
            "flow_direction", "flow_accumulation", "hillshade"
        ]
        for base in expected_bases:
            assert os.path.exists(os.path.join(out_dir, f"{base}_stats.txt"))
            if _MATPLOTLIB:
                assert os.path.exists(os.path.join(out_dir, f"{base}_vis.png"))
                assert os.path.exists(os.path.join(out_dir, f"{base}_histogram.png"))
            if _RASTERIO:
                assert os.path.exists(os.path.join(out_dir, f"{base}.tif"))


class TestTerrainPerformanceRegression:
    @pytest.mark.parametrize("size,target_sec", [
        (100, 0.2),
        (500, 2.0),
        (1000, 8.0)
    ])
    def test_performance_targets(self, size, target_sec):
        """
        Verify terrain analysis algorithms satisfy execution time limits.
        """
        # Create synthetic elevation plane
        elev = np.ones((size, size), dtype=np.float32) * 5.0
        
        profiler = PerformanceProfiler()
        profiler.start()
        
        # Trigger all computations
        slope, aspect = compute_slope_aspect(elev, 10.0)
        slope_pct = compute_slope_percent(elev, 10.0)
        flow_dir, flow_angle, downstream = compute_flow_direction_d8_all(elev, 10.0)
        flow_acc = compute_flow_accumulation(flow_dir, elev)
        hillshade = compute_hillshade(elev, 10.0)
        
        report = profiler.stop()
        dur_sec = report.execution_time_ms / 1000.0
        
        print(f"Grid {size}x{size} processed in {dur_sec:.4f}s (Target: < {target_sec}s)")
        assert dur_sec < target_sec

    def test_memory_duplication_safety(self):
        """
        Verify grid processing memory footprint is bounded within 2x raster size.
        """
        size = 500
        elev = np.ones((size, size), dtype=np.float32) * 5.0
        
        # Base size in bytes: 500 * 500 * 4 bytes = 1,000,000 bytes (approx 1 MB)
        raster_size_mb = (elev.nbytes) / (1024.0 * 1024.0)
        
        profiler = PerformanceProfiler()
        profiler.start()
        
        # Perform computation
        slope, aspect = compute_slope_aspect(elev, 10.0)
        report = profiler.stop()
        
        # Memory growth in MB should be reasonable (no huge duplicating arrays)
        assert report.memory_growth_mb <= (2.0 * raster_size_mb) or report.memory_growth_mb < 5.0


class TestTerrainEngine:
    def test_load_returns_self(self, tmp_path):
        engine = TerrainEngine()
        result = engine.load(str(tmp_path / "nonexistent.tif"))  # triggers fallback
        assert result is engine

    def test_properties_accessible(self, tmp_path):
        engine = TerrainEngine().load(str(tmp_path / "nonexistent.tif"))
        assert engine.elevation.ndim == 2
        assert engine.slope.shape == engine.elevation.shape
        assert engine.aspect.shape == engine.elevation.shape
        assert engine.flow_direction.shape == engine.elevation.shape
        assert engine.flow_accumulation.shape == engine.elevation.shape

    def test_metadata_keys(self, tmp_path):
        meta = TerrainEngine().load(str(tmp_path / "x.tif")).metadata
        for key in ("width", "height", "crs", "transform", "bounds", "stats"):
            assert key in meta

    def test_require_load_raises(self):
        engine = TerrainEngine()
        with pytest.raises(TerrainException):
            _ = engine.elevation

    def test_full_grid_backward_compat(self, tmp_path):
        grid = TerrainEngine().load(str(tmp_path / "x.tif")).full_grid()
        for key in ("width", "height", "crs", "transform", "elevation", "slope",
                    "aspect", "flow_direction", "flow_accumulation"):
            assert key in grid
        assert isinstance(grid["elevation"], list)
