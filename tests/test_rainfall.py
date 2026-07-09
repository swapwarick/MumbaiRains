"""
tests/test_rainfall.py
-----------------------
Unit tests for RainfallEngine.
"""

import numpy as np
import pytest
from simulation.rainfall.engine import RainfallEngine, RainfallMode
from backend.exceptions import RainfallException


class TestRainfallEngine:
    def test_constant_hyetograph_length(self):
        engine = RainfallEngine().generate(duration_hours=3, intensity_mm_hr=60.0, timestep_min=15)
        # 3h * 60min/h / 15min = 12 steps
        assert engine.n_steps == 12

    def test_constant_hyetograph_sum(self):
        # 3 hours at 60 mm/hr = 180 mm total
        engine = RainfallEngine().generate(duration_hours=3, intensity_mm_hr=60.0, timestep_min=15)
        assert engine.total_rainfall_mm == pytest.approx(180.0, rel=1e-3)

    def test_constant_all_same(self):
        engine = RainfallEngine().generate(duration_hours=2, intensity_mm_hr=40.0, timestep_min=30)
        h = engine.hyetograph
        assert np.all(h == h[0])

    def test_zero_intensity_gives_zeros(self):
        engine = RainfallEngine().generate(duration_hours=2, intensity_mm_hr=0.0, timestep_min=15)
        assert np.all(engine.hyetograph == 0.0)

    def test_hyetograph_nonnegative(self):
        engine = RainfallEngine().generate(duration_hours=4, intensity_mm_hr=100.0, timestep_min=15)
        assert np.all(engine.hyetograph >= 0.0)

    def test_invalid_duration_raises(self):
        with pytest.raises(RainfallException):
            RainfallEngine().generate(duration_hours=0)

    def test_invalid_intensity_raises(self):
        with pytest.raises(RainfallException):
            RainfallEngine().generate(duration_hours=2, intensity_mm_hr=-10.0)

    def test_no_generate_raises_on_access(self):
        engine = RainfallEngine()
        with pytest.raises(RainfallException):
            _ = engine.hyetograph

    def test_synthetic_mode_same_total(self):
        constant = RainfallEngine().generate(
            duration_hours=2, intensity_mm_hr=60.0, timestep_min=15,
            mode=RainfallMode.CONSTANT,
        )
        synthetic = RainfallEngine().generate(
            duration_hours=2, intensity_mm_hr=60.0, timestep_min=15,
            mode=RainfallMode.SYNTHETIC,
        )
        assert constant.total_rainfall_mm == pytest.approx(synthetic.total_rainfall_mm, rel=1e-3)

    def test_historical_mode_raises_not_implemented(self):
        with pytest.raises(RainfallException, match="not yet implemented"):
            RainfallEngine().generate(duration_hours=2, mode=RainfallMode.HISTORICAL)
