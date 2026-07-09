"""
tests/test_hydrology.py
------------------------
Unit tests for SCS runoff and HydrologyEngine.
"""

import numpy as np
import pytest
from simulation.hydrology.runoff import calculate_scs_runoff, green_ampt_infiltration
from simulation.hydrology.engine import HydrologyEngine
from backend.exceptions import SimulationException


class TestSCSRunoff:
    def test_zero_rainfall_gives_zero_runoff(self):
        cn = np.full((5, 5), 85.0, dtype=np.float32)
        runoff = calculate_scs_runoff(np.array([0.0]), cn)
        assert np.all(runoff == 0.0)

    def test_runoff_less_than_rainfall(self):
        cn = np.full((5, 5), 85.0, dtype=np.float32)
        rain = np.array([50.0])  # 50 mm
        runoff = calculate_scs_runoff(rain, cn)
        assert np.all(runoff <= 50.0)

    def test_higher_cn_gives_more_runoff(self):
        rain = np.array([50.0])
        cn_low  = np.full((1, 1), 60.0, dtype=np.float32)
        cn_high = np.full((1, 1), 90.0, dtype=np.float32)
        assert calculate_scs_runoff(rain, cn_high)[0, 0] > calculate_scs_runoff(rain, cn_low)[0, 0]

    def test_output_shape_matches_cn(self):
        cn = np.full((10, 10), 75.0, dtype=np.float32)
        runoff = calculate_scs_runoff(np.array([30.0]), cn)
        assert runoff.shape == cn.shape

    def test_runoff_nonnegative(self):
        cn = np.full((5, 5), 85.0, dtype=np.float32)
        runoff = calculate_scs_runoff(np.array([100.0]), cn)
        assert np.all(runoff >= 0.0)


class TestGreenAmpt:
    def test_returns_float(self):
        rate = green_ampt_infiltration(
            suction_head=110.0,
            hydraulic_conductivity=10.0,
            moisture_deficit=0.3,
            cumulative_infiltration=20.0,
        )
        assert isinstance(rate, float)

    def test_zero_cumulative_returns_ks(self):
        ks = 15.0
        rate = green_ampt_infiltration(110.0, ks, 0.3, 0.0)
        assert rate == pytest.approx(ks)

    def test_rate_decreases_with_more_infiltration(self):
        kwargs = dict(suction_head=110.0, hydraulic_conductivity=10.0, moisture_deficit=0.3)
        r1 = green_ampt_infiltration(**kwargs, cumulative_infiltration=10.0)
        r2 = green_ampt_infiltration(**kwargs, cumulative_infiltration=50.0)
        assert r1 > r2


class TestHydrologyEngine:
    def test_requires_initialise(self, tiny_dem):
        engine = HydrologyEngine()
        with pytest.raises(SimulationException):
            engine.compute_runoff(50.0)

    def test_initialise_returns_self(self, tiny_dem):
        engine = HydrologyEngine()
        result = engine.initialise(tiny_dem)
        assert result is engine

    def test_runoff_shape(self, tiny_dem):
        engine = HydrologyEngine().initialise(tiny_dem)
        runoff = engine.compute_runoff(50.0)
        assert runoff.shape == tiny_dem.shape

    def test_runoff_nonnegative(self, tiny_dem):
        engine = HydrologyEngine().initialise(tiny_dem)
        runoff = engine.compute_runoff(100.0)
        assert np.all(runoff >= 0.0)

    def test_low_cells_get_more_runoff(self, tiny_dem):
        """Low-lying cells (low elevation) should receive more runoff than hilltops."""
        engine = HydrologyEngine().initialise(tiny_dem)
        runoff = engine.compute_runoff(50.0)
        low_idx  = np.unravel_index(tiny_dem.argmin(), tiny_dem.shape)
        high_idx = np.unravel_index(tiny_dem.argmax(), tiny_dem.shape)
        assert runoff[low_idx] > runoff[high_idx]

    def test_reset_clears_accumulation(self, tiny_dem):
        engine = HydrologyEngine().initialise(tiny_dem)
        engine.compute_runoff(100.0)
        engine.reset()
        assert engine._accumulated_rain == 0.0
